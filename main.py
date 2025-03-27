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

# Verify tokens are set
if not ADMIN_BOT_TOKEN or not STUDENT_BOT_TOKEN:
    raise ValueError("Both ADMIN_BOT_TOKEN and STUDENT_BOT_TOKEN must be set in environment variables")

# Handler functions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "Welcome to the PDDikti Student Search Bot!\n\n"
        "Use /cari [nama/nim] to search for students."
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cari command"""
    if not context.args:
        await update.message.reply_text("Please provide a search term. Example: /cari John Doe")
        return

    keyword = " ".join(context.args)
    await update.message.reply_text(f"Searching for: {keyword}")
    # Add your search logic here

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /adduser command (admin only)"""
    if not context.args:
        await update.message.reply_text("Please provide a user ID. Example: /adduser 123456789")
        return
    
    user_id = context.args[0]
    # Add your user management logic here
    await update.message.reply_text(f"Added user: {user_id}")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removeuser command (admin only)"""
    if not context.args:
        await update.message.reply_text("Please provide a user ID. Example: /removeuser 123456789")
        return
    
    user_id = context.args[0]
    # Add your user management logic here
    await update.message.reply_text(f"Removed user: {user_id}")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /listusers command (admin only)"""
    # Add your user listing logic here
    await update.message.reply_text("List of users:\n- User 1\n- User 2")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(f"Selected option: {query.data}")

# Health check server
def run_health_check_server():
    """Run a simple HTTP server for health checks"""
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", 8000), handler) as httpd:
        print("Health check server running on port 8000")
        httpd.serve_forever()

def setup_admin_bot():
    """Setup admin bot application"""
    try:
        admin_app = Application.builder().token(ADMIN_BOT_TOKEN).build()
        
        # Add handlers
        admin_app.add_handler(CommandHandler("start", start))
        admin_app.add_handler(CommandHandler("cari", search))
        admin_app.add_handler(CommandHandler("adduser", add_user))
        admin_app.add_handler(CommandHandler("removeuser", remove_user))
        admin_app.add_handler(CommandHandler("listusers", list_users))
        admin_app.add_handler(CallbackQueryHandler(handle_callback))
        
        return admin_app
    except Exception as e:
        print(f"Error setting up admin bot: {str(e)}")
        raise

def setup_student_bot():
    """Setup student bot application"""
    try:
        student_app = Application.builder().token(STUDENT_BOT_TOKEN).build()
        
        # Add handlers
        student_app.add_handler(CommandHandler("start", start))
        student_app.add_handler(CommandHandler("cari", search))
        student_app.add_handler(CallbackQueryHandler(handle_callback))
        
        return student_app
    except Exception as e:
        print(f"Error setting up student bot: {str(e)}")
        raise

def run_admin_bot():
    """Run admin bot in a separate process"""
    try:
        admin_app = setup_admin_bot()
        print("Starting Admin Bot...")
        admin_app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print(f"Error running admin bot: {str(e)}")
        raise

def run_student_bot():
    """Run student bot in a separate process"""
    try:
        student_app = setup_student_bot()
        print("Starting Student Bot...")
        student_app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print(f"Error running student bot: {str(e)}")
        raise

def main():
    """Main function to run both bots"""
    try:
        # Start health check server in a separate process
        health_check_process = multiprocessing.Process(target=run_health_check_server)
        health_check_process.start()
        
        # Start admin bot in a separate process
        admin_process = multiprocessing.Process(target=run_admin_bot)
        admin_process.start()
        
        # Start student bot in a separate process
        student_process = multiprocessing.Process(target=run_student_bot)
        student_process.start()
        
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
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 
