from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger

from bot.services.database import db
from bot.services.product_service import product_service
from bot.keyboards.inline import get_categories_keyboard, get_products_list_keyboard

router = Router(name="categories")



async def edit_or_answer(callback: CallbackQuery, text: str, reply_markup):
    """Edit message text or delete and send new one (if photo)."""
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode="HTML")


@router.callback_query(F.data == "categories")
async def callback_categories_root(callback: CallbackQuery):
    """Show root categories."""
    try:
        categories = await db.get_categories(parent_id=0)
        keyboard = get_categories_keyboard(categories, parent_id=0)
        await edit_or_answer(callback, "📂 <b>Kategoriyalar</b>", keyboard)
    except Exception as e:
        logger.error(f"Error showing categories: {e}")
        await callback.answer("Xatolik yuz berdi", show_alert=True)


@router.callback_query(F.data.startswith("category:"))
async def callback_category_view(callback: CallbackQuery):
    """Show subcategories or products."""
    try:
        cat_id = int(callback.data.split(":")[1])
        
        # 0 = Root
        if cat_id == 0:
            await callback_categories_root(callback)
            return

        # Check for subcategories
        subcategories = await db.get_categories(parent_id=cat_id)
        current_category = await db.get_category_by_id(cat_id)
        
        if not current_category:
            await callback.answer("Kategoriya topilmadi", show_alert=True)
            return

        title = current_category['title']
        parent_id = current_category['parent']

        if subcategories:
            # Show subcategories
            # Back button -> Parent of current category
            keyboard = get_categories_keyboard(subcategories, parent_id=parent_id)
            await edit_or_answer(callback, f"📂 <b>{title}</b>", keyboard)
        else:
            # Show products
            # We fetch 6 items to determine if 'has_more' (assuming page size 5 like in search)
            products = await product_service.get_products_by_category(cat_id, limit=6)
            
            if products:
                has_more = len(products) > 5
                display_products = products[:5]
                
                # Note: Default get_products_list_keyboard does not support category-specific pagination yet.
                # Buttons "Next" will trigger 'page:1' which needs a handler.
                # For now, we display the first page.
                keyboard = get_products_list_keyboard(
                    display_products, 
                    page=0, 
                    has_more=has_more,
                    callback_prefix=f"category_page:{cat_id}"
                )
                
                await edit_or_answer(callback, f"📦 <b>{title}</b> - Mahsulotlar", keyboard)
            else:
                await callback.answer("Bu kategoriyada mahsulotlar topilmadi", show_alert=True)
                
    except Exception as e:
        logger.error(f"Error in category view: {e}")
        await callback.answer("Xatolik", show_alert=True)


@router.callback_query(F.data.startswith("category_page:"))
async def callback_category_page(callback: CallbackQuery):
    """Handle category pagination."""
    try:
        parts = callback.data.split(":")
        cat_id = int(parts[1])
        page = int(parts[2])
        
        offset = page * 5
        limit = 6  # 5 to show + 1 to check 'has_more'
        
        products = await product_service.get_products_by_category(cat_id, limit=limit, offset=offset)
        
        if not products:
            await callback.answer("Boshqa mahsulot yo'q", show_alert=True)
            return

        has_more = len(products) > 5
        display_products = products[:5]
        
        current_category = await db.get_category_by_id(cat_id)
        title = current_category['title'] if current_category else "Mahsulotlar"
        
        keyboard = get_products_list_keyboard(
            display_products, 
            page=page, 
            has_more=has_more,
            callback_prefix=f"category_page:{cat_id}"
        )
        
        await edit_or_answer(callback, f"📦 <b>{title}</b> - Mahsulotlar (Sahifa: {page+1})", keyboard)
            
    except Exception as e:
        logger.error(f"Error in category pagination: {e}")
        await callback.answer("Xatolik", show_alert=True)
