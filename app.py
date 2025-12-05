import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message
from datetime import datetime, timezone

from database.base import async_session, init
from database.models import get_user, create_user
from settings import settings

TOKEN = settings.BOT_TOKEN

dp = Dispatcher(storage=MemoryStorage())

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):

        if isinstance(event, Message):
            is_register = None
            is_login = None

            if event.text is not None:
                is_register = event.text.startswith("/register")
                is_login = event.text.startswith("/login")

        elif isinstance(event, CallbackQuery):
            is_register = False
            is_login = False
        else:
            return await handler(event, data)

        if not is_register and not is_login:
            user_id = event.from_user.id
            async with async_session() as session:
                user_data = await get_user(session, user_id)

            if not user_data:
                await event.answer("Use /login `password` to Authorization")
                return

            if user_data.exp_time and user_data.exp_time < datetime.now():
                await event.answer("Use /login `password` to Authorization")
                return

        return await handler(event, data)

dp.message.middleware(AuthMiddleware())

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await init()

    from routers import card_router, user_router, error_router

    dp.include_routers(card_router, user_router, error_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
