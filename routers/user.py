
from aiogram import Router, F
from aiogram.types import Message

from database.base import async_session
from database.models import create_user, update_user_token, get_user
from settings import settings
from utils import request_post

router = Router()

@router.message(F.text.startswith("/register"))
async def register(message: Message):
    reg = message.text.split()[1:]

    if len(reg) != 3:
        await message.answer("/register `email` `password` `password_confirm`")
        return

    url = f"{settings.HOST}/api/v1/register/"

    response = await request_post(url, email=reg[0], password=reg[1], password_confirm=reg[2])

    if response.status_code == 201:
        user_id = message.from_user.id
        async with async_session() as session:
            await create_user(session, user_id)

    res = response.json()

    if res.get("email") is not None:
        await message.answer(response.json()["email"].get("message", "Error :("))
        return

    if isinstance(res.get("message"), list):
        await message.answer("\n".join(i for i in res.get("message")))
        return

    await message.answer(str(res.get("message", "Error :(")))

@router.message(F.text.startswith("/login"))
async def login(message: Message):
    l = message.text.split()[1:]
    if len(l) != 2:
        await message.answer("/login `identifier` `password`")
        return

    url = f"{settings.HOST}/api/v1/token/"

    response = await request_post(url, identifier=l[0], password=l[1])

    if response.status_code == 200:
        user_id = message.from_user.id
        async with async_session() as session:
            if not await get_user(session, user_id):
                await create_user(session, user_id)

            await update_user_token(session, user_id, response.json()["access"], 3)


        await message.answer("You're successfully authorized")
    else:
        res = response.json()
        if res.get("non_field_errors"):
            await message.answer("\n".join(i for i in res["non_field_errors"]))
            return

        await message.answer(response.json().get("message", "Error :("))