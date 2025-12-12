from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def create_keyboard(
    buttons,
    row_width=3,
    resize=True,
    one_time=True,
) -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=resize, one_time_keyboard=one_time, keyboard=[]
    )

    if all(isinstance(i, list) for i in buttons):
        for row in buttons:
            keyboard_row = []
            for b in row:
                if len(b) == 2 and b[1] == "location":
                    keyboard_row.append(
                        KeyboardButton(text=b[0], request_location=True)
                    )
                elif len(b) == 2 and b[1] == "contact":
                    keyboard_row.append(KeyboardButton(text=b[0], request_contact=True))
                else:
                    keyboard_row.append(KeyboardButton(text=b[0]))
            keyboard.keyboard.append(keyboard_row)
    else:
        # плоский список
        row = []
        for b in buttons:
            if isinstance(b, tuple) and len(b) == 2 and b[1] == "location":
                row.append(KeyboardButton(text=b[0], request_location=True))
            elif isinstance(b, tuple) and len(b) == 2 and b[1] == "contact":
                row.append(KeyboardButton(text=b[0], request_contact=True))
            else:
                row.append(KeyboardButton(text=b if isinstance(b, str) else b[0]))

            if len(row) == row_width:
                keyboard.keyboard.append(row)
                row = []
        if row:
            keyboard.keyboard.append(row)

    return keyboard
