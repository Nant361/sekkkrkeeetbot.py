import asyncio
import logging
import multiprocessing
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import json
import os
from pddikti_api import login_pddikti, search_student, get_student_detail
import aiohttp
import http.server
import socketserver
import signal
import sys

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot tokens
ADMIN_BOT_TOKEN = os.getenv('ADMIN_BOT_TOKEN')
STUDENT_BOT_TOKEN = os.getenv('STUDENT_BOT_TOKEN')

# Health check server
def run_health_check_server():
    """Run a simple HTTP server for health checks"""
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", 8000), handler) as httpd:
        print("Health check server running on port 8000")
        httpd.serve_forever()

def setup_admin_bot():
    """Setup admin bot application"""
    admin_app = Application.builder().token(ADMIN_BOT_TOKEN).build()
    
    # Add handlers
    admin_app.add_handler(CommandHandler("start", start))
    admin_app.add_handler(CommandHandler("cari", search))
    admin_app.add_handler(CommandHandler("adduser", add_user))
    admin_app.add_handler(CommandHandler("removeuser", remove_user))
    admin_app.add_handler(CommandHandler("listusers", list_users))
    admin_app.add_handler(CallbackQueryHandler(handle_callback))
    
    return admin_app

def setup_student_bot():
    """Setup student bot application"""
    student_app = Application.builder().token(STUDENT_BOT_TOKEN).build()
    
    # Add handlers
    student_app.add_handler(CommandHandler("start", start))
    student_app.add_handler(CommandHandler("cari", search))
    student_app.add_handler(CallbackQueryHandler(handle_callback))
    
    return student_app

def run_admin_bot():
    """Run admin bot in a separate process"""
    admin_app = setup_admin_bot()
    print("Starting Admin Bot...")
    admin_app.run_polling(allowed_updates=Update.ALL_TYPES)

def run_student_bot():
    """Run student bot in a separate process"""
    student_app = setup_student_bot()
    print("Starting Student Bot...")
    student_app.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main function to run both bots"""
    # Start health check server in a separate process
    health_check_process = multiprocessing.Process(target=run_health_check_server)
    health_check_process.start()
    
    # Start admin bot in a separate process
    admin_process = multiprocessing.Process(target=run_admin_bot)
    admin_process.start()
    
    # Start student bot in a separate process
    student_process = multiprocessing.Process(target=run_student_bot)
    student_process.start()
    
    try:
        # Wait for all processes to complete
        admin_process.join()
        student_process.join()
        health_check_process.join()
    except KeyboardInterrupt:
        print("\nShutting down...")
        # Terminate all processes
        admin_process.terminate()
        student_process.terminate()
        health_check_process.terminate()
        sys.exit(0)

if __name__ == '__main__':
    main() 
