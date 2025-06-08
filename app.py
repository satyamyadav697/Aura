# Aura
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler
)
import redis
from config import TOKEN, REDIS_URL

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Redis
r = redis.from_url(REDIS_URL)

class ChatLevelsBot:
    def __init__(self):
        self.updater = Updater(TOKEN, use_context=True)
        self.dp = self.updater.dispatcher
        
        # Register handlers
        self.dp.add_handler(CommandHandler("start", self.start))
        self.dp.add_handler(CommandHandler("rank", self.show_rank))
        self.dp.add_handler(CommandHandler("leaderboard", self.show_leaderboard))
        self.dp.add_handler(CommandHandler("help", self.help_command))
        self.dp.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_message))
        self.dp.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Error handler
        self.dp.add_error_handler(self.error_handler)

    def start(self, update: Update, context: CallbackContext) -> None:
        """Send a message when the command /start is issued."""
        user = update.effective_user
        update.message.reply_markdown_v2(
            fr'Hi {user.mention_markdown_v2()}\! Welcome to Chat Levels Bot\! '
            'I track your activity and award you with levels and XP\. '
            'Use /rank to check your level or /leaderboard to see top users\.'
        )
        
        # Initialize user data if not exists
        user_id = str(user.id)
        if not r.hexists(f"user:{user_id}", "xp"):
            r.hset(f"user:{user_id}", "xp", 0)
            r.hset(f"user:{user_id}", "level", 1)
            r.hset(f"user:{user_id}", "messages", 0)

    def handle_message(self, update: Update, context: CallbackContext) -> None:
        """Handle all non-command messages and award XP."""
        user = update.effective_user
        chat = update.effective_chat
        message = update.effective_message
        
        # Skip if message is from a channel or edited
        if message.sender_chat or message.edit_date:
            return
            
        user_id = str(user.id)
        chat_id = str(chat.id)
        
        # Increment message count
        r.hincrby(f"user:{user_id}", "messages", 1)
        
        # Award XP (1-3 per message)
        xp_gain = 1 + (hash(f"{user_id}{message.message_id}") % 3)
        r.hincrby(f"user:{user_id}", "xp", xp_gain)
        
        # Check for level up
        current_xp = int(r.hget(f"user:{user_id}", "xp"))
        current_level = int(r.hget(f"user:{user_id}", "level"))
        xp_needed = self.calculate_xp_needed(current_level)
        
        if current_xp >= xp_needed:
            new_level = current_level + 1
            r.hset(f"user:{user_id}", "level", new_level)
            
            # Send level up message
            level_up_message = (
                f"🎉 Congratulations {user.mention_markdown_v2()}\! "
                f"You've leveled up to *Level {new_level}*\! 🎉"
            )
            message.reply_text(level_up_message, parse_mode='MarkdownV2')
            
            # Add bonus XP for leveling up
            r.hincrby(f"user:{user_id}", "xp", 10)

    def show_rank(self, update: Update, context: CallbackContext) -> None:
        """Show the user's current rank and XP."""
        user = update.effective_user
        user_id = str(user.id)
        
        # Get user data
        xp = int(r.hget(f"user:{user_id}", "xp") or 0)
        level = int(r.hget(f"user:{user_id}", "level") or 1)
        messages = int(r.hget(f"user:{user_id}", "messages") or 0)
        xp_needed = self.calculate_xp_needed(level)
        progress = min(100, int((xp / xp_needed) * 100)) if xp_needed > 0 else 0
        
        # Create progress bar
        progress_bar = self.create_progress_bar(progress)
        
        reply_text = (
            f"🏆 *Rank for {user.mention_markdown_v2()}*\n\n"
            f"📊 *Level:* {level}\n"
            f"✨ *XP:* {xp}/{xp_needed}\n"
            f"{progress_bar} {progress}%\n"
            f"💬 *Messages sent:* {messages}\n\n"
            f"Keep chatting to level up\!"
        )
        
        update.message.reply_text(reply_text, parse_mode='MarkdownV2')

    def show_leaderboard(self, update: Update, context: CallbackContext) -> None:
        """Show the top users in the chat."""
        chat = update.effective_chat
        chat_id = str(chat.id)
        
        # Get all users in this chat
        user_keys = r.keys("user:*")
        users = []
        
        for key in user_keys:
            user_id = key.decode().split(":")[1]
            level = int(r.hget(key, "level") or 0)
            xp = int(r.hget(key, "xp") or 0)
            if level > 0:  # Only include active users
                users.append((user_id, level, xp))
        
        # Sort by level (descending), then XP (descending)
        users.sort(key=lambda x: (-x[1], -x[2]))
        top_users = users[:10]  # Get top 10
        
        # Prepare leaderboard text
        leaderboard_text = "🏆 *Top Users Leaderboard* �\n\n"
        for i, (user_id, level, xp) in enumerate(top_users, 1):
            try:
                user = context.bot.get_chat_member(chat_id, int(user_id)).user
                username = user.mention_markdown_v2()
            except:
                username = f"User #{user_id}"
            
            leaderboard_text += f"{i}. {username} - Level {level} (✨{xp} XP)\n"
        
        if not top_users:
            leaderboard_text = "No users on the leaderboard yet. Start chatting!"
        
        # Add refresh button
        keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh_leaderboard")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            leaderboard_text,
            parse_mode='MarkdownV2',
            reply_markup=reply_markup
        )

    def button_callback(self, update: Update, context: CallbackContext) -> None:
        """Handle button callbacks."""
        query = update.callback_query
        query.answer()
        
        if query.data == "refresh_leaderboard":
            # Recreate the leaderboard
            chat = update.effective_chat
            chat_id = str(chat.id)
            
            user_keys = r.keys("user:*")
            users = []
            
            for key in user_keys:
                user_id = key.decode().split(":")[1]
                level = int(r.hget(key, "level") or 0)
                xp = int(r.hget(key, "xp") or 0)
                if level > 0:
                    users.append((user_id, level, xp))
            
            users.sort(key=lambda x: (-x[1], -x[2]))
            top_users = users[:10]
            
            leaderboard_text = "🏆 *Top Users Leaderboard* 🏆\n\n"
            for i, (user_id, level, xp) in enumerate(top_users, 1):
                try:
                    user = context.bot.get_chat_member(chat_id, int(user_id)).user
                    username = user.mention_markdown_v2()
                except:
                    username = f"User #{user_id}"
                
                leaderboard_text += f"{i}. {username} - Level {level} (✨{xp} XP)\n"
            
            if not top_users:
                leaderboard_text = "No users on the leaderboard yet. Start chatting!"
            
            keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh_leaderboard")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                text=leaderboard_text,
                parse_mode='MarkdownV2',
                reply_markup=reply_markup
            )

    def help_command(self, update: Update, context: CallbackContext) -> None:
        """Send a help message."""
        help_text = (
            "🤖 *Chat Levels Bot Help*\n\n"
            "This bot tracks your activity in chats and awards you with XP and levels.\n\n"
            "📌 *Commands:*\n"
            "/start - Start using the bot\n"
            "/rank - Check your current level and XP\n"
            "/leaderboard - Show top users in this chat\n"
            "/help - Show this help message\n\n"
            "💡 *How it works:*\n"
            "- You earn 1-3 XP for each message you send\n"
            "- Level up requires more XP as you progress\n"
            "- Leveling up gives you bonus XP\n\n"
            "Keep chatting to climb the leaderboard!"
        )
        update.message.reply_text(help_text, parse_mode='MarkdownV2')

    def error_handler(self, update: Update, context: CallbackContext) -> None:
        """Log errors."""
        logger.error(msg="Exception while handling an update:", exc_info=context.error)
        
        if update and update.effective_message:
            update.effective_message.reply_text(
                "An error occurred. Please try again later."
            )

    def calculate_xp_needed(self, level: int) -> int:
        """Calculate XP needed for the next level."""
        return 100 * (level ** 2)  # Quadratic growth

    def create_progress_bar(self, progress: int) -> str:
        """Create a text-based progress bar."""
        filled = '█' * (progress // 10)
        empty = '░' * (10 - (progress // 10))
        return f"[{filled}{empty}]"

    def run(self):
        """Start the bot."""
        # Start the Bot
        self.updater.start_polling()
        
        # Run the bot until you press Ctrl-C
        self.updater.idle()

if __name__ == '__main__':
    bot = ChatLevelsBot()
    bot.run()
