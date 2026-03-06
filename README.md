# Local LLM Telegram Assistant (Beta)

A **Telegram-based AI assistant powered by a locally hosted Large Language Model (LLM)** using **Ollama**.

This project combines natural conversation with deterministic command-based tools to build a lightweight personal AI assistant capable of managing reminders, notes, todos, and persistent memory — all running locally.

> **Status:** Beta version  
> This project is an experimental foundation for building practical personal AI assistants using local LLMs and modular tool integration.

---

# Overview

The assistant is designed around two complementary layers:

### Deterministic Command Layer
Handles structured actions such as:

- reminders  
- todos  
- notes  
- personal memory  
- task summaries  

### LLM Conversation Layer
Handles natural language interaction using a **local LLM through Ollama**, enabling flexible conversations while optionally incorporating user data when relevant.

This hybrid design keeps the assistant both:

- predictable for structured tasks  
- natural for conversational interaction  

---

# Features

Current capabilities include:

- Telegram chatbot interface
- Local LLM chat using **Ollama**
- Personal memory storage
- Todo list management
- Notes system
- Flexible reminder scheduling
- Recurring reminders (daily / weekly / interval)
- Optional short-term conversation context
- Persistent JSON-based storage
- Time-aware prompt injection

The assistant dynamically injects relevant user information (profile, reminders, notes, todos) into the system prompt when needed.

---

# Architecture

```
Telegram
   ↓
Python Bot
   ↓
Command System + LLM Layer
   ↓
Ollama (Local LLM)
```

Core components:

| File | Purpose |
|-----|--------|
| `bot.py` | Main Telegram bot logic, message routing, and scheduling |
| `commands.py` | Deterministic command handling |
| `llm.py` | Wrapper for interacting with the local Ollama model |
| `storage.py` | JSON-based persistence layer for user state |

---

# Example Commands

### Memory

```
/remember age=27
/mem
/forget age
```

### Todos

```
/todo add Finish project
/todo list
/todo done 1
```

### Notes

```
/note add Interesting idea
/note list
```

### Reminders

```
/reminder 18:00 gym
/reminder in 30m drink water
/reminder daily 08:00 vitamins
/reminder weekly sun 21:00 call family
/reminder every 2h stand up
```

### Quick summary

```
/brief
```

---

# Tech Stack

- Python
- python-telegram-bot
- Ollama
- Llama 3
- JSON storage

---

# Requirements

- Python 3.10+
- Ollama installed
- Telegram Bot Token

---

# Installation

Clone the repository:

```bash
git clone https://github.com/HadWiz/local-llm-telegram-assistant.git
cd local-llm-telegram-assistant
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start Ollama:

```bash
ollama serve
```

---

# Configuration

Before running the bot, edit the configuration inside **`bot.py`**.

Insert your Telegram bot credentials:

```python
TOKEN = "YOUR_BOT_TOKEN_HERE"
ALLOWED_USERS = {YOUR_USER_ID}
```

### How to get them

**Bot Token**

Create a new bot using **@BotFather** on Telegram.

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Follow the instructions
4. Copy the bot token that BotFather gives you

**User ID**

To get your Telegram numeric user ID:

1. Search for `@userinfobot` on Telegram
2. Start the bot
3. It will reply with your **numeric user ID**

---

# Running the Bot

Navigate to the bot directory:

```bash
cd local-llm-telegram-assistant
```

Activate the virtual environment

```bash
source venv/bin/activate
```

Start the assistant:

```bash
python3 bot.py
```

Make sure the Ollama server is running:

```bash
ollama serve
```

Once started, the bot will connect to Telegram and begin processing commands and messages.

---

# Project Motivation

This project explores how **local LLMs can be combined with deterministic tools and persistent memory** to build practical AI assistants.

Rather than relying entirely on cloud models, the assistant runs locally and focuses on:

- privacy
- modular architecture
- tool-augmented AI systems
- personal productivity workflows

---

# Future Directions

Planned improvements include:

- API integrations (weather, calendar, email, etc.)
- richer scheduling and planning workflows
- improved natural language command parsing
- hybrid local + cloud LLM routing (e.g., GPT API for complex tasks)
- enhanced long-term memory management
- plugin-style tool system
- multi-user support

---

# Project Status

This repository represents a **Beta prototype** and an ongoing exploration of AI assistants built on top of local LLMs.

The architecture is intentionally modular to allow future expansion.

---

# License

Open for experimentation and learning.
