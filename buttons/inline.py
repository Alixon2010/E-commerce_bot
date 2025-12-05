from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from classes.callback import PageCallback
from settings import settings


def create_inline_keyboard(buttons, row_width=3, next=None, previous=None) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    if all(isinstance(i, list) for i in buttons):
        for row in buttons:
            keyboard_row = [
                InlineKeyboardButton(text=text, callback_data=data) #TODO eslatma
                for text, data in row
            ]
            keyboard.inline_keyboard.append(keyboard_row)
    else:
        row = []
        for text, data in buttons:
            row.append(InlineKeyboardButton(text=text, callback_data=data))
            if len(row) == row_width:
                keyboard.inline_keyboard.append(row)
                row = []
        if row:
            keyboard.inline_keyboard.append(row)

    next_previous = []

    if previous is not None:
        next_previous.append(InlineKeyboardButton(text="Previous", callback_data=PageCallback(link_page=previous.replace(settings.HOST, "")).pack()))

    if next is not None:
        next_previous.append(InlineKeyboardButton(text="Next", callback_data=PageCallback(link_page=next.replace(settings.HOST, "")).pack()))

    if next_previous:
        keyboard.inline_keyboard.append(next_previous)

    return keyboard
