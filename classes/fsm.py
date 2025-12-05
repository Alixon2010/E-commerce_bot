from aiogram.fsm.state import StatesGroup, State

class ToCard(StatesGroup):
    quantity = State()

class UpdateCard(StatesGroup):
    count_or_delete = State()

class ToOrder(StatesGroup):
    location = State()