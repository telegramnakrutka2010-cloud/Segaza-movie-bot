import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x]

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('movies.db', check_same_thread=False)
        self.create_tables()
        self.add_sample_movies()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                language TEXT DEFAULT 'en',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Movies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                year INTEGER,
                genre TEXT,
                rating TEXT,
                duration TEXT,
                director TEXT,
                cast TEXT,
                poster_url TEXT,
                movie_url TEXT NOT NULL,
                category TEXT,
                is_active BOOLEAN DEFAULT 1,
                added_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Watch later table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watch_later (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                movie_id INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, movie_id)
            )
        ''')
        
        # Recently watched table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recently_watched (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                movie_id INTEGER,
                watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def add_sample_movies(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM movies")
        if cursor.fetchone()[0] == 0:
            sample_movies = [
                ("The Matrix", "A computer hacker learns from mysterious rebels about the true nature of his reality", 1999, "Sci-Fi", "8.7/10", "2h 16m", "Lana Wachowski, Lilly Wachowski", "Keanu Reeves, Laurence Fishburne", "https://via.placeholder.com/300x450/000000/FFFFFF?text=The+Matrix", "https://example.com/matrix", "sci_fi", 1),
                ("Inception", "A thief who steals corporate secrets through dream-sharing technology", 2010, "Sci-Fi", "8.8/10", "2h 28m", "Christopher Nolan", "Leonardo DiCaprio, Joseph Gordon-Levitt", "https://via.placeholder.com/300x450/0000FF/FFFFFF?text=Inception", "https://example.com/inception", "sci_fi", 1),
                ("The Dark Knight", "Batman faces the Joker, a criminal mastermind seeking to create chaos", 2008, "Action", "9.0/10", "2h 32m", "Christopher Nolan", "Christian Bale, Heath Ledger", "https://via.placeholder.com/300x450/FFFF00/000000?text=Dark+Knight", "https://example.com/darkknight", "action", 1)
            ]
            cursor.executemany('''
                INSERT INTO movies (title, description, year, genre, rating, duration, director, cast, poster_url, movie_url, category, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', sample_movies)
            self.conn.commit()

db = Database()

# Keyboard Functions
def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["🔍 Search Movies", "📁 Categories"],
        ["⏱️ Watch Later", "📺 Recently Watched"],
        ["⚙️ Settings", "👑 Admin Panel"]
    ], resize_keyboard=True)

def admin_panel_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("🎬 Add Movie", callback_data="admin_add_movie")],
        [InlineKeyboardButton("📝 Manage Movies", callback_data="admin_manage_movies")],
        [InlineKeyboardButton("👥 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="admin_back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def categories_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎬 Action", callback_data="category_action")],
        [InlineKeyboardButton("🚀 Sci-Fi", callback_data="category_sci_fi")],
        [InlineKeyboardButton("😂 Comedy", callback_data="category_comedy")],
        [InlineKeyboardButton("💖 Romance", callback_data="category_romance")],
        [InlineKeyboardButton("👻 Horror", callback_data="category_horror")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# User Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor = db.conn.cursor()
    
    # Add user to database
    cursor.execute('''
        INSERT OR IGNORE INTO users (telegram_id, username, first_name) 
        VALUES (?, ?, ?)
    ''', (user.id, user.username, user.first_name))
    db.conn.commit()
    
    await update.message.reply_text(
        "🎬 *Welcome to MovieBot!*\n\n"
        "Your ultimate movie companion with:\n"
        "• 🎥 Thousands of movies\n"
        "• ⏱️ Watch later list\n"
        "• 📺 Watch history\n"
        "• 🔍 Advanced search\n\n"
        "Choose an option below:",
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📁 *Select Category:*",
        parse_mode='Markdown',
        reply_markup=categories_keyboard()
    )

async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    category = query.data.replace('category_', '')
    cursor = db.conn.cursor()
    
    cursor.execute('''
        SELECT * FROM movies 
        WHERE category = ? AND is_active = 1 
        LIMIT 10
    ''', (category,))
    movies = cursor.fetchall()
    
    if movies:
        for movie in movies:
            movie_id, title, description, year, genre, rating, duration, director, cast, poster_url, movie_url, category, is_active, added_by, created_at = movie
            
            text = f"""
🎬 *{title}* ({year})

⭐ *Rating:* {rating}
⏱️ *Duration:* {duration}
🎭 *Genre:* {genre}
👨‍💼 *Director:* {director}

📖 *Plot:*
{description}

[Watch Now]({movie_url})
            """.strip()
            
            keyboard = [
                [
                    InlineKeyboardButton("🎥 Watch Movie", url=movie_url),
                    InlineKeyboardButton("⏱️ Save", callback_data=f"save_{movie_id}")
                ]
            ]
            
            if poster_url and poster_url.startswith('http'):
                try:
                    await query.message.reply_photo(
                        photo=poster_url,
                        caption=text,
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except:
                    await query.message.reply_text(
                        text,
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            else:
                await query.message.reply_text(
                    text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
    else:
        await query.message.reply_text("No movies found in this category.")

async def save_to_watch_later(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    movie_id = int(query.data.replace('save_', ''))
    
    cursor = db.conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO watch_later (user_id, movie_id) 
            VALUES (?, ?)
        ''', (user_id, movie_id))
        db.conn.commit()
        await query.answer("✅ Added to Watch Later!")
    except:
        await query.answer("❌ Already in Watch Later!")

async def show_watch_later(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor = db.conn.cursor()
    
    cursor.execute('''
        SELECT m.* FROM movies m
        JOIN watch_later wl ON m.id = wl.movie_id
        WHERE wl.user_id = ?
        ORDER BY wl.added_at DESC
    ''', (user_id,))
    movies = cursor.fetchall()
    
    if movies:
        text = "⏱️ *Your Watch Later List:*\n\n"
        for movie in movies:
            movie_id, title, description, year, genre, rating, duration, director, cast, poster_url, movie_url, category, is_active, added_by, created_at = movie
            text += f"• *{title}* ({year}) - /watch_{movie_id}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text("Your watch later list is empty!")

# Admin Handlers
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Access denied!")
        return
    
    cursor = db.conn.cursor()
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM movies")
    total_movies = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM movies WHERE is_active = 1")
    active_movies = cursor.fetchone()[0]
    
    text = f"""
👑 *Admin Panel*

📊 *Statistics:*
• 👥 Total Users: {total_users}
• 🎬 Total Movies: {total_movies}
• ✅ Active Movies: {active_movies}
• 🔒 Inactive Movies: {total_movies - active_movies}

*Admin Functions:*
• 📊 View statistics
• 🎬 Add new movies
• 📝 Manage existing movies
• 👥 Broadcast messages
    """.strip()
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=admin_panel_keyboard()
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    cursor = db.conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM movies")
    total_movies = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM watch_later")
    total_watch_later = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM recently_watched")
    total_recent = cursor.fetchone()[0]
    
    text = f"""
📊 *Detailed Statistics*

👥 *Users:*
• Total Users: {total_users}

🎬 *Movies:*
• Total Movies: {total_movies}
• Active Movies: {cursor.execute("SELECT COUNT(*) FROM movies WHERE is_active = 1").fetchone()[0]}

💾 *User Activity:*
• Watch Later Entries: {total_watch_later}
• Recently Watched: {total_recent}
    """.strip()
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=admin_panel_keyboard())

async def admin_add_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    context.user_data['adding_movie'] = True
    context.user_data['movie_step'] = 'title'
    
    await query.edit_message_text(
        "🎬 *Add New Movie*\n\n"
        "Please send movie details in the following format:\n\n"
        "*Title*\n"
        "*Description*\n" 
        "*Year*\n"
        "*Genre*\n"
        "*Rating* (e.g., 8.5/10)\n"
        "*Duration* (e.g., 2h 15m)\n"
        "*Director*\n"
        "*Cast* (comma separated)\n"
        "*Poster URL*\n"
        "*Movie URL*\n"
        "*Category* (action, sci_fi, comedy, romance, horror)\n\n"
        "*Example:*\n"
        "The Matrix\n"
        "A computer hacker learns about reality\n"
        "1999\n"
        "Sci-Fi\n"
        "8.7/10\n"
        "2h 16m\n"
        "Lana Wachowski\n"
        "Keanu Reeves, Laurence Fishburne\n"
        "https://example.com/poster.jpg\n"
        "https://example.com/movie\n"
        "sci_fi",
        parse_mode='Markdown'
    )

async def handle_add_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS or not context.user_data.get('adding_movie'):
        return
    
    try:
        lines = update.message.text.split('\n')
        if len(lines) >= 11:
            title, description, year, genre, rating, duration, director, cast, poster_url, movie_url, category = lines[:11]
            
            cursor = db.conn.cursor()
            cursor.execute('''
                INSERT INTO movies (title, description, year, genre, rating, duration, director, cast, poster_url, movie_url, category, added_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, description, int(year), genre, rating, duration, director, cast, poster_url, movie_url, category, user_id))
            db.conn.commit()
            
            await update.message.reply_text(
                f"✅ *Movie Added Successfully!*\n\n"
                f"*Title:* {title}\n"
                f"*Year:* {year}\n"
                f"*Category:* {category}\n\n"
                "Users can now find this movie in the categories.",
                parse_mode='Markdown'
            )
            
            context.user_data['adding_movie'] = False
        else:
            await update.message.reply_text("❌ Invalid format! Please send all 11 lines of information.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error adding movie: {str(e)}")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    context.user_data['broadcasting'] = True
    await query.edit_message_text(
        "📢 *Broadcast Message*\n\n"
        "Send the message you want to broadcast to all users:",
        parse_mode='Markdown'
    )

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS or not context.user_data.get('broadcasting'):
        return
    
    message = update.message.text
    cursor = db.conn.cursor()
    cursor.execute("SELECT telegram_id FROM users")
    users = cursor.fetchall()
    
    sent = 0
    failed = 0
    
    broadcast_msg = await update.message.reply_text(f"📤 Broadcasting to {len(users)} users...")
    
    for (telegram_id,) in users:
        try:
            await context.bot.send_message(
                chat_id=telegram_id,
                text=f"📢 *Announcement*\n\n{message}",
                parse_mode='Markdown'
            )
            sent += 1
        except:
            failed += 1
    
    context.user_data['broadcasting'] = False
    await broadcast_msg.edit_text(
        f"✅ *Broadcast Complete!*\n\n"
        f"✅ Successful: {sent}\n"
        f"❌ Failed: {failed}",
        parse_mode='Markdown'
    )

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏠 *Main Menu*",
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

def main():
    if not BOT_TOKEN:
        print("❌ Error: BOT_TOKEN not found in environment variables!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # User handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Text(["📁 Categories"]), show_categories))
    application.add_handler(MessageHandler(filters.Text(["⏱️ Watch Later"]), show_watch_later))
    application.add_handler(MessageHandler(filters.Text(["👑 Admin Panel"]), admin_panel))
    application.add_handler(MessageHandler(filters.Text(["🔍 Search Movies", "📺 Recently Watched", "⚙️ Settings"]), start))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(category_handler, pattern="^category_"))
    application.add_handler(CallbackQueryHandler(save_to_watch_later, pattern="^save_"))
    application.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats"))
    application.add_handler(CallbackQueryHandler(admin_add_movie, pattern="^admin_add_movie"))
    application.add_handler(CallbackQueryHandler(admin_broadcast, pattern="^admin_broadcast"))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern="^admin_back_main"))
    
    # Admin message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_movie))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast))
    
    print("🤖 Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
