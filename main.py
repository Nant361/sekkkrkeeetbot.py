import multiprocessing
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler
import admin_bot
import telegram_bot
import signal
import sys

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def run_admin_bot():
    """Run the admin bot"""
    try:
        logger.info("Starting Admin Bot...")
        application = Application.builder().token(admin_bot.ADMIN_TOKEN).build()

        # Add handlers
        handlers = [
            CommandHandler("start", admin_bot.start),
            CommandHandler("list", admin_bot.list_users),
            CommandHandler("add", admin_bot.add_user),
            CommandHandler("remove", admin_bot.remove_user),
            CommandHandler("logs", admin_bot.view_logs),
            CommandHandler("getid", admin_bot.get_user_id),
            CommandHandler("chatid", admin_bot.get_chat_id),
            MessageHandler(admin_bot.filters.FORWARDED, admin_bot.get_user_id)
        ]
        
        for handler in handlers:
            application.add_handler(handler)

        logger.info("Admin Bot is ready!")
        application.run_polling(allowed_updates=admin_bot.Update.ALL_TYPES)
            
    except Exception as e:
        logger.error(f"Error in Admin Bot: {str(e)}", exc_info=True)
        sys.exit(1)

def run_student_bot():
    """Run the student search bot"""
    try:
        logger.info("Starting Student Search Bot...")
        application = Application.builder().token(telegram_bot.TOKEN).build()

        # Add handlers
        handlers = [
            CommandHandler("start", telegram_bot.start),
            CommandHandler("cari", telegram_bot.search),
            CommandHandler("regist", telegram_bot.register_user),
            CallbackQueryHandler(telegram_bot.button_callback),
            MessageHandler(telegram_bot.filters.TEXT & ~telegram_bot.filters.COMMAND, telegram_bot.handle_message),
            MessageHandler(telegram_bot.filters.PHOTO, telegram_bot.handle_message),
            MessageHandler(telegram_bot.filters.Document.ALL, telegram_bot.handle_message),
            MessageHandler(telegram_bot.filters.VOICE, telegram_bot.handle_message),
            MessageHandler(telegram_bot.filters.VIDEO, telegram_bot.handle_message),
            MessageHandler(telegram_bot.filters.Sticker.ALL, telegram_bot.handle_message),
            MessageHandler(telegram_bot.filters.LOCATION, telegram_bot.handle_message),
            MessageHandler(telegram_bot.filters.CONTACT, telegram_bot.handle_message),
            MessageHandler(telegram_bot.filters.ANIMATION, telegram_bot.handle_message),
            MessageHandler(telegram_bot.filters.AUDIO, telegram_bot.handle_message)
        ]
        
        for handler in handlers:
            application.add_handler(handler)

        logger.info("Student Search Bot is ready!")
        application.run_polling(allowed_updates=telegram_bot.Update.ALL_TYPES)
            
    except Exception as e:
        logger.error(f"Error in Student Search Bot: {str(e)}", exc_info=True)
        sys.exit(1)

def signal_handler(signum, frame):
    """Handle termination signals"""
    logger.info("Received termination signal. Shutting down bots...")
    sys.exit(0)

def main():
    """Run both bots concurrently"""
    try:
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Starting both bots...")
        
        # Create processes for each bot
        admin_process = multiprocessing.Process(target=run_admin_bot, name="AdminBot")
        student_process = multiprocessing.Process(target=run_student_bot, name="StudentBot")
        
        # Start both processes
        admin_process.start()
        student_process.start()
        
        # Wait for both processes to complete
        admin_process.join()
        student_process.join()
        
    except KeyboardInterrupt:
        logger.info("\nBots stopped by user")
        admin_process.terminate()
        student_process.terminate()
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}", exc_info=True)
        if 'admin_process' in locals():
            admin_process.terminate()
        if 'student_process' in locals():
            student_process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main() 