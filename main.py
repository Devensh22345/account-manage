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
        
        # Create updater
        self.app.updater = None
        await self.app.updater.start_polling()
        
        logger.info("Bot started successfully!")
        logger.info(f"Owner ID: {self.config.OWNER_ID}")
        logger.info(f"Database: {self.config.DB_NAME}")
        
    def setup_handlers(self):
        """Setup all command and callback handlers"""
        
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help))
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
        self.app.add_handler(CommandHandler("stats", self.show_stats))
        
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
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_message
        ))
        
    async def start(self, update: Update, context):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        # Check if user exists in database
        users_collection = self.db.users
        user_data = await users_collection.find_one({"user_id": user_id})
        
        if not user_data:
            # Create new user entry
            await users_collection.insert_one({
                "user_id": user_id,
                "username": update.effective_user.username,
                "first_name": update.effective_user.first_name,
                "last_name": update.effective_user.last_name,
                "is_admin": False,
                "is_owner": user_id == self.config.OWNER_ID,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
        
        welcome_message = (
            "👋 **Welcome to Telegram Account Manager!**\n\n"
            "This bot allows you to manage multiple Telegram accounts "
            "with powerful automation features.\n\n"
            "**Available Commands:**\n"
            "• `/login` - Add new Telegram account\n"
            "• `/set` - User settings and account management\n"
            "• `/admin` - Admin panel (admin only)\n"
            "• `/otp` - Get OTPs from accounts\n"
            "• `/send` - Send messages from accounts\n"
            "• `/join` - Join groups/channels\n"
            "• `/leave` - Leave groups/channels\n"
            "• `/report` - Report users/groups\n"
            "• `/stop` - Stop current operation\n"
            "• `/cancel` - Cancel current process\n"
            "• `/stats` - Show bot statistics\n\n"
            "**⚠️ Important:**\n"
            "• Use at your own risk\n"
            "• Follow Telegram ToS\n"
            "• Don't spam or abuse\n"
            "• Keep your sessions secure"
        )
        
        await update.message.reply_text(
            welcome_message,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    
    async def help(self, update: Update, context):
        """Handle /help command"""
        help_message = (
            "📚 **Help Guide**\n\n"
            "**Getting Started:**\n"
            "1. Use `/login` to add your first account\n"
            "2. Follow the prompts (API ID, API Hash, etc.)\n"
            "3. Verify with OTP if needed\n\n"
            "**Managing Accounts:**\n"
            "• `/set` - View and manage your accounts\n"
            "• Remove inactive accounts from the settings\n"
            "• Set up log channels for activity tracking\n\n"
            "**Admin Features:**\n"
            "• Bulk message sending\n"
            "• Mass join/leave operations\n"
            "• Reporting system\n"
            "• Account statistics\n\n"
            "**Safety Tips:**\n"
            "• Don't share session strings\n"
            "• Use strong passwords\n"
            "• Monitor account activity\n"
            "• Remove unused accounts\n\n"
            "Need more help? Contact the bot owner."
        )
        
        await update.message.reply_text(
            help_message,
            parse_mode="Markdown"
        )
    
    async def show_stats(self, update: Update, context):
        """Handle /stats command"""
        from utils.helpers import get_active_accounts_count
        
        user_id = update.effective_user.id
        
        # Get statistics
        accounts_collection = self.db.accounts
        users_collection = self.db.users
        
        total_accounts = await accounts_collection.count_documents({"is_deleted": False})
        active_accounts = await accounts_collection.count_documents({
            "is_active": True,
            "is_deleted": False
        })
        total_users = await users_collection.count_documents({})
        
        user_accounts = await accounts_collection.count_documents({
            "user_id": user_id,
            "is_deleted": False
        })
        
        stats_message = (
            f"📊 **Bot Statistics**\n\n"
            f"👥 Total Users: {total_users}\n"
            f"📱 Total Accounts: {total_accounts}\n"
            f"🟢 Active Accounts: {active_accounts}\n"
            f"👤 Your Accounts: {user_accounts}\n\n"
            f"💾 Database: {self.config.DB_NAME}\n"
            f"⚙️ Bot Version: 1.0.0"
        )
        
        await update.message.reply_text(
            stats_message,
            parse_mode="Markdown"
        )
    
    async def handle_cancel(self, update: Update, context):
        """Handle /cancel command"""
        user_id = update.effective_user.id
        
        # Clear all states
        from handlers.login import login_states
        from handlers.user import user_states
        from handlers.admin import admin_states
        from handlers.send import send_states
        from handlers.join_leave import join_states, leave_states
        from handlers.report import report_states
        
        states_to_clear = [
            login_states, user_states, admin_states,
            send_states, join_states, leave_states, report_states
        ]
        
        for state_dict in states_to_clear:
            if user_id in state_dict:
                del state_dict[user_id]
        
        # Clear user data
        context.user_data.clear()
        
        await update.message.reply_text("✅ Current operation cancelled!")
    
    async def handle_message(self, update: Update, context):
        """Handle regular messages"""
        # Route to appropriate handler based on user state
        user_id = update.effective_user.id
        
        from handlers.login import login_states, handle_login_message
        from handlers.user import user_states, handle_user_message
        from handlers.admin import admin_states, handle_admin_message
        from handlers.send import send_states, handle_send_message
        from handlers.join_leave import join_states, leave_states, handle_join_message, handle_leave_message
        from handlers.report import report_states, handle_report_message
        
        # Check each state and route accordingly
        if user_id in login_states:
            await handle_login_message(update, context)
        elif user_id in user_states:
            await handle_user_message(update, context)
        elif user_id in admin_states:
            await handle_admin_message(update, context)
        elif user_id in send_states:
            await handle_send_message(update, context)
        elif user_id in join_states:
            await handle_join_message(update, context)
        elif user_id in leave_states:
            await handle_leave_message(update, context)
        elif user_id in report_states:
            await handle_report_message(update, context)
        else:
            # No active state, send help
            await update.message.reply_text(
                "I didn't understand that command. Use /help to see available commands."
            )
    
    async def run(self):
        """Run the bot"""
        try:
            await self.initialize()
            
            # Log startup complete
            logger.info("Bot is running... Press Ctrl+C to stop")
            
            # Keep the bot running
            await self.app.updater.idle()
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown bot gracefully"""
        logger.info("Shutting down bot...")
        
        # Cancel all active tasks
        from handlers.send import active_send_tasks
        from handlers.join_leave import active_join_tasks, active_leave_tasks
        from handlers.report import active_report_tasks
        from handlers.otp import active_otp_tasks
        
        all_tasks = [
            active_send_tasks,
            active_join_tasks,
            active_leave_tasks,
            active_report_tasks,
            active_otp_tasks
        ]
        
        for task_dict in all_tasks:
            for user_id, task in task_dict.items():
                try:
                    task.cancel()
                except:
                    pass
        
        # Stop the bot
        if self.app:
            try:
                await self.app.stop()
                await self.app.shutdown()
            except:
                pass
        
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    bot = AccountManagerBot()
    asyncio.run(bot.run())
