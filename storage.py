import json
import os
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

def _path(chat_id: int) -> str:
    return os.path.join(DATA_DIR, f"{chat_id}.json")

def list_chat_ids() -> list[int]:
    ids = []
    for name in os.listdir(DATA_DIR):
        if name.endswith(".json"):
            base = name[:-5]
            try:
                ids.append(int(base))
            except:
                pass
    return ids

def load_state(chat_id: int) -> dict[str, Any]:
    p = _path(chat_id)
    if not os.path.exists(p):
        return {
            "profile": {},
            "mode": "normal",
            "context": [],
            "todos": [],
            "notes": [],
            "reminders": []
        }
    with open(p, "r", encoding="utf-8") as f:
        state = json.load(f)

    # Backward-compatible defaults
    state.setdefault("profile", {})
    state.setdefault("mode", "normal")
    state.setdefault("context", [])
    state.setdefault("todos", [])
    state.setdefault("notes", [])
    state.setdefault("reminders", [])
    return state

def save_state(chat_id: int, state: dict[str, Any]) -> None:
    with open(_path(chat_id), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def add_context(state: dict, role: str, content: str, max_turns: int = 10) -> None:
    state["context"].append({"role": role, "content": content})
    state["context"] = state["context"][-(max_turns * 2):]
