import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

def ollama_chat(model: str, messages: list[dict], timeout: int = 120) -> str:
    r = requests.post(
        OLLAMA_URL,
        json={"model": model, "messages": messages, "stream": False},
        timeout=timeout,
    )
    r.raise_for_status()
    data = r.json()
    return (data.get("message", {}).get("content", "") or "").strip()
