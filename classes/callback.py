from aiogram.filters.callback_data import CallbackData


class PageCallback(CallbackData, prefix="page"):
    link_page: str


class PaginationCard(CallbackData, prefix="pagination"):
    page: int


class ProductCallback(CallbackData, prefix="product"):
    product_id: str


class ToCardCallback(CallbackData, prefix="to_card"):
    product_id: str


class UpdateCardCallback(CallbackData, prefix="update_card"):
    product_id: str
