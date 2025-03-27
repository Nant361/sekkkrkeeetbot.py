import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    filters,
    ContextTypes
)
import asyncio
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
import aiohttp
from pddikti_api import login_pddikti, search_student, get_student_detail

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get tokens from environment variables
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_BOT_TOKEN = os.getenv('ADMIN_BOT_TOKEN')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))

# File untuk menyimpan data pengguna yang diizinkan
ALLOWED_USERS_FILE = "allowed_users.json"

def load_allowed_users():
    """Load allowed users from JSON file"""
    try:
        print("\n=== Loading Allowed Users ===")
        if not os.path.exists(ALLOWED_USERS_FILE):
            print(f"Warning: {ALLOWED_USERS_FILE} does not exist")
            return {"users": []}
            
        with open(ALLOWED_USERS_FILE, 'r') as f:
            data = json.load(f)
            print(f"Raw data loaded: {json.dumps(data, indent=2)}")
            
            # Ensure data has correct structure
            if isinstance(data, dict) and "users" in data:
                print("Data has correct dictionary structure")
                return data
            elif isinstance(data, list):
                print("Converting list to dictionary structure")
                return {"users": data}
            else:
                print("Invalid data structure, returning empty user list")
                return {"users": []}
                
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {str(e)}")
        return {"users": []}
    except Exception as e:
        print(f"Error loading allowed users: {str(e)}")
        return {"users": []}

def is_user_allowed(user_id):
    """Check if user is allowed to use the bot"""
    try:
        allowed_users = load_allowed_users()
        print(f"\n=== Checking User Permission ===")
        print(f"User ID: {user_id}")
        print(f"Allowed Users: {json.dumps(allowed_users, indent=2)}")
        
        if not isinstance(allowed_users, dict):
            print("Error: allowed_users is not a dictionary")
            return False
            
        if "users" not in allowed_users:
            print("Error: 'users' key not found in allowed_users")
            return False
            
        is_allowed = any(user['id'] == user_id for user in allowed_users.get('users', []))
        print(f"Is User Allowed: {is_allowed}")
        return is_allowed
        
    except Exception as e:
        print(f"Error in is_user_allowed: {str(e)}")
        return False

async def check_user_permission(update: Update) -> bool:
    """Check if user has permission to use the bot"""
    user_id = update.effective_user.id
    if not is_user_allowed(user_id):
        await update.message.reply_text("❌ Maaf, Anda tidak memiliki akses ke bot ini.")
        return False
    return True

async def send_notification_to_admin(user_id: int, username: str, message: str):
    """Send notification to admin about user activity"""
    try:
        print("\n=== Sending Notification ===")
        print(f"ADMIN_BOT_TOKEN: {ADMIN_BOT_TOKEN[:10]}...")
        print(f"ADMIN_CHAT_ID: {ADMIN_CHAT_ID}")
        
        # Validate tokens and chat ID
        if not ADMIN_BOT_TOKEN:
            print("Error: ADMIN_BOT_TOKEN is empty")
            return
        if not ADMIN_CHAT_ID:
            print("Error: ADMIN_CHAT_ID is empty")
            return
            
        notification = (
            f"📱 *Pesan Baru dari User*\n\n"
            f"⏰ Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"👤 User ID: `{user_id}`\n"
            f"Username: @{username}\n"
            f"Pesan: {message}"
        )
        
        url = f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": ADMIN_CHAT_ID,
            "text": notification,
            "parse_mode": "Markdown"
        }
        
        print(f"Sending request to: {url}")
        print(f"Request data: {json.dumps(data, indent=2)}")
        
        # Use aiohttp with timeout
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(url, json=data) as response:
                    print(f"Response status code: {response.status}")
                    response_text = await response.text()
                    print(f"Response text: {response_text}")
                    
                    if response.status != 200:
                        logger.error(f"Failed to send notification: {response_text}")
                        print(f"Error sending notification: {response_text}")
                    else:
                        print(f"Notification sent successfully to admin")
            except aiohttp.ClientError as e:
                print(f"Network error: {str(e)}")
                logger.error(f"Network error sending notification: {str(e)}")
            except asyncio.TimeoutError as e:
                print(f"Timeout error: {str(e)}")
                logger.error(f"Timeout error sending notification: {str(e)}")
            
    except Exception as e:
        logger.error(f"Failed to send notification to admin: {str(e)}")
        print(f"Error sending notification: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all incoming messages"""
    try:
        print("\n=== Handling Message ===")
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        print(f"User ID: {user_id}")
        print(f"Username: {username}")
        
        # Get message type and content
        message = update.message
        if not message:
            print("Error: No message found in update")
            return
            
        # Check if we're waiting for search input
        if context.user_data.get('waiting_for_search'):
            # Clear the waiting flag
            context.user_data.pop('waiting_for_search', None)
            
            # Get the search keyword
            keyword = message.text
            
            # Show initial progress bar
            progress_message = await show_progress(update, context, 5)
            
            # Update progress to 20%
            await update_progress(progress_message, 2)
            await asyncio.sleep(0.5)
            
            # Login ke PDDikti untuk user ini (fresh login)
            await update_progress(progress_message, 4)
            print(f"\n=== Starting fresh login for user {user_id} ===")
            
            # Buat session baru untuk setiap user dengan timeout yang lebih lama
            timeout = aiohttp.ClientTimeout(total=60)  # 60 detik timeout
            session = aiohttp.ClientSession(timeout=timeout)
            context.user_data['session'] = session  # Simpan session di context user
            
            try:
                # Login dengan session baru
                i_iduser, id_organisasi, pm_token = await login_pddikti(session)
                if not i_iduser or not id_organisasi or not pm_token:
                    raise Exception("Login gagal")
                    
                print(f"Login successful for user {user_id}")
                await asyncio.sleep(0.5)
                
                # Update progress to 60%
                await update_progress(progress_message, 6)
                
                # Cari mahasiswa dengan token baru
                print(f"Searching with fresh token for user {user_id}")
                mahasiswa_list = await search_student(keyword, i_iduser, pm_token, session)
                
                if not mahasiswa_list:
                    await progress_message.edit_text("❌ Tidak ada mahasiswa ditemukan.")
                    return

                # Update progress to 100% after finding students
                await update_progress(progress_message, 10)
                await asyncio.sleep(0.5)

                # Buat keyboard inline untuk pilihan mahasiswa
                keyboard = []
                for idx, mhs in enumerate(mahasiswa_list, 1):
                    nama_pt = mhs['namapt']
                    nama_pt = nama_pt.replace('Universitas', 'Univ.')
                    nama_pt = nama_pt.replace('Institut', 'Inst.')
                    nama_pt = nama_pt.replace('Sekolah Tinggi', 'ST')
                    nama_pt = nama_pt.replace('Politeknik', 'Polit.')
                    
                    if len(nama_pt) > 20:
                        nama_pt = nama_pt[:17] + "..."
                    
                    button_text = f"{idx}. {mhs['nm_pd']} ({nama_pt})"
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            button_text,
                            callback_data=f"mhs_{idx}"
                        )
                    ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Simpan data mahasiswa dan token baru di context user ini
                context.user_data['mahasiswa_list'] = mahasiswa_list
                context.user_data['i_iduser'] = i_iduser
                context.user_data['id_organisasi'] = id_organisasi
                context.user_data['pm_token'] = pm_token

                await progress_message.edit_text(
                    "✅ Daftar Mahasiswa Ditemukan:\n"
                    "Silakan pilih mahasiswa untuk melihat detail:",
                    reply_markup=reply_markup
                )
                
            finally:
                # Jangan tutup session di sini, biarkan tetap terbuka untuk digunakan nanti
                pass
                
        else:
            # Handle other types of messages as before
            if message.photo:
                message_text = f"[Photo] {message.caption if message.caption else 'No caption'}"
            elif message.document:
                message_text = f"[Document] {message.document.file_name}"
            elif message.voice:
                message_text = "[Voice Message]"
            elif message.video:
                message_text = f"[Video] {message.caption if message.caption else 'No caption'}"
            elif message.sticker:
                message_text = f"[Sticker] {message.sticker.emoji}"
            elif message.location:
                message_text = f"[Location] {message.location.latitude}, {message.location.longitude}"
            elif message.contact:
                message_text = f"[Contact] {message.contact.first_name} {message.contact.last_name}"
            elif message.animation:
                message_text = "[Animation]"
            elif message.audio:
                message_text = f"[Audio] {message.audio.title if message.audio.title else 'No title'}"
            else:
                message_text = message.text if message.text else "Unknown message"
            
            print(f"Message text: {message_text}")
            
            # Send notification to admin for every message
            print("Sending notification to admin...")
            try:
                await send_notification_to_admin(user_id, username, message_text)
                print("Notification sent successfully")
            except Exception as e:
                print(f"Failed to send notification: {str(e)}")
                logger.error(f"Failed to send notification: {str(e)}")
            
            # Check permission after sending notification
            if not await check_user_permission(update):
                return
            
    except Exception as e:
        print(f"Error in handle_message: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

async def cleanup_user_session(context: ContextTypes.DEFAULT_TYPE):
    """Cleanup user session when done"""
    if 'session' in context.user_data:
        try:
            await context.user_data['session'].close()
        except Exception as e:
            logger.error(f"Error closing session: {str(e)}")
        finally:
            del context.user_data['session']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    # Cleanup any existing session
    await cleanup_user_session(context)
    
    await send_notification_to_admin(user_id, username, "/start")
    await update.message.reply_text(
        "🔍 I can search for any student data across Indonesia\n\n"
        "📝 How to use:\n"
        "• Search by name: /cari [nama]\n"
        "• Search by NIM: /cari [nim]\n\n"
        "📌 Examples:\n"
        "• /cari Ahmad Fauzi\n"
        "• /cari 2020123456\n"
        "• /cari Siti Nurhaliza\n"
        "• /cari 2020987654\n\n"
        "💡 Tips:\n"
        "• You can search using full name or NIM\n"
        "• Results will show student's complete information\n"
        "• Click on any result to see more details\n\n"
        "👨‍💻 Developed by Nant\n"
        "✈️ Contact: @nant12_bot"
    )

async def show_progress(update: Update, context: ContextTypes.DEFAULT_TYPE, total_steps: int):
    """Show progress bar during search"""
    progress_message = await update.message.reply_text("🔍 Mencari data mahasiswa...\n[▱▱▱▱▱▱▱▱▱▱] 0%")
    return progress_message

async def update_progress(progress_message, progress: int):
    """Update progress bar with given percentage"""
    bar = "▰" * progress + "▱" * (10 - progress)
    await progress_message.edit_text(f"🔍 Mencari data mahasiswa...\n[{bar}] {progress*10}%")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command"""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        print(f"\n=== Handling Search Command ===")
        print(f"User ID: {user_id}")
        print(f"Username: {username}")
        
        # Check permission after /cari command
        allowed_users = load_allowed_users()
        print(f"Loaded allowed users: {json.dumps(allowed_users, indent=2)}")
        
        is_allowed = any(user.get('id') == user_id for user in allowed_users.get('users', []))
        print(f"Is user {user_id} allowed: {is_allowed}")
        
        if not is_allowed:
            print(f"Access denied for user {user_id}")
            # Send notification to admin
            await send_notification_to_admin(user_id, username, "Unauthorized access attempt")
            # Send restriction message to user
            restriction_message = (
                "⚠️ <b>Akses Terbatas</b>\n\n"
                "Maaf, Anda belum memiliki akses untuk menggunakan fitur ini.\n"
                "Silakan hubungi admin untuk mendapatkan akses.\n\n"
                "Contact: @nant12_bot"
            )
            await update.message.reply_text(
                restriction_message,
                parse_mode='HTML'
            )
            return
        
        if not context.args:
            await send_notification_to_admin(user_id, username, "/cari (empty query)")
            await update.message.reply_text(
                "Silakan masukkan nama mahasiswa yang ingin dicari.\n"
                "Contoh: /cari John Doe",
                reply_markup=ForceReply(selective=True)
            )
            return

        # Get search keyword
        keyword = " ".join(context.args)
        print(f"Search keyword: {keyword}")
        
        # Check for forbidden search (except for admin)
        if user_id != 5705926766:
            forbidden_keywords = [
                "azmi ridho rinanta",
                "21523023",
                "universitas islam indonesia"
            ]
            
            # Convert keyword to lowercase for case-insensitive comparison
            keyword_lower = keyword.lower()
            
            # Check if any forbidden keyword is in the search
            if any(forbidden in keyword_lower for forbidden in forbidden_keywords):
                await update.message.reply_text(
                    "⚠️ *PERINGATAN!*\n\n"
                    "Permintaan terlarang untuk lord kami, dilarang mencarinya atau anda terkena ban permanen !",
                    parse_mode='Markdown'
                )
                return

        # Add to search history
        if 'search_history' not in context.user_data:
            context.user_data['search_history'] = []
        context.user_data['search_history'].append(keyword)
        if len(context.user_data['search_history']) > 10:
            context.user_data['search_history'].pop(0)

        await send_notification_to_admin(user_id, username, f"/cari {keyword}")
        
        try:
            # Show initial progress bar
            progress_message = await show_progress(update, context, 5)
            
            # Update progress to 20%
            await update_progress(progress_message, 2)
            await asyncio.sleep(0.5)
            
            # Clear old tokens and data
            context.user_data.clear()
            context.user_data['search_history'] = [keyword]
            
            # Login ke PDDikti untuk user ini (fresh login)
            await update_progress(progress_message, 4)
            print(f"\n=== Starting fresh login for user {user_id} ===")
            
            # Buat session baru untuk setiap user dengan timeout yang lebih lama
            timeout = aiohttp.ClientTimeout(total=60)  # 60 detik timeout
            session = aiohttp.ClientSession(timeout=timeout)
            context.user_data['session'] = session  # Simpan session di context user
            
            try:
                # Login dengan session baru
                i_iduser, id_organisasi, pm_token = await login_pddikti(session)
                if not i_iduser or not id_organisasi or not pm_token:
                    raise Exception("Login gagal")
                    
                print(f"Login successful for user {user_id}")
                await asyncio.sleep(0.5)
                
                # Update progress to 60%
                await update_progress(progress_message, 6)
                
                # Cari mahasiswa dengan token baru
                print(f"Searching with fresh token for user {user_id}")
                mahasiswa_list = await search_student(keyword, i_iduser, pm_token, session)
                
                if not mahasiswa_list:
                    await progress_message.edit_text("❌ Tidak ada mahasiswa ditemukan.")
                    return

                # Update progress to 100% after finding students
                await update_progress(progress_message, 10)
                await asyncio.sleep(0.5)

                # Buat keyboard inline untuk pilihan mahasiswa
                keyboard = []
                for idx, mhs in enumerate(mahasiswa_list, 1):
                    nama_pt = mhs['namapt']
                    nama_pt = nama_pt.replace('Universitas', 'Univ.')
                    nama_pt = nama_pt.replace('Institut', 'Inst.')
                    nama_pt = nama_pt.replace('Sekolah Tinggi', 'ST')
                    nama_pt = nama_pt.replace('Politeknik', 'Polit.')
                    
                    if len(nama_pt) > 20:
                        nama_pt = nama_pt[:17] + "..."
                    
                    button_text = f"{idx}. {mhs['nm_pd']} ({nama_pt})"
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            button_text,
                            callback_data=f"mhs_{idx}"
                        )
                    ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Simpan data mahasiswa dan token baru di context user ini
                context.user_data['mahasiswa_list'] = mahasiswa_list
                context.user_data['i_iduser'] = i_iduser
                context.user_data['id_organisasi'] = id_organisasi
                context.user_data['pm_token'] = pm_token

                await progress_message.edit_text(
                    "✅ Daftar Mahasiswa Ditemukan:\n"
                    "Silakan pilih mahasiswa untuk melihat detail:",
                    reply_markup=reply_markup
                )
                
            finally:
                # Jangan tutup session di sini, biarkan tetap terbuka untuk digunakan nanti
                pass
                
        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            await progress_message.edit_text(f"❌ Terjadi kesalahan: {str(e)}")
            # Tutup session jika terjadi error
            if 'session' in context.user_data:
                await context.user_data['session'].close()
                del context.user_data['session']

    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)}")

async def show_loading(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str):
    """Show loading animation"""
    loading_message = await update.callback_query.message.reply_text(f"⏳ {message}")
    return loading_message

async def format_brief_detail(detail):
    """Format brief student detail"""
    try:
        message = "👨‍🎓 *Detail Mahasiswa*\n\n"
        
        if 'dataumum' in detail:
            dataumum = detail['dataumum']
            message += "📌 *Data Umum:*\n"
            message += f"👤 Nama: `{dataumum.get('nm_pd', 'N/A')}`\n"
            message += f"🎓 NIM: `{dataumum.get('nipd', 'N/A')}`\n"
            message += f"📚 Program Studi: `{dataumum.get('namaprodi', 'N/A')}`\n"
            message += f"🏫 Perguruan Tinggi: `{dataumum.get('namapt', 'N/A')}`\n"
            message += f"📊 Jenjang: `{dataumum.get('namajenjang', 'N/A')}`\n\n"
        
        if 'datakuliah' in detail and detail['datakuliah']:
            latest_semester = detail['datakuliah'][-1]
            message += "📊 *Status Terkini:*\n"
            message += f"📅 Semester: `{latest_semester.get('id_smt', 'N/A')}`\n"
            message += f"📋 Status: `{latest_semester.get('nm_stat_mhs', 'N/A')}`\n"
            
            # Format IPK dengan 2 desimal
            ipk = latest_semester.get('ipke')
            if ipk is not None and ipk != 0:
                try:
                    ipk = f"{float(ipk):.2f}"
                except (ValueError, TypeError):
                    ipk = "N/A"
            else:
                ipk = "N/A"
                
            message += f"📈 IPK: `{ipk}`\n"
            message += f"📚 Total SKS: `{latest_semester.get('sks_total', 'N/A')}`\n"
        
        return message
    except Exception as e:
        logger.error(f"Error formatting brief detail: {str(e)}")
        return "❌ Terjadi kesalahan saat memformat data mahasiswa."

def format_student_detail(detail):
    """Format student detail into readable message"""
    try:
        message_parts = []
        
        # Part 1: Data Umum
        message = "👨‍🎓 *Detail Lengkap Mahasiswa (1/3)*\n\n"
        if 'dataumum' in detail:
            dataumum = detail['dataumum']
            message += "📌 *Data Umum:*\n"
            message += f"👤 Nama Lengkap: `{dataumum.get('nm_pd', 'N/A')}`\n"
            message += f"🎓 NIM: `{dataumum.get('nipd', 'N/A')}`\n"
            message += f"🆔 NISN: `{dataumum.get('nisn', 'N/A')}`\n"
            message += f"📚 Program Studi: `{dataumum.get('namaprodi', 'N/A')}`\n"
            message += f"🏫 Perguruan Tinggi: `{dataumum.get('namapt', 'N/A')}`\n"
            message += f"📊 Jenjang: `{dataumum.get('namajenjang', 'N/A')}`\n"
            message += f"👥 Jenis Kelamin: `{'Laki-laki' if dataumum.get('jk') == 'L' else 'Perempuan'}`\n"
            message += f"📍 Tempat Lahir: `{dataumum.get('tmpt_lahir', 'N/A')}`\n"
            message += f"📅 Tanggal Lahir: `{dataumum.get('tgl_lahir', 'N/A')}`\n"
            message += f"📧 Email: `{dataumum.get('email', 'N/A')}`\n"
            message += f"📱 No. HP: `{dataumum.get('no_hp', 'N/A')}`\n"
            message += f"🏠 Alamat: `{dataumum.get('jln', 'N/A')}`\n"
            message += f"🏘️ RT/RW: `{dataumum.get('rt', 'N/A')}/{dataumum.get('rw', 'N/A')}`\n"
            message += f"📮 Kode Pos: `{dataumum.get('kode_pos', 'N/A')}`\n"
            message += f"🌍 Kewarganegaraan: `{dataumum.get('kewarganegaraan', 'N/A')}`\n"
            message += f"🆔 NIK: `{dataumum.get('nik', 'N/A')}`\n\n"
            
            # Data Orang Tua
            message += "👨‍👩‍👧‍👦 *Data Orang Tua:*\n"
            message += f"👨 Nama Ayah: `{dataumum.get('nm_ayah', 'N/A')}`\n"
            message += f"👩 Nama Ibu: `{dataumum.get('nm_ibu_kandung', 'N/A')}`\n"
            if dataumum.get('nm_wali'):
                message += f"👤 Nama Wali: `{dataumum.get('nm_wali', 'N/A')}`\n"
            message += "\n"
        
        message_parts.append(message)
        
        # Part 2: Data Kuliah
        message = "👨‍🎓 *Detail Lengkap Mahasiswa (2/3)*\n\n"
        if 'datakuliah' in detail and detail['datakuliah']:
            message += "📚 *Riwayat Kuliah:*\n"
            # Hitung semester berurutan
            semester_count = 1
            for kuliah in detail['datakuliah']:
                smt = kuliah.get('id_smt', 'N/A')
                if smt != 'N/A':
                    year = smt[:4]
                    smt_text = f"Semester {semester_count} {year}"
                    semester_count += 1
                else:
                    smt_text = "N/A"
                    
                message += f"\n📅 *{smt_text}:*\n"
                message += f"📊 Status: `{kuliah.get('nm_stat_mhs', 'N/A')}`\n"
                
                # Format IPS dengan 2 desimal
                ips = kuliah.get('ips')
                if ips is not None and ips != 0:
                    try:
                        ips = f"{float(ips):.2f}"
                    except (ValueError, TypeError):
                        ips = "N/A"
                else:
                    ips = "N/A"
                
                # Format IPK dengan 2 desimal (menggunakan ipke)
                ipk = kuliah.get('ipke')
                if ipk is not None and ipk != 0:
                    try:
                        ipk = f"{float(ipk):.2f}"
                    except (ValueError, TypeError):
                        ipk = "N/A"
                else:
                    ipk = "N/A"
                
                message += f"📈 IPS: `{ips}`\n"
                message += f"📊 IPK: `{ipk}`\n"
                message += f"📚 SKS Semester: `{kuliah.get('sks_smt', 'N/A')}`\n"
                message += f"📚 SKS Total: `{kuliah.get('sks_total', 'N/A')}`\n"
            message += "\n"
        
        message_parts.append(message)
        
        # Part 3: Data KHS
        if 'datakhs' in detail and detail['datakhs']:
            # Kelompokkan data berdasarkan semester
            semester_data = {}
            for khs in detail['datakhs']:
                smt = khs.get('id_smt')
                if smt not in semester_data:
                    semester_data[smt] = []
                semester_data[smt].append(khs)
            
            # Tampilkan data per semester
            semester_count = 1
            for smt in sorted(semester_data.keys()):
                message = f"👨‍🎓 *Detail Lengkap Mahasiswa (3/3)*\n\n"
                
                # Format semester
                if smt != 'N/A':
                    year = smt[:4]
                    smt_text = f"Semester {semester_count} {year}"
                    semester_count += 1
                else:
                    smt_text = "N/A"
                    
                message += f"📝 *Riwayat Nilai {smt_text}*\n"
                message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                # Tampilkan mata kuliah dalam format portrait
                for khs in semester_data[smt]:
                    message += f"📚 *{khs.get('nm_mk', 'N/A')}*\n"
                    message += f"🆔 Kode: `{khs.get('kode_mk', 'N/A')}`\n"
                    message += f"📊 SKS: `{khs.get('sks_mk', 'N/A')}`\n"
                    
                    # Format nilai huruf (hapus spasi di akhir)
                    nilai_huruf = khs.get('nilai_huruf', 'N/A')
                    if nilai_huruf and nilai_huruf != "null":
                        nilai_huruf = nilai_huruf.strip()
                    else:
                        nilai_huruf = "N/A"
                    
                    # Format nilai indeks dengan 2 desimal
                    nilai_indeks = khs.get('nilai_indeks')
                    if nilai_indeks and nilai_indeks != "null":
                        try:
                            nilai_indeks = f"{float(nilai_indeks):.2f}"
                        except (ValueError, TypeError):
                            nilai_indeks = "N/A"
                    else:
                        nilai_indeks = "N/A"
                    
                    message += f"📈 Nilai: `{nilai_huruf}`\n"
                    message += f"📊 Indeks: `{nilai_indeks}`\n"
                    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                message_parts.append(message)
        
        return message_parts
        
    except Exception as e:
        logger.error(f"Error formatting student detail: {str(e)}")
        return ["❌ Terjadi kesalahan saat memformat data mahasiswa."]

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check permission for button callbacks
    if not is_user_allowed(user_id):
        await query.message.edit_text(
            "⚠️ *Akses Terbatas*\n\n"
            "Maaf, Anda belum memiliki akses untuk menggunakan fitur ini.\n"
            "Silakan hubungi admin untuk mendapatkan akses.\n\n"
            "📞 Contact: @nant12_bot",
            parse_mode='Markdown'
        )
        return
    
    username = query.from_user.username or "Unknown"
    
    try:
        if query.data.startswith("mhs_"):
            # Get student index from callback data
            idx = int(query.data.split("_")[1]) - 1
            
            # Get student data from context
            if 'mahasiswa_list' not in context.user_data:
                await query.message.edit_text("❌ Data mahasiswa tidak ditemukan. Silakan cari ulang.")
                return
                
            mahasiswa = context.user_data['mahasiswa_list'][idx]
            
            # Check for forbidden student (except for admin)
            if user_id != 5705926766:
                if (mahasiswa.get('nm_pd', '').lower() == "azmi ridho rinanta" or 
                    mahasiswa.get('nipd', '') == "21523023" or 
                    mahasiswa.get('namapt', '').lower() == "universitas islam indonesia"):
                    await query.message.edit_text(
                        "⚠️ *PERINGATAN!*\n\n"
                        "Permintaan terlarang untuk lord kami, dilarang mencarinya atau anda terkena ban permanen !",
                        parse_mode='Markdown'
                    )
                    return
            
            # Show loading message
            loading_message = await show_loading(update, context, "Mengambil detail mahasiswa...")
            
            # Get student detail using the same session
            if 'session' not in context.user_data:
                await loading_message.edit_text("❌ Session tidak ditemukan. Silakan cari ulang.")
                return
                
            session = context.user_data['session']
            i_iduser = context.user_data['i_iduser']
            id_organisasi = context.user_data['id_organisasi']
            pm_token = context.user_data['pm_token']
            
            detail = await get_student_detail(
                mahasiswa['id_reg_pd'],
                i_iduser,
                id_organisasi,
                pm_token,
                session
            )
            
            if not detail:
                await loading_message.edit_text("❌ Gagal mengambil detail mahasiswa.")
                return

            # Check for forbidden student in detail (except for admin)
            if user_id != 5705926766:
                if (detail.get('dataumum', {}).get('nm_pd', '').lower() == "azmi ridho rinanta" or 
                    detail.get('dataumum', {}).get('nipd', '') == "21523023" or 
                    detail.get('dataumum', {}).get('namapt', '').lower() == "universitas islam indonesia"):
                    await loading_message.edit_text(
                        "⚠️ *PERINGATAN!*\n\n"
                        "Permintaan terlarang untuk lord kami, dilarang mencarinya atau anda terkena ban permanen !",
                        parse_mode='Markdown'
                    )
                    return

            # Save detail to context for later use
            context.user_data['current_detail'] = detail
                
            # Format brief detail
            brief_message = await format_brief_detail(detail)
            
            # Create keyboard with button for complete details
            keyboard = [
                [InlineKeyboardButton("📋 Lihat Detail Lengkap", callback_data="detail_lengkap")],
                [InlineKeyboardButton("🔍 Cari Lagi", callback_data="cari_lagi")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Show brief detail with buttons
            await loading_message.edit_text(
                brief_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        elif query.data == "detail_lengkap":
            # Get saved detail from context
            if 'current_detail' not in context.user_data:
                await query.message.edit_text("❌ Data detail tidak ditemukan. Silakan cari ulang.")
                return
                
            detail = context.user_data['current_detail']
            
            # Check for forbidden student in detail (except for admin)
            if user_id != 5705926766:
                if (detail.get('dataumum', {}).get('nm_pd', '').lower() == "azmi ridho rinanta" or 
                    detail.get('dataumum', {}).get('nipd', '') == "21523023" or 
                    detail.get('dataumum', {}).get('namapt', '').lower() == "universitas islam indonesia"):
                    await query.message.edit_text(
                        "⚠️ *PERINGATAN!*\n\n"
                        "Permintaan terlarang untuk lord kami, dilarang mencarinya atau anda terkena ban permanen !",
                        parse_mode='Markdown'
                    )
                    return
            
            # Format and send complete details
            messages = format_student_detail(detail)
            
            # Send all messages
            for i, message in enumerate(messages):
                if i == 0:
                    # Edit the first message
                    await query.message.edit_text(
                        message,
                        parse_mode='Markdown'
                    )
                    try:
                        await query.message.pin(disable_notification=True)
                    except Exception as e:
                        logger.error(f"Failed to pin message: {str(e)}")
                else:
                    # Send new messages for subsequent parts
                    await query.message.reply_text(
                        message,
                        parse_mode='Markdown'
                    )
            
        elif query.data == "cari_lagi":
            # Clear previous data
            context.user_data.clear()
            
            # Send message asking for input
            await query.message.edit_text(
                "🔍 *Cari Mahasiswa*\n\n"
                "Silakan masukkan nama lengkap atau NIM mahasiswa yang ingin dicari.\n\n"
                "📌 Contoh:\n"
                "• Ahmad Fauzi\n"
                "• 2020123456\n"
                "• Siti Nurhaliza\n"
                "• 2020987654",
                parse_mode='Markdown'
            )
            
            # Set flag to indicate we're waiting for search input
            context.user_data['waiting_for_search'] = True
            
    except Exception as e:
        logger.error(f"Error in button_callback: {str(e)}")
        await query.message.edit_text(f"❌ Terjadi kesalahan: {str(e)}")

async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /regist command"""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        # Check if command is /regist ordalnant
        if not context.args or " ".join(context.args).lower() != "ordalnant":
            await update.message.reply_text("❌ token registrasi salah")
            return
            
        # Load current allowed users
        allowed_users = load_allowed_users()
        
        # Check if user is already registered
        if any(user['id'] == user_id for user in allowed_users.get('users', [])):
            await update.message.reply_text(
                "✅ Anda sudah terdaftar sebelumnya.\n"
                "Silakan gunakan bot dengan normal."
            )
            return
            
        # Add new user
        if not isinstance(allowed_users, dict):
            allowed_users = {"users": []}
        if "users" not in allowed_users:
            allowed_users["users"] = []
            
        allowed_users["users"].append({
            "id": user_id,
            "username": username,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Save updated allowed users
        with open(ALLOWED_USERS_FILE, 'w') as f:
            json.dump(allowed_users, f, indent=4)
            
        # Send success message
        await update.message.reply_text(
            "✅ Registrasi berhasil!\n\n"
            "Sekarang Anda dapat menggunakan bot untuk mencari data mahasiswa.\n"
            "Gunakan command /cari diikuti nama atau NIM mahasiswa.\n\n"
            "Contoh:\n"
            "• /cari Ahmad Fauzi\n"
            "• /cari 2020123456"
        )
        
        # Send notification to admin
        await send_notification_to_admin(
            user_id,
            username,
            f"New user registration: {username} (ID: {user_id})"
        )
        
    except Exception as e:
        logger.error(f"Error in register_user: {str(e)}")
        await update.message.reply_text(f"❌ Terjadi kesalahan: {str(e)}")

def main():
    """Start the bot"""
    try:
        print("\n=== Starting Student Search Bot ===")
        print(f"TELEGRAM_BOT_TOKEN: {TOKEN[:10]}...")
        print(f"ADMIN_BOT_TOKEN: {ADMIN_BOT_TOKEN[:10]}...")
        print(f"ADMIN_CHAT_ID: {ADMIN_CHAT_ID}")
        
        # Validate environment variables
        if not TOKEN:
            print("Error: TELEGRAM_BOT_TOKEN is empty")
            return
        if not ADMIN_BOT_TOKEN:
            print("Error: ADMIN_BOT_TOKEN is empty")
            return
        if not ADMIN_CHAT_ID:
            print("Error: ADMIN_CHAT_ID is empty")
            return
        
        # Create the Application
        application = Application.builder().token(TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("cari", search))
        application.add_handler(CommandHandler("regist", register_user))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Add handlers for all types of messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.PHOTO, handle_message))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_message))
        application.add_handler(MessageHandler(filters.VOICE, handle_message))
        application.add_handler(MessageHandler(filters.VIDEO, handle_message))
        application.add_handler(MessageHandler(filters.Sticker.ALL, handle_message))
        application.add_handler(MessageHandler(filters.Location.ALL, handle_message))
        application.add_handler(MessageHandler(filters.Contact.ALL, handle_message))
        application.add_handler(MessageHandler(filters.ANIMATION, handle_message))
        application.add_handler(MessageHandler(filters.AUDIO, handle_message))

        print("Handlers registered successfully")
        print("Starting polling...")

        # Start the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        print(f"Error starting bot: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main()