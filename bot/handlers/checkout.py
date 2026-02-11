"""
Checkout Handler - Buyurtma rasmiylashtirish
Ism, telefon va manzilni so'rab, buyurtma yaratish.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from bot.services.cart import cart_service
from bot.services.database import db
from bot.keyboards.inline import get_main_menu_keyboard
from bot.config import settings
from bot.services.facebook_pixel import fb_pixel

router = Router(name="checkout")


class CheckoutStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    confirm_order = State()


@router.callback_query(F.data == "checkout_start")
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    """Start checkout process."""
    user_id = callback.from_user.id
    cart = await cart_service.get_cart_details(user_id)
    
    if not cart["items"]:
        await callback.answer("Savatingiz bo'sh!", show_alert=True)
        return

    await state.set_state(CheckoutStates.waiting_for_name)
    
    # Store total price and items in state to avoid re-fetching or inconsistent data
    await state.update_data(
        cart_items=cart["items"],
        total_price=cart["total_price"]
    )
    
    await callback.message.delete()
    await callback.message.answer(
        "✍️ <b>Buyurtmani rasmiylashtirish</b>\n\n"
        "Iltimos, ismingizni kiriting:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    await callback.answer()

    # Send Pixel Event: InitiateCheckout
    try:
        user_data = {
            "id": callback.from_user.id,
            "first_name": callback.from_user.first_name,
            "last_name": callback.from_user.last_name,
            "username": callback.from_user.username
        }
        
        content_ids = [str(item['product']['id']) for item in cart["items"]]
        
        custom_data = {
            "content_ids": content_ids,
            "content_type": "product",
            "num_items": len(cart["items"]),
            "value": cart["total_price"],
            "currency": "UZS"
        }
        
        await fb_pixel.send_event("InitiateCheckout", user_data, custom_data)
    except Exception as e:
        logger.error(f"Pixel error: {e}")


@router.message(CheckoutStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Process name input."""
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("Iltimos, to'liq ismingizni kiriting.")
        return
    
    await state.update_data(name=name)
    await state.set_state(CheckoutStates.waiting_for_phone)
    
    # Request contact button
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        "📱 Iltimos, telefon raqamingizni yuboring yoki yozing (+998...):",
        reply_markup=keyboard
    )


@router.message(CheckoutStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Process phone input."""
    phone = ""
    
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip()
        # Basic validation
        import re
        if not re.match(r"^[\+]?[0-9]{9,15}$", phone):
            await message.answer("⚠️ Telefon raqam noto'g'ri formatda. Qaytadan kiriting:")
            return
            
    await state.update_data(phone=phone)
    await state.set_state(CheckoutStates.waiting_for_address)
    
    await message.answer(
        "📍 Yetkazib berish manzilini kiriting (Toshkent shahar...):",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(CheckoutStates.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    """Process address input."""
    address = message.text.strip()
    await state.update_data(address=address)
    
    data = await state.get_data()
    cart_items = data['cart_items']
    total_price = data['total_price']
    
    # Preview
    text = f"""✅ <b>Buyurtmani tasdiqlash</b>

👤 Xaridor: {data['name']}
📱 Telefon: {data['phone']}
📍 Manzil: {address}

🛒 Mahsulotlar: {len(cart_items)} xil
💰 <b>Jami to'lov: {total_price:,.0f} so'm</b>

Buyurtmani tasdiqlaysizmi?"""

    confirm_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Tasdiqlash"), KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await state.set_state(CheckoutStates.confirm_order)
    await message.answer(text, parse_mode="HTML", reply_markup=confirm_kb)


@router.message(CheckoutStates.confirm_order)
async def process_confirm(message: Message, state: FSMContext):
    """Confirmed order."""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Buyurtma bekor qilindi.", reply_markup=get_main_menu_keyboard())
        return

    if message.text != "✅ Tasdiqlash":
        await message.answer("Iltimos, tugmalardan birini tanlang.")
        return
    
    data = await state.get_data()
    user_id = message.from_user.id
    
    try:
        # Create order in DB
        order_id = await db.create_order(data, data['cart_items'])
        
        # Clear cart
        cart_service.clear_cart(user_id)
        
        # Notify admins (optional)
        # TODO: Send notification to Admin IDs
        
        await message.answer(
            f"🎉 <b>Rahmat! Buyurtmangiz qabul qilindi.</b>\n\n"
            f"🆔 Buyurtma raqami: <b>#{order_id}</b>\n"
            f"Biz tez orada siz bilan bog'lanamiz.",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
        
        # Send Pixel Event: Purchase
        try:
            # Prepare user data with phone number if available
            user_data = {
                "id": message.from_user.id,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "username": message.from_user.username,
                "phone": data.get('phone')
            }
            
            content_ids = [str(item['product']['id']) for item in data['cart_items']]
            
            custom_data = {
                "content_ids": content_ids,
                "content_type": "product",
                "num_items": len(data['cart_items']),
                "value": data['total_price'],
                "currency": "UZS",
                "order_id": str(order_id)
            }
            
            await fb_pixel.send_event("Purchase", user_data, custom_data)
        except Exception as e:
            logger.error(f"Pixel error: {e}")
        
    except Exception as e:
        logger.error(f"Failed to create order: {e}")
        await message.answer(
            "⚠️ Kechirasiz, buyurtma yaratishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
