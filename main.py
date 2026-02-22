import os
import logging
import random
import datetime
from pathlib import Path
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from telegram.error import Conflict

import config

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / '__log__'
LOG_FILE = LOG_DIR / 'login.log'
PRIVATE_CHAT_DIR = BASE_DIR / '__chat_user__'
CHAT_DIR = BASE_DIR / 'chat_user'


def reply_safe(update: Update, text: str, **kwargs) -> None:
    message = getattr(update, 'message', None)
    if not message:
        return
    try:
        message.reply_text(text, **kwargs)
    except Exception:
        logger.exception("Failed to send reply to user")


def iter_user_records():
    if not LOG_FILE.exists():
        return
    try:
        with open(LOG_FILE, 'r') as log_file:
            for line_number, line in enumerate(log_file, start=1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    data = eval(raw)
                except Exception:
                    logger.warning("Skipping malformed record in login.log at line %s", line_number)
                    continue
                if isinstance(data, dict):
                    yield data
                else:
                    logger.warning("Skipping non-dict record in login.log at line %s", line_number)
    except OSError:
        logger.exception("Unable to read user records from %s", LOG_FILE)


def ensure_storage() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.touch(exist_ok=True)
    PRIVATE_CHAT_DIR.mkdir(parents=True, exist_ok=True)
    CHAT_DIR.mkdir(parents=True, exist_ok=True)

# Define states for registration
USERNAME, PASSWORD, PHONE_NUMBER, CHECK_EXISTENCE = range(4)

# Define states for login
LOGIN_USERNAME, LOGIN_PASSWORD = range(4, 6)

# Define state for user details
USER_DETAILS = 6

# Define states for chat
CHOOSE_CHAT, CHAT, REPLY = range(7, 10)


# Command: /start
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if is_registered(user_id):
        update.message.reply_text(f"Welcome back! Use /details to see your information. \n use /chat for start chat :)")
    else:
        update.message.reply_text("Welcome! Please use /registration to register or /login to log in.")


# Command: /registration
def registration_start(update: Update, context: CallbackContext) -> int:
    reply_safe(update, "Please enter your desired username:")
    return USERNAME


def registration_username(update: Update, context: CallbackContext) -> int:
    username = (update.message.text or '').strip()

    if len(username) < 3:
        reply_safe(update, "Username must be at least 3 characters. Please enter another username:")
        return USERNAME

    # Check if the username is already in use
    if is_username_exists(username):
        reply_safe(update, "Username already exists. Please choose another username:")
        return USERNAME

    context.user_data['username'] = username
    reply_safe(update, "Please enter your password:")
    return PASSWORD


def registration_password(update: Update, context: CallbackContext) -> int:
    password = (update.message.text or '').strip()
    if len(password) < 4:
        reply_safe(update, "Password must be at least 4 characters. Please enter your password again:")
        return PASSWORD

    context.user_data['password'] = password
    reply_safe(update, "Please tap the button below to share your vCard:")
    button = KeyboardButton(text="Share vCard", request_contact=True)
    keyboard = [[button]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    reply_safe(update, "Please tap the button below to share your vCard:", reply_markup=reply_markup)
    return PHONE_NUMBER


def registration_phone_number(update: Update, context: CallbackContext) -> int:
    if update.message.contact:
        phone_number = (update.message.contact.phone_number or '').strip()

        if not phone_number:
            reply_safe(update, "Invalid contact detected. Please share your contact again using the button.")
            return PHONE_NUMBER

        # Check if the phone number is already in use
        if is_phone_number_exists(phone_number):
            reply_safe(update,
                "This phone number is already associated with an account. "
                "Please log in instead using /login."
            )
            return ConversationHandler.END

        username = context.user_data.get('username')
        password = context.user_data.get('password')
        if not username or not password:
            reply_safe(update, "Registration session expired. Please use /registration and try again.")
            return ConversationHandler.END

        # Generate a random unique ID for the user with a minimum of 32 characters
        auser_id = ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(32))

        # Save user data to a log file
        try:
            with open(LOG_FILE, 'a') as log_file:
                user_data = {
                    'username': username,
                    'password': password,
                    'phone_number': phone_number,
                    'chat_id': update.message.chat_id,
                    'user_id': update.message.from_user.id,
                    'name': update.message.from_user.first_name,
                    'auser_id': auser_id,
                }
                log_file.write(str(user_data) + '\n')
        except OSError:
            logger.exception("Failed to persist registration data")
            reply_safe(update, "We could not save your registration right now. Please try again shortly.")
            return ConversationHandler.END

        # Create a folder with the name of auser_id under the chat_user directory
        user_folder_path = PRIVATE_CHAT_DIR / auser_id
        os.makedirs(user_folder_path, exist_ok=True)

        reply_safe(update,
            f"Registration successful! Your unique ID is {auser_id}. Use /login to log in."
        )
        return ConversationHandler.END
    else:
        reply_safe(update, "Please use the 'Share vCard' button to share your vCard.")
        return PHONE_NUMBER


# Command: /login
def login_start(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if is_registered(user_id):
        reply_safe(update, "Please enter your username:")
        return LOGIN_USERNAME
    else:
        reply_safe(update, "You are not registered. Please use /registration to register first.")
        return ConversationHandler.END


def login_username(update: Update, context: CallbackContext) -> int:
    username = (update.message.text or '').strip()

    if not username:
        reply_safe(update, "Username cannot be empty. Please enter your username:")
        return LOGIN_USERNAME

    # Check if the username exists in the log file
    if is_username_exists(username):
        context.user_data['username'] = username
        reply_safe(update, "Please enter your password:")
        return LOGIN_PASSWORD
    else:
        reply_safe(update, "Invalid username. Please try again or use /registration to register.")
        return ConversationHandler.END


def login_password(update: Update, context: CallbackContext) -> int:
    password = (update.message.text or '').strip()
    username = context.user_data.get('username')

    if not username:
        reply_safe(update, "Login session expired. Please use /login again.")
        return ConversationHandler.END

    # Check if the provided password is correct
    if is_password_correct(username, password):
        reply_safe(update,
            f"Login successful! Welcome back! Use /details to see your information.\nUse /chat for start chat :)"
        )
    else:
        reply_safe(update, "Invalid password. Please try again or use /registration to register.")
    return ConversationHandler.END


# Command: /details
def user_details(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if is_registered(user_id):
        details = get_user_details(user_id)
        reply_safe(update, details)
    else:
        reply_safe(update, "You are not logged in. Please use /login or /registration to log in.")


# Command: /logout
def logout(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if is_registered(user_id):
        # You can add any specific logout logic here if needed
        reply_safe(update, "Logout successful! You have been logged out.")
    else:
        reply_safe(update, "You are not logged in. Please use /login or /registration to log in.")
    return ConversationHandler.END


# Command: /cancel
def cancel(update: Update, context: CallbackContext) -> int:
    reply_safe(update, "Operation cancelled.")
    return ConversationHandler.END


# Check if a username already exists
def is_username_exists(username: str) -> bool:
    for data in iter_user_records() or []:
        if 'username' in data and data['username'] == username:
            return True
    return False


# Check if a phone number already exists
def is_phone_number_exists(phone_number: str) -> bool:
    for data in iter_user_records() or []:
        if 'phone_number' in data and data['phone_number'] == phone_number:
            return True
    return False


# Check if a user is registered
def is_registered(user_id: int) -> bool:
    for data in iter_user_records() or []:
        if 'user_id' in data and data['user_id'] == user_id:
            return True
    return False


# Check if the provided password is correct for the given username
def is_password_correct(username: str, password: str) -> bool:
    for data in iter_user_records() or []:
        if 'username' in data and data['username'] == username and \
                'password' in data and data['password'] == password:
            return True
    return False


# Get user details as a formatted string
def get_user_details(user_id: int) -> str:
    for data in iter_user_records() or []:
        if 'user_id' in data and data['user_id'] == user_id:
            details = (
                f"Name: {data.get('name', 'N/A')}\n"
                f"Phone Number: {data.get('phone_number', 'N/A')}\n"
                f"User ID: {data.get('auser_id', 'N/A')}"
            )
            return details
    return "User details not found."


# Register a new user
def register_user(username: str, password: str, phone_number: str, chat_id: int, user_id: int, name: str) -> None:
    # Generate a random unique ID for the user with a minimum of 32 characters
    auser_id = ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(32))

    # Save user data to a log file
    with open(LOG_FILE, 'a') as log_file:
        user_data = {
            'username': username,
            'password': password,
            'phone_number': phone_number,
            'chat_id': chat_id,
            'user_id': user_id,
            'name': name,
            'auser_id': auser_id,
        }
        log_file.write(str(user_data) + '\n')

    # Create a folder with the name of auser_id under the chat_user directory
    user_folder_path = PRIVATE_CHAT_DIR / auser_id
    os.makedirs(user_folder_path, exist_ok=True)

# Command: /chat
def chat_start(update: Update, context: CallbackContext) -> int:
    if not is_registered(update.message.from_user.id):
        reply_safe(update, "Please register first using /registration before starting a chat.")
        return ConversationHandler.END
    reply_safe(update, "Please enter the auser_id you want to chat with:")
    return CHOOSE_CHAT


def choose_chat(update: Update, context: CallbackContext) -> int:
    auser_id = (update.message.text or '').strip()

    if not auser_id:
        reply_safe(update, "auser_id cannot be empty. Please enter a valid auser_id:")
        return CHOOSE_CHAT

    # Check if the provided auser_id is valid
    if is_valid_auser_id(auser_id) and get_user_data_by_auser_id(auser_id):
        context.user_data['auser_id'] = auser_id
        reply_safe(update, f"Chat with {auser_id} initiated. You can start typing your messages.")
        return CHAT
    else:
        reply_safe(update, "Invalid auser_id. Please try again or use /chat to start a new chat.")
        return CHOOSE_CHAT


def chat(update: Update, context: CallbackContext) -> None:
    auser_id = context.user_data.get('auser_id')
    if not auser_id:
        reply_safe(update, "No active chat. Use /chat to start a new chat.")
        return

    target_user_data = get_user_data_by_auser_id(auser_id)
    if not target_user_data:
        reply_safe(update, "The selected auser_id does not exist. Please start again with /chat.")
        return

    # Get user data
    user_data = get_user_data(update.message.from_user.id)
    user_name = user_data.get('name')
    if not user_name:
        reply_safe(update, "Could not find your account details. Please use /registration first.")
        return

    # Get the user's auser_id
    user_auser_id = user_data.get('auser_id')

    # Format the message with the user's name and message
    message_part1 = f"({user_name}): {update.message.text}\n\nTo reply, please use /chat and provide this id: "
    message_part2 = f"{user_auser_id}"

    # Get the chat folder path
    chat_folder_path = CHAT_DIR / auser_id

    # Create the chat_user directory if it doesn't exist
    os.makedirs(chat_folder_path, exist_ok=True)

    # Get the chat log file path
    chat_log_file_path = chat_folder_path / 'chat_log.log'

    # Create the chat_log.log file if it doesn't exist
    with open(chat_log_file_path, 'a'):
        pass  # This creates an empty file if it doesn't exist

    # Append the message to the chat log file
    with open(chat_log_file_path, 'a') as chat_log_file:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        chat_log_file.write(f"{timestamp} - {user_name}: {update.message.text}\n")

    # Send the user's name and message as the first part
    if not send_message_to_user(context, auser_id, message_part1):
        reply_safe(update, "Message could not be delivered. The recipient may have blocked the bot or is unavailable.")
        return

    # Send the instruction to reply with the auser_id as the second part
    if not send_message_to_user(context, auser_id, message_part2):
        reply_safe(update, "Message could not be delivered. The recipient may have blocked the bot or is unavailable.")
        return
    

    return REPLY


def reply(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    auser_id = context.user_data.get('auser_id')
    if not auser_id:
        reply_safe(update, "No active chat target found. Please start with /chat.")
        return ConversationHandler.END

    if not get_user_data_by_auser_id(auser_id):
        reply_safe(update, "The recipient is no longer available. Please start again with /chat.")
        return ConversationHandler.END

    # Get user data
    user_data = get_user_data(user_id)
    user_name = user_data.get('name')
    if not user_name:
        reply_safe(update, "Could not find your account details. Please use /registration first.")
        return ConversationHandler.END

    # Format the message
    formatted_message = f"({user_name}): {update.message.text}"

    # Get the chat folder path
    chat_folder_path = CHAT_DIR / auser_id

    os.makedirs(chat_folder_path, exist_ok=True)

    # Get the chat log file path
    chat_log_file_path = chat_folder_path / 'chat_log.log'

    # Append the message to the chat log file
    with open(chat_log_file_path, 'a') as chat_log_file:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        chat_log_file.write(f"{timestamp} - {user_name}: {update.message.text}\n")

    # Send the formatted message to the other user
    if not send_message_to_user(context, auser_id, formatted_message):
        reply_safe(update, "Message could not be delivered. The recipient may have blocked the bot or is unavailable.")
        return ConversationHandler.END

    return REPLY


# Check if the provided auser_id is valid
def is_valid_auser_id(auser_id: str) -> bool:
    return len(auser_id) >= 32


# Modified send_message_to_user function with context parameter
def send_message_to_user(context: CallbackContext, auser_id: str, message: str) -> bool:
    user_data = get_user_data_by_auser_id(auser_id)
    if user_data:
        chat_id = user_data.get('chat_id')
        if not chat_id:
            return False

        try:
            context.bot.send_message(chat_id=chat_id, text=message)
            return True
        except Exception:
            logger.exception("Failed to send message to chat_id=%s", chat_id)
            return False
    return False


# Get user data by auser_id
def get_user_data_by_auser_id(auser_id: str) -> dict:
    for data in iter_user_records() or []:
        if 'auser_id' in data and data['auser_id'] == auser_id:
            return data
    return {}


# Get user data by user_id
def get_user_data(user_id: int) -> dict:
    for data in iter_user_records() or []:
        if 'user_id' in data and data['user_id'] == user_id:
            return data
    return {}


def error_handler(update: object, context: CallbackContext) -> None:
    if isinstance(context.error, Conflict):
        logger.error("Polling conflict detected: another bot instance is using this token.")
        return
    logger.exception("Unhandled exception while processing update", exc_info=context.error)

    try:
        if isinstance(update, Update) and update.effective_message:
            update.effective_message.reply_text(
                "Something went wrong while processing your request. Please try again or use /cancel."
            )
    except Exception:
        logger.exception("Failed to send error message to user")


def main() -> None:
    ensure_storage()

    # Read the Telegram token from config.tx`_token
    with open(config.t_token, 'r') as token_file:
        token = token_file.read().strip()

    updater = Updater(token)
    dp = updater.dispatcher

    registration_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('registration', registration_start)],
        states={
            USERNAME: [MessageHandler(Filters.text & ~Filters.command, registration_username)],
            PASSWORD: [MessageHandler(Filters.text & ~Filters.command, registration_password)],
            PHONE_NUMBER: [MessageHandler(Filters.contact & ~Filters.command, registration_phone_number)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    login_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('login', login_start)],
        states={
            LOGIN_USERNAME: [MessageHandler(Filters.text & ~Filters.command, login_username)],
            LOGIN_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, login_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    chat_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('chat', chat_start)],
        states={
            CHOOSE_CHAT: [MessageHandler(Filters.text & ~Filters.command, choose_chat)],
            CHAT: [MessageHandler(Filters.text & ~Filters.command, chat)],
            REPLY: [MessageHandler(Filters.text & ~Filters.command, reply)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )



    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(registration_conv_handler)
    dp.add_handler(login_conv_handler)
    dp.add_handler(CommandHandler('details', user_details))
    dp.add_handler(CommandHandler('logout', logout))
    dp.add_handler(chat_conv_handler)
    dp.add_error_handler(error_handler)

    # Start the Bot
    try:
        updater.bot.delete_webhook(drop_pending_updates=True)
    except TypeError:
        updater.bot.delete_webhook()

    updater.start_polling(drop_pending_updates=True)

    # Run the bot until you send a signal to stop it
    updater.idle()


if __name__ == '__main__':
    main()
