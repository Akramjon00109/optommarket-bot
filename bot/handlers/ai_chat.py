"""
AI Chat Handler - Tabiiy tilda suhbat
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from loguru import logger

from bot.keyboards.inline import get_products_list_keyboard, get_back_keyboard
from bot.services.ai_service import ai_service
from bot.services.product_service import product_service


router = Router(name="ai_chat")


@router.message(F.text)
async def handle_text_message(message: Message, state: FSMContext):
    """
    Handle any text message with AI.
    This handler has lowest priority and catches all text messages
    not handled by other handlers.
    """
    # Skip if in another state
    current_state = await state.get_state()
    if current_state:
        return
    
    user_id = message.from_user.id
    user_message = message.text.strip()
    
    logger.info(f"AI chat from user {user_id}: {user_message[:50]}...")
    
    # Show typing indicator
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Try AI-powered search first
        products, is_product_search = await product_service.ai_search(user_message)
        
        # Get AI response with product context
        ai_response, mentioned_products = await ai_service.get_response(
            user_id=user_id,
            user_message=user_message,
            products_context=products if is_product_search else None
        )
        
        # Send response with products if found
        if is_product_search and products:
            # Format response with products
            response_text = ai_response + "\n\n"
            
            for i, product in enumerate(products[:3], 1):
                stock_emoji = "✅" if product.get('stock', 0) > 0 else "❌"
                response_text += (
                    f"{i}. <b>{product['title']}</b>\n"
                    f"   💰 {product['formatted_price']} so'm {stock_emoji}\n\n"
                )
            
            await message.answer(
                response_text,
                parse_mode="HTML",
                reply_markup=get_products_list_keyboard(products[:5])
            )
        else:
            # Simple text response
            await message.answer(
                ai_response,
                parse_mode="HTML",
                reply_markup=get_back_keyboard() if len(ai_response) > 100 else None
            )
    except Exception as e:
        logger.error(f"AI chat error for user {user_id}: {e}")
        await message.answer(
            "Kechirasiz, hozirda texnik muammo bor. Iltimos, keyinroq urinib ko'ring.\n\n"
            "Yoki /search buyrug'i orqali mahsulotlarni qidirishingiz mumkin.",
            reply_markup=get_back_keyboard()
        )
