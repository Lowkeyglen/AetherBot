#!/usr/bin/env python3
"""
AetherBot - Advanced Telegram Assistant
Created with assistance from Glen GitHub (Lowkeyglen)
"""

import logging
import random
import requests
import json
import sqlite3
import datetime
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Configuration - Secure token handling
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("""
❌ BOT_TOKEN not found in environment variables!

Please create a .env file with:
BOT_TOKEN=your_actual_bot_token_here

Or set environment variable:
export BOT_TOKEN=your_actual_bot_token_here

Get your token from @BotFather on Telegram
""")

# Database setup
def init_db():
    conn = sqlite3.connect('aetherbot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_mood TEXT,
            mood_count INTEGER DEFAULT 0,
            feature_usage TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            note_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            category TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Response data
GREETINGS = {
    'morning': ['Good morning! 🌅', 'Morning! Ready for a new day? ☀️', 'Rise and shine! 🌄'],
    'afternoon': ['Good afternoon! 🌞', 'Afternoon! Hope your day is going well! 😊', 'Hello there! 👋'],
    'evening': ['Good evening! 🌙', 'Evening! How was your day? 🌆', 'Hello! Hope you had a great day! ✨'],
    'night': ['Good night! 🌃', 'Late night? Hope you get some rest! 😴', 'Hello night owl! 🦉']
}

MOOD_RESPONSES = {
    'great': [
        "That's awesome! 🎉 Let's make today even better!",
        "Fantastic! 😄 Ready to be productive?",
        "Wonderful! 🌟 What would you like to accomplish today?"
    ],
    'good': [
        "Glad to hear you're doing well! 😊",
        "Nice! Let's keep the positive vibes going! ✨",
        "Good to know! Ready for some productivity? 📈"
    ],
    'okay': [
        "Hope your day gets even better! 🌈",
        "Let me help brighten your day! ☀️",
        "We all have those days. How can I help? 🤗"
    ],
    'bad': [
        "I'm here for you! 💙 Would you like to talk about it?",
        "Sorry to hear that. Remember, this too shall pass. 🌦️",
        "Let me try to cheer you up! How about a joke? 😊"
    ]
}

class AetherBot:
    def __init__(self):
        self.user_sessions = {}
    
    def get_time_based_greeting(self):
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            return random.choice(GREETINGS['morning'])
        elif 12 <= hour < 17:
            return random.choice(GREETINGS['afternoon'])
        elif 17 <= hour < 22:
            return random.choice(GREETINGS['evening'])
        else:
            return random.choice(GREETINGS['night'])
    
    def get_user_data(self, user_id):
        conn = sqlite3.connect('aetherbot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'user_id': user[0],
                'username': user[1],
                'first_name': user[2],
                'last_mood': user[3],
                'mood_count': user[4],
                'feature_usage': json.loads(user[5]) if user[5] else {}
            }
        return None
    
    def update_user_data(self, user_id, username, first_name, mood=None, feature=None):
        conn = sqlite3.connect('aetherbot.db')
        cursor = conn.cursor()
        
        user_data = self.get_user_data(user_id)
        feature_usage = user_data['feature_usage'] if user_data else {}
        
        if feature:
            feature_usage[feature] = feature_usage.get(feature, 0) + 1
        
        if user_data:
            cursor.execute('''
                UPDATE users SET username=?, first_name=?, last_mood=?, mood_count=mood_count+?, feature_usage=?
                WHERE user_id=?
            ''', (username, first_name, mood, 1 if mood else 0, json.dumps(feature_usage), user_id))
        else:
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_mood, mood_count, feature_usage)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, mood, 1 if mood else 0, json.dumps(feature_usage)))
        
        conn.commit()
        conn.close()

# Initialize bot instance
aether_bot = AetherBot()

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    greeting = aether_bot.get_time_based_greeting()
    
    welcome_message = f"""
{greeting}

I'm **AetherBot** 🤖 - Your intelligent assistant! 

I'm here to help you with:
• 📊 Productivity tasks
• 🔧 Utility functions  
• 😊 Daily assistance
• 🎉 Fun activities

*Created with assistance from Glen GitHub (Lowkeyglen)*

How can I help you today? Use /help to see all features!
    """
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    # Ask how they're feeling
    keyboard = [
        [
            InlineKeyboardButton("🎉 Great!", callback_data="mood_great"),
            InlineKeyboardButton("😊 Good", callback_data="mood_good"),
        ],
        [
            InlineKeyboardButton("😐 Okay", callback_data="mood_okay"),
            InlineKeyboardButton("😔 Not great", callback_data="mood_bad"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "How are you feeling today? 😊",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 **AetherBot Help Menu**

**📊 Productivity Commands:**
/notes - Manage your quick notes
/expenses - Track your expenses  
/reminder - Set a reminder
/todo - To-do list management

**🔧 Utility Commands:**
/shorten - Shorten long URLs
/password - Generate secure passwords
/calc - Quick calculations
/convert - Currency & unit conversion

**😊 Fun Commands:**
/quote - Get daily inspiration
/fact - Learn something new
/joke - Have a laugh
/weather - Check weather

**ℹ️ Info Commands:**
/features - Detailed feature list
/tutorial - Usage guide
/about - About this bot

*Just type normally like "hello" or ask questions!*
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def features(update: Update, context: ContextTypes.DEFAULT_TYPE):
    features_text = """
🌟 **AetherBot Features Overview**

**Smart Assistant:**
• Natural language understanding
• Mood tracking & empathy
• Personalized responses
• Context-aware greetings

**Productivity Suite:**
• Quick note-taking with /notes
• Expense tracking with /expenses
• Reminder system with /reminder
• To-do lists with /todo

**Utility Tools:**
• URL shortening with /shorten
• Password generation with /password
• Calculator with /calc
• Currency converter with /convert

**Entertainment:**
• Daily inspirational quotes
• Interesting facts
• Humorous jokes
• Weather information

**Special Features:**
• Multi-language support
• Daily proactive tips
• Usage analytics
• Session management

*Powered by advanced AI assistance from Glen GitHub (Lowkeyglen)*
"""
    await update.message.reply_text(features_text, parse_mode='Markdown')

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = """
🤖 **About AetherBot**

*Version 2.0 - Advanced Telegram Assistant*

**Creator:** Developed with AI assistance
**Special Thanks:** Glen GitHub (Lowkeyglen) for development guidance

**Features:**
• 15+ useful tools in one bot
• Intelligent conversation system
• Mood tracking & empathy
• Multi-language support
• Secure & private

**Technology:**
• Built with python-telegram-bot
• SQLite database for data persistence
• REST API integrations
• Advanced NLP capabilities

*This bot aims to be your all-in-one digital companion for productivity and entertainment!*
"""
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def shorten_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        url = context.args[0]
        try:
            response = requests.get(f"http://tinyurl.com/api-create.php?url={url}")
            short_url = response.text
            await update.message.reply_text(f"🔗 Shortened URL:\n`{short_url}`", parse_mode='Markdown')
            aether_bot.update_user_data(update.effective_user.id, update.effective_user.username, update.effective_user.first_name, feature='shorten')
        except Exception as e:
            await update.message.reply_text("❌ Sorry, couldn't shorten that URL.")
    else:
        await update.message.reply_text("Usage: /shorten <URL>")

async def generate_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import secrets
    import string
    
    length = 12
    if context.args:
        try:
            length = int(context.args[0])
            length = max(8, min(32, length))  # Limit between 8-32
        except:
            pass
    
    characters = string.ascii_letters + string.digits + "!@#$%"
    password = ''.join(secrets.choice(characters) for _ in range(length))
    
    await update.message.reply_text(
        f"🔐 **Secure Password Generated**\n\n"
        f"`{password}`\n\n"
        f"*Length: {length} characters*\n"
        f"*Save this in a secure place!*",
        parse_mode='Markdown'
    )
    aether_bot.update_user_data(update.effective_user.id, update.effective_user.username, update.effective_user.first_name, feature='password')

async def quick_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            expression = ' '.join(context.args)
            # Safety check - only allow basic math operations
            allowed_chars = set('0123456789+-*/.() ')
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                await update.message.reply_text(f"🧮 Calculation Result:\n`{expression} = {result}`", parse_mode='Markdown')
                aether_bot.update_user_data(update.effective_user.id, update.effective_user.username, update.effective_user.first_name, feature='calc')
            else:
                await update.message.reply_text("❌ Only basic math operations are allowed.")
        except:
            await update.message.reply_text("❌ Invalid mathematical expression.")
    else:
        await update.message.reply_text("Usage: /calc <expression>\nExample: /calc 15 * (20 + 5)")

async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage user notes"""
    user_id = update.effective_user.id
    
    if context.args:
        # Add new note
        note_text = ' '.join(context.args)
        conn = sqlite3.connect('aetherbot.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO user_notes (user_id, note_text) VALUES (?, ?)', (user_id, note_text))
        conn.commit()
        conn.close()
        await update.message.reply_text("📝 Note saved successfully!")
        aether_bot.update_user_data(user_id, update.effective_user.username, update.effective_user.first_name, feature='notes')
    else:
        # Show existing notes
        conn = sqlite3.connect('aetherbot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT note_text, created_at FROM user_notes WHERE user_id = ? ORDER BY created_at DESC LIMIT 5', (user_id,))
        notes = cursor.fetchall()
        conn.close()
        
        if notes:
            notes_text = "📋 **Your Recent Notes:**\n\n"
            for i, (note, created_at) in enumerate(notes, 1):
                notes_text += f"{i}. {note}\n   🕒 {created_at[:16]}\n\n"
            await update.message.reply_text(notes_text, parse_mode='Markdown')
        else:
            await update.message.reply_text("📝 No notes yet! Use `/notes <your note>` to add one.", parse_mode='Markdown')

async def expenses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track expenses"""
    user_id = update.effective_user.id
    
    if len(context.args) >= 2:
        try:
            amount = float(context.args[0])
            category = context.args[1]
            description = ' '.join(context.args[2:]) if len(context.args) > 2 else "No description"
            
            conn = sqlite3.connect('aetherbot.db')
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO expenses (user_id, amount, category, description) VALUES (?, ?, ?, ?)',
                (user_id, amount, category, description)
            )
            conn.commit()
            conn.close()
            
            await update.message.reply_text(f"💰 Expense recorded: ${amount:.2f} for {category}")
            aether_bot.update_user_data(user_id, update.effective_user.username, update.effective_user.first_name, feature='expenses')
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid amount. Usage: `/expenses <amount> <category> [description]`", parse_mode='Markdown')
    else:
        await update.message.reply_text("Usage: `/expenses <amount> <category> [description]`\nExample: `/expenses 15.50 food Lunch at cafe`", parse_mode='Markdown')

async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get inspirational quote"""
    quotes = [
        "The only way to do great work is to love what you do. - Steve Jobs",
        "Innovation distinguishes between a leader and a follower. - Steve Jobs",
        "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
        "Strive not to be a success, but rather to be of value. - Albert Einstein",
        "The way to get started is to quit talking and begin doing. - Walt Disney",
    ]
    
    quote = random.choice(quotes)
    await update.message.reply_text(f"💫 **Inspirational Quote:**\n\n{quote}")
    aether_bot.update_user_data(update.effective_user.id, update.effective_user.username, update.effective_user.first_name, feature='quote')

async def fact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get interesting fact"""
    facts = [
        "Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly good to eat.",
        "Octopuses have three hearts. Two pump blood through the gills, while the third pumps it through the rest of the body.",
        "A day on Venus is longer than a year on Venus. It takes Venus 243 Earth days to rotate once, but only 225 Earth days to orbit the Sun.",
        "The shortest war in history was between Britain and Zanzibar in 1896. It lasted only 38 minutes.",
        "Bananas are berries, but strawberries aren't.",
    ]
    
    fact = random.choice(facts)
    await update.message.reply_text(f"🧠 **Did You Know?**\n\n{fact}")
    aether_bot.update_user_data(update.effective_user.id, update.effective_user.username, update.effective_user.first_name, feature='fact')

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tell a joke"""
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "Why did the scarecrow win an award? He was outstanding in his field!",
        "Why don't eggs tell jokes? They'd crack each other up!",
        "What do you call a fake noodle? An impasta!",
        "Why did the math book look so sad? Because it had too many problems!",
    ]
    
    joke = random.choice(jokes)
    await update.message.reply_text(f"😂 **Joke of the Moment:**\n\n{joke}")
    aether_bot.update_user_data(update.effective_user.id, update.effective_user.username, update.effective_user.first_name, feature='joke')

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get weather information (simulated)"""
    if context.args:
        city = ' '.join(context.args)
        # Simulate weather data
        temperatures = [72, 68, 75, 80, 65, 70]
        conditions = ["sunny", "cloudy", "partly cloudy", "rainy", "clear"]
        
        temp = random.choice(temperatures)
        condition = random.choice(conditions)
        
        await update.message.reply_text(
            f"🌤️ **Weather for {city.title()}:**\n"
            f"• Temperature: {temp}°F\n"
            f"• Conditions: {condition}\n"
            f"• Humidity: {random.randint(40, 80)}%\n\n"
            f"*Note: This is simulated data*"
        )
    else:
        await update.message.reply_text("Usage: `/weather <city>`\nExample: `/weather New York`")
    
    aether_bot.update_user_data(update.effective_user.id, update.effective_user.username, update.effective_user.first_name, feature='weather')

async def tutorial_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tutorial"""
    tutorial_text = """
📚 **AetherBot Tutorial**

**Getting Started:**
1. Just say "hello" or use /start
2. Share your mood using the buttons
3. Explore features through the menu

**Key Features:**
• Notes: `/notes Your note here` - Quick saving
• Expenses: `/expenses 15.50 food` - Track spending
• Passwords: `/password` - Secure generation
• Calculations: `/calc 15 * (20 + 5)` - Quick math

**Pro Tips:**
• Use natural language like "how are you?"
• Buttons provide quick access to features
• All your data is stored securely locally

**Need Help?**
Use /help for command list or /features for details!
"""
    await update.message.reply_text(tutorial_text, parse_mode='Markdown')

# Placeholder commands for future implementation
async def reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏰ Reminder feature coming soon! Use /notes for now to jot down reminders.")

async def todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 To-do list feature coming soon! Use /notes for now to track tasks.")

async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Currency conversion feature coming soon! Use /calc for basic calculations.")

# Message Handlers
async def handle_greeting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text.lower()
    
    greeting = aether_bot.get_time_based_greeting()
    personalized_greeting = f"{greeting} {user.first_name}! 👋"
    
    await update.message.reply_text(personalized_greeting)
    
    # Update user data
    aether_bot.update_user_data(user.id, user.username, user.first_name)
    
    # Ask about their mood
    keyboard = [
        [
            InlineKeyboardButton("🎉 Great!", callback_data="mood_great"),
            InlineKeyboardButton("😊 Good", callback_data="mood_good"),
        ],
        [
            InlineKeyboardButton("😐 Okay", callback_data="mood_okay"),
            InlineKeyboardButton("😔 Not great", callback_data="mood_bad"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "How are you feeling today? 😊",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text.lower()
    
    # Simple NLP for common questions
    if any(word in message_text for word in ['what can you do', 'capabilities', 'features']):
        await help_command(update, context)
    elif any(word in message_text for word in ['thank', 'thanks']):
        await update.message.reply_text("You're welcome! 😊 Is there anything else I can help with?")
    elif any(word in message_text for word in ['how are you', 'how do you feel']):
        await update.message.reply_text("I'm functioning perfectly! 🤖 Ready to help you with anything! 💪")
    else:
        await update.message.reply_text(
            "I understand you're saying: '" + update.message.text + "'\n\n"
            "Try /help to see all the things I can do for you! 🚀"
        )

# Callback Query Handlers
async def handle_mood_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    mood = query.data.replace('mood_', '')
    user = query.from_user
    
    # Update user mood in database
    aether_bot.update_user_data(user.id, user.username, user.first_name, mood=mood)
    
    # Send empathetic response
    mood_response = random.choice(MOOD_RESPONSES[mood])
    
    # Create feature suggestion keyboard
    keyboard = [
        [InlineKeyboardButton("📝 Quick Notes", callback_data="feature_notes")],
        [InlineKeyboardButton("💰 Expense Track", callback_data="feature_expenses")],
        [InlineKeyboardButton("🔐 Password Gen", callback_data="feature_password")],
        [InlineKeyboardButton("🌤️ Weather", callback_data="feature_weather")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"{mood_response}\n\n"
        "What would you like to do? Choose a feature below or type /help for full options:",
        reply_markup=reply_markup
    )

async def handle_feature_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    feature = query.data.replace('feature_', '')
    user = query.from_user
    
    # Update feature usage
    aether_bot.update_user_data(user.id, user.username, user.first_name, feature=feature)
    
    feature_responses = {
        'notes': "📝 **Quick Notes Feature**\nUse /notes to manage your personal notes!",
        'expenses': "💰 **Expense Tracking**\nUse /expenses to track your spending!",
        'password': "🔐 **Password Generator**\nUse /password to create secure passwords!",
        'weather': "🌤️ **Weather Info**\nUse /weather <city> to get weather information!"
    }
    
    await query.edit_message_text(
        feature_responses.get(feature, "Feature selected! Use the command to get started! 🚀")
    )

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("features", features))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("shorten", shorten_url))
    application.add_handler(CommandHandler("password", generate_password))
    application.add_handler(CommandHandler("calc", quick_calc))
    application.add_handler(CommandHandler("notes", notes_command))
    application.add_handler(CommandHandler("expenses", expenses_command))
    application.add_handler(CommandHandler("quote", quote_command))
    application.add_handler(CommandHandler("fact", fact_command))
    application.add_handler(CommandHandler("joke", joke_command))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("tutorial", tutorial_command))
    application.add_handler(CommandHandler("reminder", reminder_command))
    application.add_handler(CommandHandler("todo", todo_command))
    application.add_handler(CommandHandler("convert", convert_command))

    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^(hi|hello|hey|good morning|good afternoon|good evening|yo|whats up|howdy)'), handle_greeting))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Callback query handlers
    application.add_handler(CallbackQueryHandler(handle_mood_selection, pattern="^mood_"))
    application.add_handler(CallbackQueryHandler(handle_feature_selection, pattern="^feature_"))

    # Start the Bot
    print("🤖 AetherBot is starting...")
    print("✅ Environment variables loaded successfully")
    print("📝 Created with assistance from Glen GitHub (Lowkeyglen)")
    print("🔐 Token security: Enabled")
    application.run_polling()

if __name__ == '__main__':
    main()
