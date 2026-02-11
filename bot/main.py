"""
OptomMarket Telegram Bot - Main Entry Point
"""

import asyncio
import os
import sys
from pathlib import Path

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo
from dotenv import load_dotenv
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

from bot.config import settings
from bot.handlers import admin, ai_chat, broadcast, categories, inline, order, search, start
from bot.services.database import db
from bot.services.instagram_service import instagram_service
from bot.services.scheduler import scheduler_service


async def health_check(request):
    """Health check endpoint for hosting platform."""
    return web.Response(text="OK", status=200)


async def webhook_get(request):
    """Handle Meta Webhook verification (GET)."""
    mode = request.query.get("hub.mode")
    token = request.query.get("hub.verify_token")
    challenge = request.query.get("hub.challenge")

    if mode == "subscribe" and token == settings.meta_verify_token:
        logger.info("Webhook verified successfully")
        return web.Response(text=challenge, status=200)

    logger.warning("Webhook verification failed")
    return web.Response(text="Forbidden", status=403)


async def webhook_post(request):
    """Handle incoming Instagram webhook events (POST)."""
    try:
        data = await request.json()
        obj_type = (data.get("object") or "").lower()
        logger.info(f"Received webhook event object={obj_type}")

        for entry in data.get("entry", []):
            # 1) Direct messages in "messaging"
            for messaging in entry.get("messaging", []):
                sender_id = str(messaging.get("sender", {}).get("id", ""))
                message = messaging.get("message", {}) or {}
                text = message.get("text")
                is_echo = message.get("is_echo", False)

                if (
                    sender_id
                    and text
                    and not is_echo
                    and sender_id != str(settings.instagram_page_id or "")
                ):
                    asyncio.create_task(instagram_service.handle_message(sender_id, text))

            # 2) Changes payload (comments, mentions, some message shapes)
            for change in entry.get("changes", []):
                field = (change.get("field") or "").lower()
                value = change.get("value", {})

                # Some IG messaging events can come through changes/messages
                if field == "messages":
                    sender_id = str(value.get("sender", {}).get("id", ""))
                    text = (value.get("message") or {}).get("text")
                    if sender_id and text and sender_id != str(settings.instagram_page_id or ""):
                        asyncio.create_task(instagram_service.handle_message(sender_id, text))
                    continue

                if field not in {"comments", "mentions", "feed"}:
                    continue

                # Page feed events: only process new comments
                if obj_type == "page" and field in {"feed", "comments"}:
                    item = (value.get("item") or "").lower()
                    verb = (value.get("verb") or "").lower()
                    if not (item == "comment" and verb == "add"):
                        continue

                comment_id = value.get("id") or value.get("comment_id")
                text = value.get("text") or value.get("message")
                from_user = value.get("from", {}) or {}
                sender_id = str(from_user.get("id", ""))
                sender_name = from_user.get("username") or from_user.get("name")
                media_id = (value.get("media", {}) or {}).get("id") or value.get("post_id", "")

                if (
                    comment_id
                    and sender_id
                    and text
                    and sender_id != str(settings.instagram_page_id or "")
                ):
                    asyncio.create_task(
                        instagram_service.handle_comment(
                            str(comment_id),
                            sender_id,
                            sender_name,
                            str(text),
                            str(media_id),
                        )
                    )

        return web.Response(text="EVENT_RECEIVED", status=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(text="Error", status=500)


async def start_health_server():
    """Start health server with Meta webhook routes."""
    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_get("/", health_check)
    app.router.add_get("/webhook", webhook_get)
    app.router.add_post("/webhook", webhook_post)

    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Men {port}-portda eshityapman (0.0.0.0:{port})")


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    ),
    level=settings.log_level,
)
logger.add(
    "logs/bot_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
)


async def set_bot_commands(bot: Bot):
    """Set bot commands in Telegram menu."""
    commands = [
        BotCommand(command="start", description="Bosh menyu"),
        BotCommand(command="search", description="Mahsulot qidirish"),
        BotCommand(command="order", description="Buyurtma holati"),
        BotCommand(command="help", description="Yordam"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Bot commands set")


async def set_menu_button(bot: Bot):
    """Set Telegram web app menu button."""
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Do'kon",
                web_app=WebAppInfo(url=settings.moguta_url),
            )
        )
        logger.info(f"Menu button set to: {settings.moguta_url}")
    except Exception as e:
        logger.warning(f"Failed to set menu button: {e}")


async def on_startup(bot: Bot):
    """Startup hooks."""
    logger.info("Starting OptomMarket Bot")
    await db.connect()
    await set_bot_commands(bot)
    await set_menu_button(bot)

    scheduler_service.set_bot(bot)
    scheduler_service.start()

    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")

    logger.info(f"Instagram token configured: {bool(settings.instagram_page_access_token)}")
    logger.info(f"Instagram page id configured: {bool(settings.instagram_page_id)}")
    logger.info(f"Meta verify token configured: {bool(settings.meta_verify_token)}")
    logger.info(f"Meta access token configured: {bool(settings.meta_access_token)}")
    logger.info(f"Meta pixel id configured: {bool(settings.meta_pixel_id)}")


async def on_shutdown(bot: Bot):
    """Shutdown hooks."""
    logger.info("Shutting down bot")
    scheduler_service.stop()
    await db.disconnect()
    logger.info("Bot stopped")


def setup_routers(dp: Dispatcher):
    """Register all routers."""
    # Order matters: ai_chat should be last (catch-all).
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(broadcast.router)
    dp.include_router(search.router)
    dp.include_router(order.router)
    dp.include_router(categories.router)
    dp.include_router(inline.router)
    dp.include_router(ai_chat.router)
    logger.info("Routers registered")


async def main():
    """Main async entrypoint."""
    await start_health_server()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    setup_routers(dp)

    try:
        logger.info("Starting polling")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
