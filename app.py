import asyncio
import logging
import sys
from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, CallbackQuery, Message

from database.base import async_session, init
from database.models import get_user
from settings import settings

TOKEN = settings.BOT_TOKEN

dp = Dispatcher(storage=MemoryStorage())


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        message = getattr(event, "message", None)
        callback = getattr(event, "callback_query", None)

        user_id = None
        is_auth_command = False

        if message:
            user_id = message.from_user.id
            text = message.text or ""

            is_auth_command = text.startswith((
                "/register",
                "/login",
                "/start"
            ))

        elif callback:
            user_id = callback.from_user.id

        if is_auth_command:
            return await handler(event, data)

        if user_id:
            async with async_session() as session:
                user_data = await get_user(session, user_id)

                if not user_data or not user_data.token:
                    if message:
                        await message.answer(
                            "🔒 Please login first!\n\n"
                            "<code>/login email password</code>\n"
                            "or\n"
                            "<code>/register email password password_confirm</code>"
                        )
                    elif callback:
                        await callback.answer(
                            "Please login first!",
                            show_alert=True
                        )
                    return

                if user_data.is_expired:
                    if message:
                        await message.answer(
                            "⏰ Session expired! Please login again:\n"
                            "<code>/login email password</code>"
                        )
                    elif callback:
                        await callback.answer(
                            "Session expired! Please login again.",
                            show_alert=True
                        )
                    return

        return await handler(event, data)



dp.update.outer_middleware(AuthMiddleware())


async def set_bot_commands(bot: Bot):
    """Set bot commands for menu"""
    commands = [
        BotCommand(command="/start", description="Start bot"),
        BotCommand(command="/register", description="Register new account"),
        BotCommand(command="/login", description="Login to account"),
        BotCommand(command="/products", description="Browse products"),
        BotCommand(command="/my_cart", description="View shopping cart"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await set_bot_commands(bot)

    await init()

    from routers import card_router, error_router, start_router, user_router

    dp.include_routers(start_router, user_router, card_router, error_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
