import multiprocessing
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler
import admin_bot
import telegram_bot
import signal
import sys
import http.server
import socketserver
from threading import Thread

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

def main():
    logging.info("Starting both bots...")
    
    # Start health check server
    health_thread = Thread(target=run_health_check_server, daemon=True)
    health_thread.start()
    
    # Start bot processes
    admin_process = multiprocessing.Process(target=run_admin_bot)
    student_process = multiprocessing.Process(target=run_student_bot)
    
    admin_process.start()
    student_process.start()
    
    def signal_handler(signum, frame):
        logging.info("Received termination signal. Shutting down bots...")
        admin_process.terminate()
        student_process.terminate()
        admin_process.join()
        student_process.join()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    admin_process.join()
    student_process.join()

if __name__ == '__main__':
    main() 
