import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram import Update
import admin_bot
import telegram_bot
import signal
import sys
import http.server
import socketserver
from threading import Thread
import multiprocessing
from telegram.error import Conflict

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Health check server
class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

def run_health_check_server():
    with socketserver.TCPServer(("", 8000), HealthCheckHandler) as httpd:
        httpd.serve_forever()

def setup_admin_bot():
    """Setup the admin bot"""
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
        return application
            
    except Exception as e:
        logger.error(f"Error in Admin Bot setup: {str(e)}", exc_info=True)
        raise

def setup_student_bot():
    """Setup the student search bot"""
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
        return application
            
    except Exception as e:
        logger.error(f"Error in Student Bot setup: {str(e)}", exc_info=True)
        raise

def run_admin_bot():
    """Run admin bot in a separate process"""
    app = setup_admin_bot()
    app.run_polling(allowed_updates=Update.ALL_TYPES)

def run_student_bot():
    """Run student bot in a separate process"""
    app = setup_student_bot()
    app.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    logger.info("Starting both bots...")
    
    # Start health check server
    health_thread = Thread(target=run_health_check_server, daemon=True)
    health_thread.start()
    
    try:
        # Start both bots in separate processes
        admin_process = multiprocessing.Process(target=run_admin_bot)
        student_process = multiprocessing.Process(target=run_student_bot)
        
        admin_process.start()
        student_process.start()
        
        # Wait for processes to complete
        admin_process.join()
        student_process.join()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
        admin_process.terminate()
        student_process.terminate()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        if 'admin_process' in locals():
            admin_process.terminate()
        if 'student_process' in locals():
            student_process.terminate()
        sys.exit(1)

if __name__ == '__main__':
    main() 
