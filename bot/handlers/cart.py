"""
Cart Handler - Savatni boshqarish
Savatga qo'shish, ko'rish, o'zgartirish va tozalash.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest
from loguru import logger

from bot.services.cart import cart_service
from bot.keyboards.inline import get_cart_keyboard, get_back_keyboard, get_main_menu_keyboard
from bot.services.cart import cart_service
from bot.keyboards.inline import get_cart_keyboard, get_back_keyboard, get_main_menu_keyboard
from bot.services.product_service import product_service
from bot.services.facebook_pixel import fb_pixel


router = Router(name="cart")


@router.callback_query(F.data.startswith("add_to_cart:"))
async def callback_add_to_cart(callback: CallbackQuery):
    """Mahsulotni savatga qo'shish."""
    try:
        product_id = int(callback.data.split(":")[1])
        user_id = callback.from_user.id
        
        # Add to cart
        cart_service.add_item(user_id, product_id)
        
        # Get product name for notification
        product = await product_service.get_product_details(product_id)
        product_name = product['title'] if product else "Mahsulot"
        
        await callback.answer(f"✅ {product_name} savatga qo'shildi!", show_alert=True)

        # Send Pixel Event: AddToCart
        try:
            user_data = {
                "id": callback.from_user.id,
                "first_name": callback.from_user.first_name,
                "last_name": callback.from_user.last_name,
                "username": callback.from_user.username
            }
            
            custom_data = {
                "content_ids": [str(product_id)],
                "content_type": "product",
                "content_name": product_name,
                "value": product.get('price', 0) if product else 0,
                "currency": "UZS"
            }
            
            await fb_pixel.send_event("AddToCart", user_data, custom_data)
        except Exception as e:
            logger.error(f"Pixel error: {e}")
        
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)


@router.callback_query(F.data == "cart_view")
async def callback_view_cart(callback: CallbackQuery):
    """Savatni ko'rish."""
    user_id = callback.from_user.id
    
    # Get cart details
    cart = await cart_service.get_cart_details(user_id)
    
    if not cart["items"]:
        await callback.answer("Savat bo'sh", show_alert=True)
        # If message text is "Savat", we might want to update it or send new message
        # But here we assume it comes from main menu
        return

    # Format cart message
    text = "🛒 <b>Sizning savatingiz:</b>\n\n"
    
    for i, item in enumerate(cart["items"], 1):
        product = item["product"]
        text += (
            f"{i}. <b>{product['title']}</b>\n"
            f"   {item['count']} x {item['formatted_price']} = {item['formatted_subtotal']} so'm\n\n"
        )
    
    text += f"💰 <b>Jami: {cart['formatted_total_price']} so'm</b>"
    
    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_cart_keyboard(cart["items"], cart["total_price"])
        )
    except TelegramBadRequest:
        # If editing fails (e.g. same content or photo message), send new message
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_cart_keyboard(cart["items"], cart["total_price"])
        )

    await callback.answer()


@router.callback_query(F.data == "clear_cart")
async def callback_clear_cart(callback: CallbackQuery):
    """Savatni tozalash."""
    user_id = callback.from_user.id
    cart_service.clear_cart(user_id)
    
    await callback.answer("✅ Savat tozalandi")
    
    # Return to main menu
    await callback.message.edit_text(
        "🗑 Savat tozalandi.",
        reply_markup=get_back_keyboard()
    )
