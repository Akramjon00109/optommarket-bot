"""
Search Handler - Mahsulot qidirish funksiyalari
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from bot.keyboards.inline import (
    get_products_list_keyboard,
    get_product_keyboard,
    get_categories_keyboard,
    get_back_keyboard,
    get_cancel_keyboard
)
from bot.services.database import db
from bot.services.product_service import product_service
from bot.services.ai_service import ai_service
from bot.services.facebook_pixel import fb_pixel


router = Router(name="search")


class SearchStates(StatesGroup):
    """Search FSM states."""
    waiting_for_query = State()


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    """Handle /search command."""
    await state.set_state(SearchStates.waiting_for_query)
    
    await message.answer(
        "🔍 <b>Mahsulot qidirish</b>\n\n"
        "Qidirmoqchi bo'lgan mahsulot nomini yozing.\n\n"
        "<i>Masalan: ko'ylak, futbolka, ayollar kiyimi</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.callback_query(F.data == "search_products")
async def callback_search(callback: CallbackQuery, state: FSMContext):
    """Handle search callback."""
    await state.set_state(SearchStates.waiting_for_query)
    
    await callback.message.edit_text(
        "🔍 <b>Mahsulot qidirish</b>\n\n"
        "Qidirmoqchi bo'lgan mahsulot nomini yozing.\n\n"
        "<i>Masalan: ko'ylak, futbolka, ayollar kiyimi</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()




@router.message(SearchStates.waiting_for_query)
async def process_search_query(message: Message, state: FSMContext):
    """Process search query."""
    query = message.text.strip()
    
    # Save query for pagination and clear state
    await state.set_state(None)
    await state.update_data(last_search_query=query)
    
    # Show typing indicator
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    logger.info(f"User {message.from_user.id} searching: {query}")
    
    # Search products
    products = await product_service.search_products(query=query, limit=10)
    
    if not products:
        # Fallback to AI chat
        ai_response, _ = await ai_service.get_response(message.from_user.id, query)
        await message.answer(
            ai_response,
            parse_mode="HTML",
            reply_markup=get_back_keyboard()
        )
        return
    # Format response
    response = f"🔍 <b>\"{query}\"</b> bo'yicha natijalar:\n\n"
    
    for i, product in enumerate(products[:5], 1):
        stock_emoji = "✅" if product.get('stock', 0) > 0 else "❌"
        response += (
            f"{i}. <b>{product['title']}</b>\n"
            f"   💰 {product['formatted_price']} so'm | {stock_emoji}\n\n"
        )
    
    has_more = len(products) > 5
    if has_more:
        response += f"<i>...va yana {len(products) - 5} ta mahsulot</i>"
    
    await message.answer(
        response,
        parse_mode="HTML",
        reply_markup=get_products_list_keyboard(
            products[:5], 
            page=0, 
            has_more=has_more,
            callback_prefix="search_page"
        )
    )


@router.callback_query(F.data.startswith("search_page:"))
async def callback_search_page(callback: CallbackQuery, state: FSMContext):
    """Handle search pagination."""
    try:
        page = int(callback.data.split(":")[1])
        
        # Get query from state
        data = await state.get_data()
        query = data.get("last_search_query")
        
        if not query:
            await callback.answer("Qidiruv natijalari eskirgan. Qaytadan qidiring.", show_alert=True)
            return
            
        offset = page * 5
        limit = 6  # 5 + 1 check
        
        products = await product_service.search_products(query=query, limit=limit, offset=offset)
        
        if not products:
            await callback.answer("Boshqa natija yo'q", show_alert=True)
            return

        has_more = len(products) > 5
        display_products = products[:5]
        
        response = f"🔍 <b>\"{query}\"</b> bo'yicha natijalar (Sahifa: {page+1}):\n\n"
        
        for i, product in enumerate(display_products, 1):
            stock_emoji = "✅" if product.get('stock', 0) > 0 else "❌"
            response += (
                f"{i}. <b>{product['title']}</b>\n"
                f"   💰 {product['formatted_price']} so'm | {stock_emoji}\n\n"
            )
            
        keyboard = get_products_list_keyboard(
            display_products, 
            page=page, 
            has_more=has_more,
            callback_prefix="search_page"
        )
        
        await callback.message.edit_text(
            response,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in search pagination: {e}")
        await callback.answer("Xatolik", show_alert=True)


@router.callback_query(F.data.startswith("product:"))
async def callback_product(callback: CallbackQuery):
    """Show product details."""
    product_id = int(callback.data.split(":")[1])
    
    product = await product_service.get_product_details(product_id)
    
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    
    # Format product card
    text = await product_service.format_product_card(product)
    
    # Send photo if available
    if product.get('image_full_url'):
        try:
            await callback.message.answer_photo(
                photo=product['image_full_url'],
                caption=text,
                parse_mode="HTML",
                reply_markup=get_product_keyboard(product)
            )
        except Exception:
            await callback.message.answer(
                text,
                parse_mode="HTML",
                reply_markup=get_product_keyboard(product)
            )
    else:
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_product_keyboard(product)
        )
    # Send Pixel Event: ViewContent
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
            "content_name": product.get('title', ''),
            "value": product.get('price', 0),
            "currency": "UZS"
        }
        
        await fb_pixel.send_event("ViewContent", user_data, custom_data)
    except Exception as e:
        logger.error(f"Pixel error: {e}")

    await callback.answer()
