from aiogram import Router
from aiogram.types import ErrorEvent

router = Router()


@router.error()
async def error_handler(event: ErrorEvent):
    error = event.exception

    print(f"⚠️ Error: {type(error).__name__}: {error}")

    # Можно отправить сообщение пользователю
    try:
        if hasattr(event.update, 'message'):
            await event.update.message.answer("😕 An error occurred. Please try again.")
        elif hasattr(event.update, 'callback_query'):
            await event.update.callback_query.message.answer("😕 An error occurred. Please try again.")
    except:
        pass

    return True