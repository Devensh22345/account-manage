#!/usr/bin/env python3
"""
Telegram Account Manager Bot - Main Entry Point
"""

import logging
import asyncio
import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update
from config import Config
from utils.helpers import setup_logging
from database.mongodb import init_database, get_database

# Import handlers
from handlers.login import handle_login, handle_login_message
from handlers.user import handle_settings, handle_user_message
from handlers.admin import handle_admin
from handlers.send import handle_send
from handlers.join_leave import handle_join, handle_leave
from handlers.report import handle_report, handle_stop
from handlers.otp import handle_otp

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

config = Config()

class AccountManagerBot:
    def __init__(self):
        self.config = config
        self.app = Application.builder().token(self.config.BOT_TOKEN).build()
        self.db = None
        
    async def initialize(self):
        """Initialize the bot"""
        logger.info("🚀 Starting Telegram Account Manager Bot...")
        
        # Check if BOT_TOKEN is set
        if not self.config.BOT_TOKEN or self.config.BOT_TOKEN == "your_bot_token_here":
            logger.error("❌ BOT_TOKEN not set in .env file!")
            logger.error("Please get a token from @BotFather and add it to .env")
            sys.exit(1)
        
        # Initialize database
        logger.info("📊 Initializing database...")
        if not await init_database():
            logger.error("❌ Failed to initialize database!")
            sys.exit(1)
        
        # Setup handlers
        self.setup_handlers()
        
        logger.info("✅ Bot initialization complete")
        
    def setup_handlers(self):
        """Setup all command handlers"""
        # Basic commands
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help))
        self.app.add_handler(CommandHandler("stats", self.stats))
        self.app.add_handler(CommandHandler("cancel", self.cancel))
        
        # Feature commands
        self.app.add_handler(CommandHandler("login", handle_login))
        self.app.add_handler(CommandHandler("set", handle_settings))
        self.app.add_handler(CommandHandler("admin", handle_admin))
        self.app.add_handler(CommandHandler("otp", handle_otp))
        self.app.add_handler(CommandHandler("send", handle_send))
        self.app.add_handler(CommandHandler("join", handle_join))
        self.app.add_handler(CommandHandler("leave", handle_leave))
        self.app.add_handler(CommandHandler("report", handle_report))
        self.app.add_handler(CommandHandler("stop", handle_stop))
        
        # Message handlers for state-based inputs
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_message
        ))
        
        # Error handler
        self.app.add_error_handler(self.error_handler)
        
    async def start(self, update: Update, context):
        """Handle /start command"""
        user = update.effective_user
        logger.info(f"👤 User {user.id} ({user.username}) started the bot")
        
        welcome_msg = (
            "👋 **Welcome to Telegram Account Manager!**\n\n"
            "I can help you manage multiple Telegram accounts with powerful features:\n\n"
            "📱 **Account Management**\n"
            "• Add/remove accounts with /login\n"
            "• Manage settings with /set\n\n"
            "⚡ **Admin Features**\n"
            "• Send messages with /send\n"
            "• Join/leave groups with /join and /leave\n"
            "• Manage OTPs with /otp\n"
            "• Report content with /report\n\n"
            "🔧 **Utilities**\n"
            "• /help - Show help guide\n"
            "• /stats - Show bot statistics\n"
            "• /cancel - Cancel current operation\n\n"
            "🚀 **Get started with /login to add your first account!**"
        )
        
        await update.message.reply_text(
            welcome_msg,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    
    async def help(self, update: Update, context):
        """Handle /help command"""
        help_msg = (
            "📚 **Help Guide**\n\n"
            "**Basic Commands:**\n"
            "• /start - Start the bot\n"
            "• /help - Show this help message\n"
            "• /stats - Show bot statistics\n"
            "• /cancel - Cancel current operation\n\n"
            "**Account Management:**\n"
            "• /login - Add new Telegram account\n"
            "• /set - User settings and account management\n\n"
            "**Admin Features:**\n"
            "• /admin - Admin panel\n"
            "• /otp - Get OTPs from accounts\n"
            "• /send - Send messages from accounts\n"
            "• /join - Join groups/channels\n"
            "• /leave - Leave groups/channels\n"
            "• /report - Report content\n"
            "• /stop - Stop current operation\n\n"
            "⚠️ **Note:** Some commands require admin privileges.\n"
            "Only the bot owner can grant admin access."
        )
        
        await update.message.reply_text(
            help_msg,
            parse_mode="Markdown"
        )
    
    async def stats(self, update: Update, context):
        """Handle /stats command"""
        from database.mongodb import get_accounts_collection, get_users_collection
        
        try:
            accounts_collection = await get_accounts_collection()
            users_collection = await get_users_collection()
            
            total_accounts = await accounts_collection.count_documents({"is_deleted": False})
            active_accounts = await accounts_collection.count_documents({
                "is_active": True,
                "is_deleted": False
            })
            total_users = await users_collection.count_documents({})
            
            stats_msg = (
                "📊 **Bot Statistics**\n\n"
                f"👥 **Total Users:** {total_users}\n"
                f"📱 **Total Accounts:** {total_accounts}\n"
                f"🟢 **Active Accounts:** {active_accounts}\n"
                f"🔴 **Inactive Accounts:** {total_accounts - active_accounts}\n\n"
                f"⚙️ **Bot Version:** 1.0.0\n"
                f"📅 **Uptime:** Starting up..."
            )
            
            await update.message.reply_text(
                stats_msg,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"❌ Error getting stats: {e}")
            await update.message.reply_text(
                "❌ Error retrieving statistics. Please try again later."
            )
    
    async def cancel(self, update: Update, context):
        """Handle /cancel command"""
        user_id = update.effective_user.id
        
        # Clear user data
        if 'user_data' in context.__dict__:
            context.user_data.clear()
        
        # Import and clear states from all handlers
        try:
            from handlers.login import login_states
            if user_id in login_states:
                del login_states[user_id]
                
            from handlers.user import user_states
            if user_id in user_states:
                del user_states[user_id]
                
            from handlers.admin import admin_states
            if user_id in admin_states:
                del admin_states[user_id]
                
        except Exception as e:
            logger.error(f"❌ Error clearing states: {e}")
        
        await update.message.reply_text(
            "✅ Current operation cancelled!\n"
            "You can start a new command."
        )
    
    async def handle_message(self, update: Update, context):
        """Handle regular messages for state-based operations"""
        user_id = update.effective_user.id
        text = update.message.text
        
        logger.info(f"📨 Message from {user_id}: {text[:50]}...")
        
        # Try to handle login messages
        try:
            from handlers.login import login_states, handle_login_message
            if user_id in login_states:
                await handle_login_message(update, context)
                return
        except Exception as e:
            logger.error(f"❌ Error in login message handler: {e}")
        
        # Try to handle user messages
        try:
            from handlers.user import user_states, handle_user_message
            if user_id in user_states:
                await handle_user_message(update, context)
                return
        except Exception as e:
            logger.error(f"❌ Error in user message handler: {e}")
        
        # If no state matched, send help
        await update.message.reply_text(
            "I didn't understand that command. Use /help to see available commands."
        )
    
    async def error_handler(self, update: Update, context):
        """Handle errors"""
        logger.error(f"❌ Error occurred: {context.error}")
        
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ An error occurred. Please try again or contact the admin."
                )
            except:
                pass
    
    async def run(self):
        """Run the bot"""
        try:
            # Initialize
            await self.initialize()
            
            # Start polling
            logger.info("🔄 Starting bot polling...")
            await self.app.initialize()
            await self.app.start()
            
            # Get updater
            updater = self.app.updater
            if updater:
                await updater.start_polling()
            
            logger.info("✅ Bot is now running! Press Ctrl+C to stop.")
            logger.info(f"🤖 Bot username: @{(await self.app.bot.get_me()).username}")
            
            # Keep running until interrupted
            await asyncio.Event().wait()
            
        except KeyboardInterrupt:
            logger.info("⏹️ Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Bot crashed: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the bot gracefully"""
        logger.info("🔌 Shutting down bot...")
        
        try:
            # Stop the application
            if self.app:
                await self.app.stop()
                await self.app.shutdown()
                
            # Close database connections
            from database.mongodb import db_instance
            if db_instance:
                await db_instance.close()
                
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
        
        logger.info("👋 Bot shutdown complete")

def main():
    """Main function"""
    # Check for .env file
    if not os.path.exists(".env"):
        print("❌ .env file not found!")
        print("Please copy .env.example to .env and add your credentials")
        sys.exit(1)
    
    # Create necessary directories
    os.makedirs("sessions", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("backups", exist_ok=True)
    
    # Run the bot
    bot = AccountManagerBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
