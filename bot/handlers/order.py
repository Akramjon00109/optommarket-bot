"""
Order Handler - Buyurtma holati tekshirish
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from bot.keyboards.inline import get_order_keyboard, get_back_keyboard, get_cancel_keyboard
from bot.services.database import db
from bot.services.product_service import product_service


router = Router(name="order")


class OrderStates(StatesGroup):
    """Order FSM states."""
    waiting_for_order_id = State()


@router.message(Command("order"))
async def cmd_order(message: Message, state: FSMContext):
    """Handle /order command."""
    await state.set_state(OrderStates.waiting_for_order_id)
    
    await message.answer(
        "📦 <b>Buyurtma holatini tekshirish</b>\n\n"
        "Buyurtma raqamingizni yoki telefon raqamingizni yuboring.\n\n"
        "<i>Masalan: 12345 yoki +998901234567</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.callback_query(F.data == "check_order")
async def callback_check_order(callback: CallbackQuery, state: FSMContext):
    """Handle order check callback."""
    await state.set_state(OrderStates.waiting_for_order_id)
    
    await callback.message.edit_text(
        "📦 <b>Buyurtma holatini tekshirish</b>\n\n"
        "Buyurtma raqamingizni yoki telefon raqamingizni yuboring.\n\n"
        "<i>Masalan: 12345 yoki +998901234567</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(OrderStates.waiting_for_order_id)
async def process_order_query(message: Message, state: FSMContext):
    """Process order query (ID or phone number)."""
    query = message.text.strip()
    await state.clear()
    
    logger.info(f"User {message.from_user.id} checking order: {query}")
    
    # Check if it's an order ID (only numbers)
    if query.isdigit():
        order = await db.get_order_by_id(int(query))
        
        if order:
            await show_order_details(message, order)
        else:
            await message.answer(
                f"❌ Buyurtma <b>#{query}</b> topilmadi.\n\n"
                "Buyurtma raqamini tekshirib qaytadan urinib ko'ring.",
                parse_mode="HTML",
                reply_markup=get_back_keyboard()
            )
    else:
        # Search by phone number
        orders = await db.get_orders_by_phone(query)
        
        if not orders:
            await message.answer(
                f"❌ <b>{query}</b> raqami bo'yicha buyurtmalar topilmadi.\n\n"
                "Telefon raqamingizni tekshirib qaytadan urinib ko'ring.",
                parse_mode="HTML",
                reply_markup=get_back_keyboard()
            )
        elif len(orders) == 1:
            order = await db.get_order_by_id(orders[0]['id'])
            await show_order_details(message, order)
        else:
            # Multiple orders found
            text = f"📱 <b>{query}</b> raqami bo'yicha topilgan buyurtmalar:\n\n"
            
            for order in orders:
                status_name = await db.get_order_status_name(order['status_id'])
                total = f"{order['total']:,.0f}".replace(",", " ")
                text += (
                    f"📦 <b>#{order['id']}</b> - {status_name}\n"
                    f"   💰 {total} so'm | 📅 {order['created_at']}\n\n"
                )
            
            text += "Batafsil ko'rish uchun buyurtma raqamini yuboring."
            
            await message.answer(
                text,
                parse_mode="HTML",
                reply_markup=get_back_keyboard()
            )


async def show_order_details(message: Message, order: dict):
    """Show order details."""
    status_name = await db.get_order_status_name(order['status_id'])
    total = f"{order['total']:,.0f}".replace(",", " ")
    
    # Status emoji
    status_emojis = {
        0: "🆕",  # Yangi
        1: "✅",  # Qabul qilindi
        2: "⏳",  # Jarayonda
        3: "🚚",  # Yuborildi
        4: "✅",  # Yetkazildi
        5: "❌"   # Bekor qilindi
    }
    status_emoji = status_emojis.get(order['status_id'], "📦")
    
    text = f"""
📦 <b>Buyurtma #{order['id']}</b>

{status_emoji} <b>Holati:</b> {status_name}
💰 <b>Jami:</b> {total} so'm

👤 <b>Xaridor:</b> {order.get('name_buyer', "Noma'lum")}
📱 <b>Telefon:</b> {order.get('phone', 'N/A')}
📍 <b>Manzil:</b> {order.get('address', 'N/A')}

📅 <b>Yaratilgan:</b> {order.get('created_at', 'N/A')}
🔄 <b>Yangilangan:</b> {order.get('updated_at', 'N/A')}
"""
    
    if order.get('comment'):
        text += f"\n💬 <b>Izoh:</b> {order['comment']}"
    
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_order_keyboard(order['id'])
    )


@router.callback_query(F.data.startswith("order_items:"))
async def callback_order_items(callback: CallbackQuery):
    """Show order items."""
    order_id = int(callback.data.split(":")[1])
    
    items = await db.get_order_items(order_id)
    
    if not items:
        await callback.answer("Buyurtma tarkibi topilmadi", show_alert=True)
        return
    
    text = f"📋 <b>Buyurtma #{order_id} tarkibi:</b>\n\n"
    
    total = 0
    for item in items:
        price = item['price']
        quantity = item['quantity']
        subtotal = price * quantity
        total += subtotal
        
        price_str = f"{price:,.0f}".replace(",", " ")
        subtotal_str = f"{subtotal:,.0f}".replace(",", " ")
        
        text += (
            f"📦 <b>{item['product_name']}</b>\n"
            f"   {quantity} x {price_str} = {subtotal_str} so'm\n"
        )
        
        if item.get('variants'):
            text += f"   📝 {item['variants']}\n"
        text += "\n"
    
    total_str = f"{total:,.0f}".replace(",", " ")
    text += f"─────────────────\n💰 <b>Jami: {total_str} so'm</b>"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard("main_menu")
    )
    await callback.answer()
