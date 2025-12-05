import requests
import stripe
from aiogram import Router, F, html
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from buttons.inline import create_inline_keyboard
from buttons.keyboard import create_keyboard
from classes.callback import PageCallback, ProductCallback, UpdateCardCallback, ToCardCallback

from classes.fsm import ToCard, UpdateCard, ToOrder
from database.base import async_session
from database.models import get_user
from settings import settings
from utils import request_get, request_post, request_delete

router = Router()

user_tokens = {}


@router.message(F.text == "/products")
async def products_handler(message: Message):
    response = requests.get(f"{settings.HOST}/api/v1/products/")
    if response.status_code == 200:
        data = response.json()
        products = [(product["name"][:20], ProductCallback(product_id=product["id"]).pack()) for product in
                    data["results"]]
        button = create_inline_keyboard(products, next=data["next"], previous=data["previous"])
        await message.answer(text="List Products:", reply_markup=button)
    else:
        await message.answer(text="Error :(")


@router.callback_query(PageCallback.filter())
async def products_callback(call, callback_data: PageCallback):
    link_page = callback_data.link_page
    response = await request_get(f"{settings.HOST}{link_page}")
    await call.answer()
    if response.status_code == 200:
        data = response.json()
        products = [(product["name"][:20], ProductCallback(product_id=product["id"]).pack()) for product in
                    data["results"]]
        button = create_inline_keyboard(products, next=data["next"], previous=data["previous"])
        await call.message.edit_text(text="List Products:", reply_markup=button)
    elif response.status_code == 404:
        await call.message.answer(text="Page Not Found!")


@router.callback_query(ProductCallback.filter())
async def product_detail(call, callback_data: ProductCallback):
    product_id = callback_data.product_id
    response = await request_get(f"{settings.HOST}/api/v1/products/{product_id}")
    await call.answer()
    if response.status_code == 200:
        data = response.json()
        text = f"""
        *{data['name']}*

        💰 Price: {data['price']} USD
        💸 Discount Percent: {data['discount_percent']}%
        ⭐ AVG raiting: {data.get('avg_rating', '—')}

        📦 Stock: {data['stock']}
        📝 Description:\n\n{data['description'][:4000]}

        🖼 Image: {data['image'] or 'Image does not exists'}
        """

        button = create_inline_keyboard([[("To Card", ToCardCallback(product_id=product_id).pack())]])
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=button)  # TODO
    else:
        await call.message.edit_text(text="Error :(")


@router.callback_query(ToCardCallback.filter())
async def find_quantity(call, callback_data: ToCardCallback, state):
    await call.answer()
    await call.message.answer("Enter the quantity")
    await state.set_data({"product_id": callback_data.product_id})
    await state.set_state(ToCard.quantity)


@router.message(ToCard.quantity)
async def validate_quantity(message, state: FSMContext):
    if message.text is None:
        await message.answer("Enter the number!!")
        return

    try:
        await state.update_data(quantity=int(message.text))
    except ValueError:
        await message.answer("Enter the number!!")
        return

    url = f"{settings.HOST}/api/v1/to_card/"
    user_id = message.from_user.id
    async with async_session() as session:
        user = await get_user(session, user_id)

    data = await state.get_data()
    response = await request_post(url, auth_token=user.token, **data)

    res = response.json()

    if res.get("quantity"):
        await message.answer("\n".join(res["quantity"]))
        return

    if res.get("messages"):
        await message.answer("\n".join(f"{key}: {value}" for key, value in res.get("messages")))

    await message.answer(res.get("message", "ERROR :("))

    if response.status_code == 200:
        await state.clear()


@router.message(F.text == "/my_card")
async def users_card(message):
    user_id = message.from_user.id
    async with async_session() as session:
        user = await get_user(session, user_id)

    url = f"{settings.HOST}/api/v1/card/"

    response = await request_get(url, auth_token=user.token)

    if response.status_code != 200:
        await message.answer("ERROR!")
        return

    data = "\n".join(
        f"{i}. {product["name"]}: {product["quantity"]} - {html.bold(round(product["price"], 2))}$" for i, product in
        enumerate(response.json()["products"], 1))
    data += f"\nTotal price: {round(response.json()["total_price"], 2)}$"
    button = create_inline_keyboard([[("Update card", "update_card"), ("To Order", "to_order")]])

    await message.answer(data, reply_markup=button)


@router.callback_query(F.data == "update_card")
async def update_card(call):
    user_id = call.from_user.id
    async with async_session() as session:
        user = await get_user(session, user_id)

    url = f"{settings.HOST}/api/v1/card/"

    response = await request_get(url, auth_token=user.token)

    await call.answer()
    if response.status_code != 200:
        await call.message.answer("ERROR!")
        return

    data = response.json()

    button = create_inline_keyboard(
        [(product["name"][:20], UpdateCardCallback(product_id=product["id"]).pack()) for product in data["products"]])

    await call.message.edit_text("Choose product:", reply_markup=button)


@router.callback_query(UpdateCardCallback.filter())
async def update_card_next(call, callback_data: UpdateCardCallback, state: FSMContext):
    await call.answer()
    await call.message.answer("Enter the new quantity\nEnter delete to delete from card\nEnter cancel to cancel")
    await state.set_data({"card_product_id": callback_data.product_id})
    await state.set_state(UpdateCard.count_or_delete)


@router.message(UpdateCard.count_or_delete)
async def count_or_delete(message, state: FSMContext):
    url = f"{settings.HOST}/api/v1/remove_card/{(await state.get_data())["card_product_id"]}"
    async with async_session() as session:
        user = await get_user(session, message.from_user.id)

    if message.text.lower() == "cancel":
        await state.clear()
        await message.answer("Update canceled")

    if message.text.lower() == "delete":
        response = await request_delete(url, auth_token=user.token)
        if response.status_code == 404:
            await message.answer(response.json()["detail"])
        elif response.status_code == 204:
            await message.answer("Product removed from card")
        await state.clear()

    if message.text.isdigit() and int(message.text) > 0:
        data = await state.get_data()
        data["quantity"] = int(message.text)
        url = f"{settings.HOST}/api/v1/update_card/"
        response = await request_post(url, auth_token=user.token, **data)
        if response.status_code == 200:
            await state.clear()

        await message.answer(response.json().get("message", "Error :("))
        return

    await message.answer("Enter a valid data")


@router.callback_query(F.data == "to_order")
async def to_order(call, state: FSMContext):
    await call.answer()
    button = create_keyboard([("Send location", "location")])
    await call.message.answer("Send your location", reply_markup=button)
    await state.set_state(ToOrder.location)


@router.message(F.location)
async def get_location(message: Message, state: FSMContext):
    locate = {
        "latitude": message.location.latitude,
        "longitude": message.location.longitude
    }

    async with async_session() as session:
        user = await get_user(session, message.from_user.id)

    url = f"{settings.HOST}/api/v1/to_order/"
    response = await request_post(url, auth_token=user.token, **locate)

    if response.status_code == 200:
        try:
            data = response.json()
            print("Data:", data)
        except Exception as e:
            print("JSON Error:", e)
            await message.answer("Server error")
            return

        payment_url = data['checkout_url']

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Pay", url=payment_url)],
            [InlineKeyboardButton(text="✅ Check", callback_data="check_payment")]
        ])

        await state.update_data(
            session_id=data['session_id'],
            checkout_url=payment_url
        )

        await message.answer(
            "✅ Follow the link to pay:",
            reply_markup=keyboard
        )
    else:
        await message.answer("Error creating order")
        await state.clear()


@router.callback_query(F.data == "check_payment")
async def check_payment(call, state: FSMContext):
    await call.answer()

    state_data = await state.get_data()
    session_id = state_data.get('session_id')

    if not session_id:
        await call.message.answer("❌ Session not found")
        return

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == 'paid':
            await call.message.answer("✅ Payment successful! Order confirmed.")

            await state.clear()

        elif session.payment_status == 'unpaid':
            await call.message.answer("❌ Payment not completed. Please complete the payment.")

        else:
            await call.message.answer(f"⏳ Status: {session.payment_status}")

    except stripe.error.StripeError as e:
        await call.message.answer(f"❌ Stripe error: {str(e)}")
    except Exception as e:
        await call.message.answer("❌ Error checking payment")
    