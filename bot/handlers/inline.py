"""
Inline Query Handler - Guruh chatlarda mahsulot ulashish
"""

from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from loguru import logger

from bot.services.product_service import product_service
from bot.config import settings


router = Router(name="inline")


@router.inline_query()
async def inline_search(inline_query: InlineQuery):
    """Handle inline queries for product search."""
    query = inline_query.query.strip()
    
    # If query is empty, show instructions
    if not query or len(query) < 2:
        results = [
            InlineQueryResultArticle(
                id="help",
                title="🔍 Mahsulot qidirish",
                description="Mahsulot nomini yozing (kamida 2 ta belgi)",
                input_message_content=InputTextMessageContent(
                    message_text="🛒 <b>OptomMarket</b>\n\nMahsulotlarni qidirish uchun @optommarketai_bot dan foydalaning!",
                    parse_mode="HTML"
                ),
                thumbnail_url="https://optommarket.uz/favicon.ico"
            )
        ]
        await inline_query.answer(results, cache_time=10)
        return
    
    logger.info(f"Inline search: '{query}' by user {inline_query.from_user.id}")
    
    # Search products
    products = await product_service.search_products(query=query, limit=10)
    
    if not products:
        results = [
            InlineQueryResultArticle(
                id="not_found",
                title="😔 Mahsulot topilmadi",
                description=f"'{query}' bo'yicha hech narsa topilmadi",
                input_message_content=InputTextMessageContent(
                    message_text=f"😔 '{query}' bo'yicha mahsulot topilmadi.\n\n🛒 Boshqa mahsulotlarni ko'rish: @optommarketai_bot",
                    parse_mode="HTML"
                )
            )
        ]
        await inline_query.answer(results, cache_time=30)
        return
    
    # Build results
    results = []
    for product in products:
        product_url = product.get('full_url', f"{settings.moguta_url}")
        
        # Format price
        price = product.get('formatted_price', '0')
        old_price = product.get('old_price', 0)
        
        # Build message text
        message_text = f"🏷 <b>{product['title']}</b>\n\n"
        message_text += f"💰 Narxi: <b>{price}</b> so'm\n"
        
        if old_price and float(old_price) > 0:
            old_price_formatted = product_service.format_price(old_price)
            message_text += f"🏷 Eski narxi: <s>{old_price_formatted}</s> so'm\n"
        
        # Stock status
        stock = product.get('stock', 0)
        if stock and int(stock) > 0:
            message_text += "📦 Mavjud ✅\n"
        else:
            message_text += "📦 Tugagan ❌\n"
        
        message_text += f"\n🛒 <a href='{product_url}'>Batafsil ko'rish</a>"
        
        # Create inline keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Sotib olish", url=product_url)]
        ])
        
        # Get thumbnail
        thumb_url = product.get('image_full_url', None)
        
        result = InlineQueryResultArticle(
            id=str(product['id']),
            title=product['title'],
            description=f"💰 {price} so'm",
            input_message_content=InputTextMessageContent(
                message_text=message_text,
                parse_mode="HTML"
            ),
            reply_markup=keyboard,
            thumbnail_url=thumb_url if thumb_url else None
        )
        results.append(result)
    
    await inline_query.answer(results, cache_time=60)
