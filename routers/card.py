import requests
import stripe
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from buttons.inline import create_inline_keyboard
from buttons.keyboard import create_keyboard
from classes.callback import (
    PageCallback,
    ProductCallback,
    ToCardCallback,
    UpdateCardCallback,
)
from classes.fsm import ToCard, ToOrder, UpdateCard
from database.base import async_session
from database.models import get_user
from settings import settings
from utils import request_delete, request_get, request_post

router = Router()
user_tokens = {}


@router.message(F.text == "/products")
async def products_handler(message: Message):
    """Show product list"""
    response = requests.get(f"{settings.HOST}/api/v1/products/")
    if response.status_code == 200:
        data = response.json()
        products = [
            (
                f"📦 {product['name'][:20]}",
                ProductCallback(product_id=product["id"]).pack(),
            )
            for product in data["results"]
        ]
        button = create_inline_keyboard(
            products, next=data["next"], previous=data["previous"]
        )
        await message.answer(
            text="🛒 *Product List*:", reply_markup=button, parse_mode="Markdown"
        )
    else:
        await message.answer(text="❌ Error loading products")


@router.callback_query(PageCallback.filter())
async def products_callback(call, callback_data: PageCallback):
    """Products pagination"""
    link_page = callback_data.link_page
    response = await request_get(f"{settings.HOST}{link_page}")
    await call.answer()

    if response.status_code == 200:
        data = response.json()
        products = [
            (
                f"📦 {product['name'][:20]}",
                ProductCallback(product_id=product["id"]).pack(),
            )
            for product in data["results"]
        ]
        button = create_inline_keyboard(
            products, next=data["next"], previous=data["previous"]
        )
        await call.message.edit_text(
            text="🛒 *Product List*:", reply_markup=button, parse_mode="Markdown"
        )
    elif response.status_code == 404:
        await call.message.answer("❌ Page not found!")


@router.callback_query(ProductCallback.filter())
async def product_detail(call, callback_data: ProductCallback):
    """Show product details"""
    product_id = callback_data.product_id
    response = await request_get(f"{settings.HOST}/api/v1/products/{product_id}")
    await call.answer()

    if response.status_code == 200:
        data = response.json()
        text = f"""
📦 *{data['name']}*

💰 Price: {data['price']} USD
🎯 Discount: {data['discount_percent']}%
⭐ Average rating: {data.get('avg_rating') or "—"}

📊 Stock: {data['stock']}
📝 Description:\n{data['description'][:4000]}

🖼 Image: {data['image'] or 'No image available'}
        """
        button = create_inline_keyboard(
            [[("➕ Add to Cart", ToCardCallback(product_id=product_id).pack())]]
        )
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=button)
    else:
        await call.message.edit_text(text="❌ Error loading product details")


@router.callback_query(ToCardCallback.filter())
async def find_quantity(call, callback_data: ToCardCallback, state: FSMContext):
    """Ask for quantity to add to cart"""
    await call.answer()
    await call.message.answer("🔢 Please enter quantity:")
    await state.set_data({"product_id": callback_data.product_id})
    await state.set_state(ToCard.quantity)


@router.message(ToCard.quantity)
async def validate_quantity(message: Message, state: FSMContext):
    """Validate and add product to cart"""
    if message.text is None or not message.text.isdigit():
        await message.answer("❌ Please enter a valid number!")
        return

    try:
        quantity = int(message.text)
        if quantity <= 0:
            await message.answer("❌ Quantity must be greater than 0!")
            return
        await state.update_data(quantity=quantity)
    except ValueError:
        await message.answer("❌ Please enter a valid number!")
        return

    url = f"{settings.HOST}/api/v1/to_card/"
    async with async_session() as session:
        user = await get_user(session, message.from_user.id)

    data = await state.get_data()
    response = await request_post(url, auth_token=user.token, **data)
    res = response.json()

    if response.status_code == 200:
        await message.answer("✅ Product added to cart!")
        await state.clear()
    else:
        if res.get("quantity"):
            errors = "\n".join(res["quantity"])
            await message.answer(f"❌ Quantity errors:\n{errors}")
        elif res.get("message"):
            await message.answer(f"❌ {res['message']}")
        else:
            await message.answer("❌ Error adding to cart")


@router.message(F.text == "/my_cart")
async def users_card(message: Message):
    """Show user's shopping cart"""
    async with async_session() as session:
        user = await get_user(session, message.from_user.id)

    url = f"{settings.HOST}/api/v1/card/"
    response = await request_get(url, auth_token=user.token)

    if response.status_code != 200:
        await message.answer("❌ Error loading cart")
        return

    data = response.json()
    if not data["products"]:
        await message.answer("🛒 Your cart is empty!")
        return

    cart_items = "\n".join(
        f"{i}. 📦 {product['name']}: {product['quantity']} × {product['price']}$ "
        f"= *{round(product['total_price'], 2)}$*"
        for i, product in enumerate(data["products"], 1)
    )
    total = f"\n\n💰 *Total: {round(data['total_price'], 2)}$*"

    button = create_inline_keyboard(
        [[("✏️ Update Cart", "update_card")], [("✅ Place Order", "to_order")]]
    )

    await message.answer(
        f"🛒 *Your Cart:*\n{cart_items}{total}",
        reply_markup=button,
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "update_card")
async def update_card(call):
    """Show cart items for updating"""
    async with async_session() as session:
        user = await get_user(session, call.from_user.id)

    url = f"{settings.HOST}/api/v1/card/"
    response = await request_get(url, auth_token=user.token)
    await call.answer()

    if response.status_code != 200:
        await call.message.answer("❌ Error loading cart")
        return

    data = response.json()
    if not data["products"]:
        await call.message.edit_text("🛒 Your cart is empty!")
        return

    buttons = [
        (
            f"📦 {product['name'][:20]}",
            UpdateCardCallback(product_id=product["id"]).pack(),
        )
        for product in data["products"]
    ]
    button = create_inline_keyboard(buttons)

    await call.message.edit_text("✏️ Select product to update:", reply_markup=button)


@router.callback_query(UpdateCardCallback.filter())
async def update_card_next(call, callback_data: UpdateCardCallback, state: FSMContext):
    """Ask for new quantity or deletion"""
    await call.answer()
    instructions = """
✏️ *Update Product:*
Enter new quantity (number)
Or type 'delete' to remove from cart
Or type 'cancel' to cancel
    """
    await call.message.answer(instructions, parse_mode="Markdown")
    await state.set_data({"card_product_id": callback_data.product_id})
    await state.set_state(UpdateCard.count_or_delete)


@router.message(UpdateCard.count_or_delete)
async def count_or_delete(message: Message, state: FSMContext):
    """Process cart update"""
    async with async_session() as session:
        user = await get_user(session, message.from_user.id)

    data = await state.get_data()
    user_input = message.text.lower().strip()

    if user_input == "cancel":
        await state.clear()
        await message.answer("❌ Update cancelled")
        return

    if user_input == "delete":
        url = f"{settings.HOST}/api/v1/remove_card/{data['card_product_id']}"
        response = await request_delete(url, auth_token=user.token)
        if response.status_code == 204:
            await message.answer("✅ Product removed from cart")
        else:
            await message.answer("❌ Error removing product")
        await state.clear()
        return

    if user_input.isdigit() and int(user_input) > 0:
        data["quantity"] = int(user_input)
        url = f"{settings.HOST}/api/v1/update_card/"
        response = await request_post(url, auth_token=user.token, **data)
        if response.status_code == 200:
            await message.answer("✅ Cart updated successfully")
        else:
            await message.answer(f"❌ {response.json().get('message', 'Update error')}")
        await state.clear()
        return

    await message.answer(
        "❌ Please enter:\n- A number (e.g., '5')\n- 'delete'\n- 'cancel'"
    )


@router.callback_query(F.data == "to_order")
async def to_order(call, state: FSMContext):
    """Start order process"""
    await call.answer()
    button = create_keyboard([("📍 Send Location", "location")])
    await call.message.answer(
        "📍 Please send your delivery location:", reply_markup=button
    )
    await state.set_state(ToOrder.location)


@router.message(F.location)
async def get_location(message: Message, state: FSMContext):
    """Process location and create order"""
    locate = {
        "latitude": message.location.latitude,
        "longitude": message.location.longitude,
    }

    async with async_session() as session:
        user = await get_user(session, message.from_user.id)

    url = f"{settings.HOST}/api/v1/to_order/"
    response = await request_post(url, auth_token=user.token, **locate)

    if response.status_code == 200:
        try:
            data = response.json()
        except Exception:
            await message.answer("❌ Server error processing order")
            return

        payment_url = data["checkout_url"]
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Pay Now", url=payment_url)],
                [
                    InlineKeyboardButton(
                        text="✅ Check Payment", callback_data="check_payment"
                    )
                ],
            ]
        )

        await state.update_data(session_id=data["session_id"], checkout_url=payment_url)

        await message.answer(
            "✅ *Order Created!*\n\n"
            "Click the button below to complete payment.\n"
            "After payment, click 'Check Payment' to verify.",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
    else:
        await message.answer("❌ Error creating order")
        await state.clear()


@router.callback_query(F.data == "check_payment")
async def check_payment(call, state: FSMContext):
    """Check payment status"""
    await call.answer()

    state_data = await state.get_data()
    session_id = state_data.get("session_id")

    if not session_id:
        await call.message.answer("❌ No active order session found")
        return

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == "paid":
            await call.message.answer(
                "✅ *Payment Successful!*\n\n"
                "Your order has been confirmed and is being processed.\n"
                "We'll contact you with delivery details soon."
            )
            await state.clear()

        elif session.payment_status == "unpaid":
            await call.message.answer(
                "❌ *Payment Not Completed*\n\n"
                "Please complete the payment or try again."
            )

        else:
            await call.message.answer(f"⏳ Payment status: {session.payment_status}")

    except stripe.error.StripeError as e:
        await call.message.answer(f"❌ Stripe error: {str(e)}")
    except Exception:
        await call.message.answer("❌ Error checking payment status")
