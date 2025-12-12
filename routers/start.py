from aiogram import Router, F
from aiogram.types import Message

from database.base import async_session
from database.models import get_or_create_user, get_user

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    """Welcome message with commands"""
    user_id = message.from_user.id

    async with async_session() as session:
        await get_or_create_user(session, user_id)

    async with async_session() as session:
        user = await get_user(session, user_id)
        logged_in = user and user.token and not user.is_expired

    if logged_in:
        welcome_text = """
    👋 <b>Welcome back!</b>

    You are logged in. Here's what you can do:

    🛒 <b>Shopping:</b>
    /products - Browse all products
    /my_cart - View your shopping cart

    📋 <b>Account:</b>
    /login - Switch account
    /register - Create new account

    💡 <b>Tips:</b>
    - Add products to cart from /products
    - Check out from /my_card
    - Your session expires in 50 hours
        """
    else:
        welcome_text = """
    🛍️ <b>Welcome to E-Commerce Bot!</b>

    This bot helps you shop online with ease.

    🔐 <b>First, you need to log in:</b>
    <code>/login email password</code>

    🆕 <b>New user? Register:</b>
    <code>/register email password password_confirm</code>

    🛒 <b>After login you can:</b>
    /products - Browse products
    /my_card - View shopping cart

    📱 <b>Example:</b>
    <code>/login user@example.com mypassword</code>
        """

    await message.answer(welcome_text, parse_mode="HTML")
