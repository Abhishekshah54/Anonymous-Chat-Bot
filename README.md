# Anonymous Chat Bot

A Telegram bot that lets users register, exchange messages anonymously via a generated user ID (`auser_id`), and view their account details.

## Features

- User registration with:
  - username
  - password
  - phone number via Telegram contact sharing
- User login flow
- Unique anonymous ID (`auser_id`) generation (32 chars)
- Anonymous one-to-one messaging using `/chat` + recipient `auser_id`
- Chat logs stored per target user
- Basic user details command (`/details`)

## Tech Stack

- Python
- `python-telegram-bot==13.15` (polling mode)

## Project Structure

- `main.py` – Bot handlers, conversation flows, storage logic
- `config.py` – Token file path configuration
- `requirements.txt` – Python dependencies
- `__config__/ttoken.anobot` – Telegram bot token file
- `__log__/login.log` – User records log (created automatically)
- `__chat_user__/` – Per-user private directory by generated `auser_id`
- `chat_user/` – Chat logs grouped by recipient `auser_id`

## Requirements

- Python 3.8+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## Setup

1. Clone or open this folder in VS Code.
2. Create and activate a virtual environment (recommended).
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Add your Telegram bot token to:

```text
__config__/ttoken.anobot
```

The file should contain only the raw token text, for example:

```text
123456789:AAExampleTokenValue
```

## Run

From the project root:

```bash
python main.py
```

The bot starts polling Telegram updates.

## Bot Commands

- `/start` – Welcome and guidance
- `/registration` – Register a new user
- `/login` – Login with username/password
- `/details` – Show your saved details (name, phone, anonymous ID)
- `/logout` – Logout message flow
- `/chat` – Start anonymous chat by entering recipient `auser_id`
- `/cancel` – Cancel current conversation flow

## How Chat Works

1. User A runs `/chat`.
2. User A enters User B's `auser_id`.
3. User A sends message text.
4. Bot forwards the message to User B and includes User A's `auser_id` for reply.
5. User B can reply by starting `/chat` with that ID.

## Notes

- Storage is file-based (no database).
- Data is persisted in plain text logs.
- Existing code uses `eval()` while reading stored records. This is unsafe for untrusted data and should be replaced with a safer format (for example JSON).
- Keep your token file private and never commit real tokens.

## Existing Bot Link

See `Bot Link.txt` for the currently shared bot URL.
