import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from storage import save_state

TZ = ZoneInfo("Asia/Jerusalem")

def _now() -> datetime:
    return datetime.now(TZ)

def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")

def _next_id(items: list[dict]) -> int:
    mx = 0
    for it in items:
        try:
            mx = max(mx, int(it.get("id", 0)))
        except:
            pass
    return mx + 1

def parse_remind(text: str) -> tuple[dict | None, str | None]:
    s = text.strip()
    s = re.sub(r"^/reminder\b", "/remind", s, flags=re.IGNORECASE)

    m = re.match(r"^/remind\s+every\s+(\d+)\s*([mh])\s+(.+)$", s, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()
        msg = m.group(3).strip()
        mins = n if unit == "m" else n * 60
        dt = _now() + timedelta(minutes=mins)
        meta = {"repeat": "every", "every_minutes": mins, "when": dt}
        return meta, msg

    m = re.match(r"^/remind\s+daily\s+(\d{2}:\d{2})\s+(.+)$", s, re.IGNORECASE)
    if m:
        time_s = m.group(1)
        msg = m.group(2).strip()
        hh, mm = map(int, time_s.split(":"))
        dt = _now().replace(hour=hh, minute=mm, second=0, microsecond=0)
        if dt <= _now():
            dt = dt + timedelta(days=1)
        meta = {"repeat": "daily", "when": dt, "time": time_s}
        return meta, msg

    m = re.match(r"^/remind\s+weekly\s+(mon|tue|wed|thu|fri|sat|sun)\s+(\d{2}:\d{2})\s+(.+)$", s, re.IGNORECASE)
    if m:
        day_s = m.group(1).lower()
        time_s = m.group(2)
        msg = m.group(3).strip()
        hh, mm = map(int, time_s.split(":"))
        target = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}[day_s]
        now = _now()
        dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        days_ahead = (target - now.weekday()) % 7
        if days_ahead == 0 and dt <= now:
            days_ahead = 7
        dt = dt + timedelta(days=days_ahead)
        meta = {"repeat": "weekly", "when": dt, "weekday": target, "day": day_s, "time": time_s}
        return meta, msg

    m = re.match(r"^/remind\s+in\s+(\d+)\s*([mh])\s+(.+)$", s, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()
        msg = m.group(3).strip()
        dt = _now() + (timedelta(minutes=n) if unit == "m" else timedelta(hours=n))
        meta = {"repeat": "once", "when": dt}
        return meta, msg

    m = re.match(r"^/remind\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+(.+)$", s)
    if m:
        date_s = m.group(1)
        time_s = m.group(2)
        msg = m.group(3).strip()
        dt = datetime.strptime(f"{date_s} {time_s}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
        meta = {"repeat": "once", "when": dt}
        return meta, msg

    m = re.match(r"^/remind\s+(\d{2}:\d{2})\s+(.+)$", s)
    if m:
        time_s = m.group(1)
        msg = m.group(2).strip()
        hh, mm = map(int, time_s.split(":"))
        dt = _now().replace(hour=hh, minute=mm, second=0, microsecond=0)
        if dt <= _now():
            dt = dt + timedelta(days=1)
        meta = {"repeat": "once", "when": dt}
        return meta, msg

    return None, None

def handle_command(chat_id: int, state: dict, text: str) -> str:
    parts = text.strip().split(maxsplit=2)
    cmd = parts[0].lower()

    if cmd == "/reminder":
        cmd = "/remind"

    # ===== memory/profile =====
    if cmd == "/remember":
        raw = text.strip()[len("/remember"):].strip()
        if "=" not in raw:
            return "Usage: /remember key=value"
        key, value = raw.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key:
            return "Usage: /remember key=value"

        state.setdefault("profile", {})
        state["profile"][key] = value
        save_state(chat_id, state)
        return f"Saved: {key}={value}"

    if cmd == "/mem":
        prof = state.get("profile", {})
        if not prof:
            return "No saved memory."
        return "Saved memory:\n" + "\n".join([f"{k} = {v}" for k, v in prof.items()])

    if cmd == "/forget":
        if len(parts) < 2:
            return "Usage: /forget key"
        key = parts[1].strip()
        if key in state["profile"]:
            del state["profile"][key]
            save_state(chat_id, state)
            return f"Removed: {key}"
        return "Not found."

    # ===== mode/context =====
    if cmd == "/mode":
        if len(parts) < 2:
            return "Usage: /mode normal|context"
        mode = parts[1].lower()
        if mode not in {"normal", "context"}:
            return "Usage: /mode normal|context"
        state["mode"] = mode
        if mode == "normal":
            state["context"] = []
        save_state(chat_id, state)
        return f"Mode set to: {mode}"

    # ===== todo =====
    if cmd == "/todo":
        if len(parts) < 2:
            return "Usage: /todo add|list|done|del|clear ."
        action = parts[1].lower()

        if action == "add":
            if len(parts) < 3:
                return "Usage: /todo add <text>"
            state["todos"].append({"text": parts[2].strip(), "done": False})
            save_state(chat_id, state)
            return "Added."

        if action == "list":
            show_all = (len(parts) >= 3 and parts[2].strip().lower() == "all")
            todos = state.get("todos", [])
            items = todos if show_all else [t for t in todos if not t.get("done")]
            if not items:
                return "No todos."
            out = []
            for i, t in enumerate(items, start=1):
                mark = "✅" if t.get("done") else "⬜"
                rid = t.get("reminder_id")
                link = f" ⏰#{rid}" if rid else ""
                out.append(f"{i}) {mark} {t.get('text','')}{link}")
            return "\n".join(out)

        if action == "done":
            if len(parts) < 3:
                return "Usage: /todo done <id>"
            try:
                idx = int(parts[2]) - 1
                t = state["todos"][idx]
                t["done"] = True

                rid = t.get("reminder_id")
                if rid:
                    before = len(state.get("reminders", []))
                    state["reminders"] = [r for r in state.get("reminders", []) if int(r.get("id", -1)) != int(rid)]
                    t.pop("reminder_id", None)
                    save_state(chat_id, state)
                    if len(state.get("reminders", [])) != before:
                        return f"__CANCEL_REMINDER__|{rid}|Done (and canceled reminder #{rid})."
                save_state(chat_id, state)
                return "Done."
            except:
                return "Invalid id."

        if action == "del":
            if len(parts) < 3:
                return "Usage: /todo del <id>"
            try:
                idx = int(parts[2]) - 1
                t = state["todos"][idx]
                rid = t.get("reminder_id")
                state["todos"].pop(idx)

                if rid:
                    before = len(state.get("reminders", []))
                    state["reminders"] = [r for r in state.get("reminders", []) if int(r.get("id", -1)) != int(rid)]
                    save_state(chat_id, state)
                    if len(state.get("reminders", [])) != before:
                        return f"__CANCEL_REMINDER__|{rid}|Deleted todo (and canceled reminder #{rid})."

                save_state(chat_id, state)
                return "Deleted."
            except:
                return "Invalid id."

        if action == "clear":
            for t in state.get("todos", []):
                rid = t.get("reminder_id")
                if rid:
                    state["reminders"] = [r for r in state.get("reminders", []) if int(r.get("id", -1)) != int(rid)]
            state["todos"] = []
            save_state(chat_id, state)
            return "Todos cleared."

        return "Usage: /todo add|list|done|del|clear ..."

    # ===== note =====
    if cmd == "/note":
        if len(parts) < 2:
            return "Usage: /note add|list|del|clear ..."
        action = parts[1].lower()

        if action == "add":
            if len(parts) < 3:
                return "Usage: /note add <text>"
            nid = _next_id(state["notes"])
            state["notes"].append({"id": nid, "text": parts[2].strip(), "ts": _fmt_dt(_now())})
            save_state(chat_id, state)
            return f"Saved note #{nid}."

        if action == "list":
            notes = state.get("notes", [])
            if not notes:
                return "No notes."
            last = notes[-10:]
            out = []
            for n in last:
                out.append(f"{n.get('id')}) [{n.get('ts')}] {n.get('text')}")
            return "\n".join(out)

        if action == "del":
            if len(parts) < 3:
                return "Usage: /note del <id>"
            try:
                nid = int(parts[2])
                before = len(state["notes"])
                state["notes"] = [n for n in state["notes"] if int(n.get("id", -1)) != nid]
                save_state(chat_id, state)
                return "Deleted." if len(state["notes"]) != before else "Not found."
            except:
                return "Invalid id."

        if action == "clear":
            state["notes"] = []
            save_state(chat_id, state)
            return "Notes cleared."

        return "Usage: /note add|list|del|clear ..."

    # ===== remind =====
    if cmd == "/remind":
        if len(parts) >= 2 and parts[1].lower() == "list":
            rems = sorted(state.get("reminders", []), key=lambda r: r.get("when", ""))
            if not rems:
                return "No reminders."
            out = []
            for r in rems[:30]:
                dt = datetime.fromisoformat(r["when"])
                rep = (r.get("repeat") or "once").lower()
                rep_txt = ""
                if rep == "daily":
                    rep_txt = " (daily)"
                elif rep == "weekly":
                    rep_txt = " (weekly)"
                elif rep == "every":
                    mins = int(r.get("every_minutes", 60))
                    rep_txt = f" (every {mins}m)"
                out.append(f"{r.get('id')}) {_fmt_dt(dt)}{rep_txt} — {r.get('text','')}")
            return "\n".join(out)

        if len(parts) >= 2 and parts[1].lower() == "del":
            if len(parts) < 3:
                return "Usage: /reminder del <id>"
            try:
                rid = int(parts[2])
                before = len(state["reminders"])
                state["reminders"] = [r for r in state.get("reminders", []) if int(r.get("id", -1)) != rid]

                for t in state.get("todos", []):
                    if int(t.get("reminder_id", -1)) == rid:
                        t.pop("reminder_id", None)

                save_state(chat_id, state)
                if len(state["reminders"]) != before:
                    return f"__CANCEL_REMINDER__|{rid}|Deleted reminder #{rid}."
                return "Not found."
            except:
                return "Invalid id."

        m = re.match(r"^/(remind|reminder)\s+todo\s+(\d+)\s+(.+)$", text.strip(), re.IGNORECASE)
        if m:
            todo_id = int(m.group(2))
            schedule_part = m.group(3).strip()

            try:
                idx = todo_id - 1
                t = state.get("todos", [])[idx]
                if t.get("done"):
                    return "That todo is already done."
                todo_text = (t.get("text") or "").strip()
                if not todo_text:
                    return "Todo text is empty."
            except:
                return "Invalid todo id."

            meta, _ = parse_remind(f"/remind {schedule_part} X")
            if not meta:
                return (
                    "Usage:\n"
                    "/reminder todo <id> HH:MM\n"
                    "/reminder todo <id> YYYY-MM-DD HH:MM\n"
                    "/reminder todo <id> in 10m (or 2h)\n"
                    "/reminder todo <id> daily HH:MM\n"
                    "/reminder todo <id> weekly sun HH:MM\n"
                    "/reminder todo <id> every 2h (or 30m)\n"
                )

            dt = meta["when"]
            rid = _next_id(state["reminders"])
            r = {"id": rid, "when": dt.isoformat(), "text": todo_text, "repeat": meta.get("repeat", "once"), "todo_id": todo_id}
            if r["repeat"] == "every":
                r["every_minutes"] = int(meta.get("every_minutes", 60))
            if r["repeat"] == "daily":
                r["time"] = meta.get("time")
            if r["repeat"] == "weekly":
                r["weekday"] = int(meta.get("weekday", 0))
                r["day"] = meta.get("day")
                r["time"] = meta.get("time")

            state["reminders"].append(r)
            state["todos"][idx]["reminder_id"] = rid

            save_state(chat_id, state)
            return f"__SCHEDULE_REMINDER__|{rid}"

        meta, msg = parse_remind(text)
        if not meta or not msg:
            return (
                "Usage:\n"
                "/reminder HH:MM text\n"
                "/reminder YYYY-MM-DD HH:MM text\n"
                "/reminder in 10m text (or 2h)\n"
                "/reminder daily HH:MM text\n"
                "/reminder weekly sun HH:MM text\n"
                "/reminder every 2h text (or 30m)\n"
                "/reminder todo <id> daily HH:MM\n"
            )

        dt = meta["when"]
        rid = _next_id(state["reminders"])
        r = {"id": rid, "when": dt.isoformat(), "text": msg, "repeat": meta.get("repeat", "once")}
        if r["repeat"] == "every":
            r["every_minutes"] = int(meta.get("every_minutes", 60))
        if r["repeat"] == "daily":
            r["time"] = meta.get("time")
        if r["repeat"] == "weekly":
            r["weekday"] = int(meta.get("weekday", 0))
            r["day"] = meta.get("day")
            r["time"] = meta.get("time")

        state["reminders"].append(r)
        save_state(chat_id, state)
        return f"__SCHEDULE_REMINDER__|{rid}"

    # ===== brief =====
    if cmd == "/brief":
        todos = [t for t in state.get("todos", []) if not t.get("done")]
        notes = state.get("notes", [])
        rems = sorted(state.get("reminders", []), key=lambda r: r.get("when", ""))

        out = []
        out.append("📋 Todos:")
        if todos:
            for t in todos[:5]:
                rid = t.get("reminder_id")
                link = f" ⏰#{rid}" if rid else ""
                out.append(f"- {t.get('text')}{link}")
        else:
            out.append("- (none)")

        out.append("")
        out.append("⏰ Reminders:")
        if rems:
            for r in rems[:5]:
                dt = datetime.fromisoformat(r["when"])
                rep = (r.get("repeat") or "once").lower()
                rep_txt = ""
                if rep == "daily":
                    rep_txt = " (daily)"
                elif rep == "weekly":
                    rep_txt = " (weekly)"
                elif rep == "every":
                    rep_txt = f" (every {int(r.get('every_minutes', 60))}m)"
                out.append(f"- {_fmt_dt(dt)}{rep_txt} — {r.get('text')}")
        else:
            out.append("- (none)")

        out.append("")
        out.append("📝 Notes:")
        if notes:
            for n in notes[-3:]:
                out.append(f"- {n.get('text')}")
        else:
            out.append("- (none)")

        return "\n".join(out)

    return "Unknown command. Try: /remember /mem /forget /mode /todo /note /reminder /brief"
