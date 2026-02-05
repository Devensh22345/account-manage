import logging
import asyncio
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update
from config import Config
from database.mongodb import get_database
from handlers import (
    admin, user, login, send, 
    join_leave, report, otp
)
from utils.helpers import setup_logging

# Setup logging
setup_logging()

logger = logging.getLogger(__name__)

class AccountManagerBot:
    def __init__(self):
        self.config = Config()
        self.app = Application.builder().token(self.config.BOT_TOKEN).build()
        self.db = None
        
    async def initialize(self):
        """Initialize database and setup handlers"""
        # Connect to MongoDB
        self.db = await get_database()
        
        # Setup handlers
        self.setup_handlers()
        
        # Start bot
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        logger.info("Bot started successfully!")
        
    def setup_handlers(self):
        """Setup all command and callback handlers"""
        
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("login", login.handle_login))
        self.app.add_handler(CommandHandler("set", user.handle_settings))
        self.app.add_handler(CommandHandler("admin", admin.handle_admin))
        self.app.add_handler(CommandHandler("otp", otp.handle_otp))
        self.app.add_handler(CommandHandler("send", send.handle_send))
        self.app.add_handler(CommandHandler("join", join_leave.handle_join))
        self.app.add_handler(CommandHandler("leave", join_leave.handle_leave))
        self.app.add_handler(CommandHandler("report", report.handle_report))
        self.app.add_handler(CommandHandler("stop", report.handle_stop))
        self.app.add_handler(CommandHandler("cancel", self.handle_cancel))
        
        # Callback query handlers
        self.app.add_handler(CallbackQueryHandler(login.handle_login_callback, pattern="^login_"))
        self.app.add_handler(CallbackQueryHandler(user.handle_user_callback, pattern="^user_"))
        self.app.add_handler(CallbackQueryHandler(admin.handle_admin_callback, pattern="^admin_"))
        self.app.add_handler(CallbackQueryHandler(otp.handle_otp_callback, pattern="^otp_"))
        self.app.add_handler(CallbackQueryHandler(send.handle_send_callback, pattern="^send_"))
        self.app.add_handler(CallbackQueryHandler(join_leave.handle_join_callback, pattern="^join_"))
        self.app.add_handler(CallbackQueryHandler(join_leave.handle_leave_callback, pattern="^leave_"))
        self.app.add_handler(CallbackQueryHandler(report.handle_report_callback, pattern="^report_"))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
    async def start(self, update: Update, context):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        await update.message.reply_text(
            "👋 Welcome to Telegram Account Manager!\n\n"
            "Available commands:\n"
            "/login - Login new Telegram account\n"
            "/set - User settings\n"
            "/admin - Admin panel (admin only)\n"
            "/otp - Get OTP from accounts\n"
            "/send - Send messages\n"
            "/join - Join groups/channels\n"
            "/leave - Leave groups/channels\n"
            "/report - Report users/groups\n"
            "/stop - Stop current operation\n"
            "/cancel - Cancel current process"
        )
        
    async def handle_cancel(self, update: Update, context):
        """Handle /cancel command"""
        user_id = update.effective_user.id
        context.user_data.clear()
        
        await update.message.reply_text("✅ Current operation cancelled!")
        
    async def handle_message(self, update: Update, context):
        """Handle regular messages"""
        # Handle state-based responses (like OTP, API credentials, etc.)
        await login.handle_login_message(update, context)
        await admin.handle_admin_message(update, context)
        await user.handle_user_message(update, context)
        
    async def run(self):
        """Run the bot"""
        try:
            await self.initialize()
            
            # Keep the bot running
            await asyncio.Event().wait()
            
        except Exception as e:
            logger.error(f"Bot error: {e}")
        finally:
            await self.shutdown()
            
    async def shutdown(self):
        """Shutdown bot gracefully"""
        if self.app:
            await self.app.stop()
            await self.app.shutdown()

if __name__ == "__main__":
    bot = AccountManagerBot()
    asyncio.run(bot.run())
