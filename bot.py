import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

from llm import ollama_chat
from storage import load_state, save_state, add_context, list_chat_ids
from commands import handle_command

# ===== CONFIG =====
TOKEN = "8582375123:AAESYz8UaFFqHRjn_12IYvW7-L-wf-6wOJ8"
MODEL = "llama3:latest"
ALLOWED_USERS = {5264776416}
# ==================

TZ = ZoneInfo("Asia/Jerusalem")

SYSTEM_BASE = (
    "You are a helpful assistant.\n"
    "IMPORTANT RULES:\n"
    "1) Only use the user's saved data (profile/todos/reminders/notes) if it is clearly relevant to the current message.\n"
    "2) If it is not relevant, do NOT mention it and do NOT hint that you saw it.\n"
    "3) If you use saved data, keep it to ONE short sentence, then answer the question.\n"
    "4) Never invent or assume details from saved data.\n"
    "Keep answers short."
)

def wants_tasks_memory(user_text: str) -> bool:
    t = (user_text or "").lower()
    keywords = [
        "todo", "todos", "task", "tasks",
        "plan", "planning", "schedule", "agenda",
        "remind", "reminder", "reminders",
        "note", "notes",
        "what should i do", "what do i have", "what's on",
        "today", "tomorrow", "this week", "next week",
        "list", "show", "brief"
    ]
    return any(k in t for k in keywords)

def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")

def _job_name(chat_id: int, rid: int) -> str:
    return f"reminder:{chat_id}:{rid}"

def cancel_job(application, chat_id: int, rid: int) -> None:
    name = _job_name(chat_id, rid)
    try:
        jobs = application.job_queue.get_jobs_by_name(name)
        for j in jobs:
            try:
                j.schedule_removal()
            except:
                pass
    except:
        pass

def _find_reminder(state: dict, rid: int) -> dict | None:
    for r in state.get("reminders", []):
        try:
            if int(r.get("id", -1)) == int(rid):
                return r
        except:
            pass
    return None

def schedule_one(application, chat_id: int, rid: int, when_iso: str, text: str) -> None:
    when_dt = datetime.fromisoformat(when_iso)
    now = datetime.now(TZ)

    # If reminder is in the past, drop it (for one-time reminders)
    if when_dt <= now:
        state = load_state(chat_id)
        r = _find_reminder(state, rid)
        if r:
            repeat = (r.get("repeat") or "once").lower()
            if repeat in ("once", "one", "single"):
                state["reminders"] = [x for x in state.get("reminders", []) if int(x.get("id", -1)) != int(rid)]
                save_state(chat_id, state)
        return

    # prevent duplicates
    cancel_job(application, chat_id, rid)

    delay = (when_dt - now).total_seconds()
    application.job_queue.run_once(
        send_reminder,
        when=delay,
        data={"chat_id": chat_id, "rid": rid, "text": text},
        name=_job_name(chat_id, rid),
    )

def schedule_from_state(application, chat_id: int, rid: int) -> None:
    state = load_state(chat_id)
    r = _find_reminder(state, rid)
    if not r:
        return
    schedule_one(application, chat_id, int(r["id"]), r["when"], r.get("text", ""))

async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data or {}
    chat_id = job_data.get("chat_id")
    rid = job_data.get("rid")
    text = job_data.get("text", "")

    if not chat_id or rid is None:
        return

    # Send message
    await context.bot.send_message(chat_id=chat_id, text=f"🔔 Reminder: {text}")

    # Update storage: if recurring -> compute next time, else delete
    state = load_state(chat_id)
    rems = state.get("reminders", [])
    r = _find_reminder(state, int(rid))
    if not r:
        return

    repeat = (r.get("repeat") or "once").lower()
    now = datetime.now(TZ)

    if repeat in ("once", "one", "single"):
        state["reminders"] = [it for it in rems if int(it.get("id", -1)) != int(rid)]
        save_state(chat_id, state)
        return

    dt = datetime.fromisoformat(r["when"])
    if repeat == "daily":
        next_dt = dt + timedelta(days=1)
    elif repeat == "weekly":
        next_dt = dt + timedelta(days=7)
    elif repeat == "every":
        mins = int(r.get("every_minutes", 60))
        next_dt = dt + timedelta(minutes=mins)
    else:
        # unknown -> treat as one-time
        state["reminders"] = [it for it in rems if int(it.get("id", -1)) != int(rid)]
        save_state(chat_id, state)
        return

    while next_dt <= now:
        if repeat == "daily":
            next_dt += timedelta(days=1)
        elif repeat == "weekly":
            next_dt += timedelta(days=7)
        elif repeat == "every":
            next_dt += timedelta(minutes=int(r.get("every_minutes", 60)))

    r["when"] = next_dt.isoformat()
    save_state(chat_id, state)

    # schedule next occurrence
    schedule_from_state(context.application, chat_id, int(rid))

def reschedule_all(application) -> None:
    for chat_id in list_chat_ids():
        state = load_state(chat_id)
        for r in state.get("reminders", []):
            try:
                schedule_one(application, chat_id, int(r["id"]), r["when"], r.get("text", ""))
            except:
                pass

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    if update.effective_user.id not in ALLOWED_USERS:
        return

    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()
    if not text:
        return

    state = load_state(chat_id)

    # 1) Deterministic commands
    if text.startswith("/"):
        reply = handle_command(chat_id, state, text)

        # schedule marker
        if reply.startswith("__SCHEDULE_REMINDER__|"):
            _, rid_s = reply.split("|", 1)
            rid = int(rid_s.strip())
            schedule_from_state(context.application, chat_id, rid)

            state2 = load_state(chat_id)
            r = _find_reminder(state2, rid)
            when_dt = datetime.fromisoformat(r["when"]) if r else datetime.now(TZ)
            rep = (r.get("repeat") if r else "once")
            extra = f" ({rep})" if rep and rep != "once" else ""
            await update.message.reply_text(f"Reminder set for {_fmt_dt(when_dt)}{extra}.")
            return

        # cancel marker
        if reply.startswith("__CANCEL_REMINDER__|"):
            _, rid_s, msg = reply.split("|", 2)
            rid = int(rid_s.strip())
            cancel_job(context.application, chat_id, rid)
            await update.message.reply_text(msg.strip() if msg else "Canceled.")
            return

        await update.message.reply_text(reply)
        return

    # 2) Build system prompt
    system_prompt = SYSTEM_BASE
    # Always inject current time/date
    now = datetime.now(TZ)
    system_prompt += f"\nCurrent time: {now.strftime('%Y-%m-%d %H:%M')} ({TZ.key}, {now.strftime('%A')})"
	

    # ALWAYS inject personal profile if it exists (so personal info works naturally)
    profile = state.get("profile", {})
    prof_lines = "\n".join([f"{k}: {v}" for k, v in profile.items()])
    if prof_lines:
        system_prompt += f"\nUser profile:\n{prof_lines}"

    # Inject tasks only when relevant
    if wants_tasks_memory(text):
        todos = [t for t in state.get("todos", []) if not t.get("done")]
        todo_lines = "\n".join([f"- {t.get('text','')}" for t in todos[:10]])

        reminders = sorted(state.get("reminders", []), key=lambda r: r.get("when", ""))
        rem_lines = []
        for r in reminders[:5]:
            dt = datetime.fromisoformat(r["when"])
            rem_lines.append(f"- {_fmt_dt(dt)} — {r.get('text','')}")
        rem_lines = "\n".join(rem_lines)

        notes = state.get("notes", [])
        note_lines = "\n".join([f"- {n.get('text','')}" for n in notes[-10:]])

        if todo_lines:
            system_prompt += f"\nUser todos (pending):\n{todo_lines}"
        if rem_lines:
            system_prompt += f"\nUser reminders (upcoming):\n{rem_lines}"
        if note_lines:
            system_prompt += f"\nUser notes (recent):\n{note_lines}"

    messages = [{"role": "system", "content": system_prompt}]

    # 3) Short-term context (optional)
    if state.get("mode") == "context":
        messages += state.get("context", [])

    messages.append({"role": "user", "content": text})

    # 4) LLM call
    reply = ollama_chat(MODEL, messages)

    # 5) Save context if enabled
    if state.get("mode") == "context":
        add_context(state, "user", text, max_turns=10)
        add_context(state, "assistant", reply, max_turns=10)
        save_state(chat_id, state)

    await update.message.reply_text(reply or "No response.")

async def on_start(app):
    reschedule_all(app)

app = ApplicationBuilder().token(TOKEN).post_init(on_start).build()
app.add_handler(MessageHandler(filters.TEXT, handle))
app.run_polling()
