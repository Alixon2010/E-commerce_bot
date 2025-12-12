from aiogram import F, Router
from aiogram.types import Message

from database.base import async_session
from database.models import get_or_create_user, update_user_token
from settings import settings
from utils import request_post
import re

router = Router()


def is_valid_email(email: str) -> bool:
    """Simple email validation"""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None


@router.message(F.text.startswith("/register"))
async def register(message: Message):
    """Handle user registration - no errors, user can register multiple times"""
    try:
        # Parse command
        parts = message.text.split()
        if len(parts) < 4:
            await message.answer(
                "Usage: /register email password password_confirm\n"
                "Example: <code>/register test@example.com pass123 pass123</code>"
            )
            return

        _, email, password, password_confirm = parts

        email = email.strip().lower()
        password = password.strip()
        password_confirm = password_confirm.strip()

        if not is_valid_email(email):
            await message.answer(
                "❌ Please enter a valid email address (e.g., user@example.com)"
            )
            return

        if len(password) < 6:
            await message.answer("❌ Password must be at least 6 characters")
            return

        if password != password_confirm:
            await message.answer("❌ Passwords do not match")
            return

        user_id = message.from_user.id
        async with async_session() as session:
            await get_or_create_user(session, user_id)  # ← No duplicate errors

        url = f"{settings.HOST}/api/v1/register/"
        response = await request_post(
            url, email=email, password=password, password_confirm=password_confirm
        )

        if response.status_code == 201:
            await message.answer(
                "✅ Registration successful!\n\n"
                "You can now login with:\n"
                f"<code>/login {email} {password}</code>\n\n"
                "Start shopping with /products"
            )
        else:
            data = response.json()
            error_lines = []
            for key, value in data.items():
                if isinstance(value, list):
                    error_lines.append(f"{key}: {', '.join(value)}")
                elif isinstance(value, str):
                    error_lines.append(f"{key}: {value}")

            if error_lines:
                await message.answer("❌ " + "\n".join(error_lines)[:1000])
            else:
                await message.answer("❌ Registration failed")

    except Exception as e:
        error = str(e)
        if len(error) > 100:
            error = error[:100] + "..."
        await message.answer(f"❌ Error: {error}")


@router.message(F.text.startswith("/login"))
async def login(message: Message):
    """Handle user login - simple version"""
    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer(
                "Usage: /login identifier password\n"
                "Example: <code>/login user@example.com mypassword</code>"
            )
            return

        _, identifier, password = parts

        identifier = identifier.strip()
        password = password.strip()

        url = f"{settings.HOST}/api/v1/token/"
        response = await request_post(url, identifier=identifier, password=password)

        if response.status_code == 200:
            data = response.json()
            access_token = data["access"]

            user_id = message.from_user.id
            async with async_session() as session:
                await get_or_create_user(session, user_id)
                await update_user_token(session, user_id, access_token, 50)

            await message.answer(
                "✅ Login successful!\n\n"
                "You can now:\n"
                "/products - Browse products\n"
                "/my_cart - View your cart\n\n"
                "Happy shopping! 🛒"
            )
        else:
            data = response.json()
            error_msg = data.get("message", "Login failed")

            if "non_field_errors" in data:
                errors = "\n".join(data["non_field_errors"])
                await message.answer(f"❌ {errors}")
            else:
                await message.answer(f"❌ {error_msg}")

    except Exception as e:
        error = str(e)
        if len(error) > 100:
            error = error[:100] + "..."
        await message.answer(f"❌ Error: {error}")
