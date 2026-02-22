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
- User-side error handling with clear feedback for invalid/empty input and delivery issues

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

## Validation & Error Handling

- Registration input checks:
  - Username must be at least 3 characters
  - Password must be at least 4 characters
  - Contact share is required for phone capture
- Login and chat flows return clear messages if session data is missing/expired.
- Chat now validates that target `auser_id` exists (not just length check).
- If message delivery fails (for example recipient blocked bot or chat is unavailable), sender gets a friendly error.
- Malformed lines inside `__log__/login.log` are skipped safely instead of crashing the bot.
- Global fallback error message is sent to users when unexpected handler exceptions occur.

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
- `/logout` currently returns a confirmation message but does not maintain a persistent authenticated session state.

## Existing Bot Link

See `Bot Link.txt` for the currently shared bot URL.
