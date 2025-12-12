from aiogram.fsm.state import State, StatesGroup


class ToCard(StatesGroup):
    quantity = State()


class UpdateCard(StatesGroup):
    count_or_delete = State()


class ToOrder(StatesGroup):
    location = State()
