"""
Inline Keyboards for Telegram Bot
"""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any

from bot.config import settings


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Asosiy menyu klaviaturasi."""
    builder = InlineKeyboardBuilder()
    
    # 1. Shop (Web App)
    builder.row(
        InlineKeyboardButton(
            text="🛒 Do'kon (Sayt)",
            web_app=WebAppInfo(url=settings.moguta_url)
        )
    )
    
    # 2. Search & Categories
    builder.row(
        InlineKeyboardButton(text="🔍 Qidirish", callback_data="search_products"),
        InlineKeyboardButton(text="📂 Kategoriyalar", callback_data="categories")
    )
    
    # 3. Orders & Contact
    builder.row(
        InlineKeyboardButton(text="📦 Buyurtmalarim", callback_data="check_order"),
        InlineKeyboardButton(text="📞 Aloqa", callback_data="contact")
    )
    
    # 4. AI & Help
    builder.row(
        InlineKeyboardButton(text="🤖 AI Yordamchi", callback_data="ai_help"),
        InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help")
    )
    
    # 5. Channel
    builder.row(
        InlineKeyboardButton(text="📢 Kanalimiz", url="https://t.me/optommarket7")
    )
    
    return builder.as_markup()


def get_product_keyboard(product: Dict[str, Any]) -> InlineKeyboardMarkup:
    """Mahsulot uchun klaviatura."""
    builder = InlineKeyboardBuilder()
    
    # Product URL logic (ensure valid URL)
    moguta_url = settings.moguta_url.rstrip('/')
    product_url = product.get('url', '')
    
    if not product_url.startswith('http'):
        # If product url is relative like 'category/product-slug'
        if not product_url.startswith('/'):
            product_url = '/' + product_url
        full_url = f"{moguta_url}{product_url}"
    else:
        full_url = product_url
        
    # Buy button (Direct Website Link)
    builder.row(
        InlineKeyboardButton(
            text="🛒 Sotib olish (Saytda) 🌐",
            url=full_url
        )
    )
    
    # First row: Share and Categories
    builder.row(
        InlineKeyboardButton(
            text="📤 Ulashish",
            switch_inline_query=product.get('title', '')[:30]
        ),
        InlineKeyboardButton(text="📂 Kategoriyalar", callback_data="categories")
    )
    
    # Second row: Back and Home
    category_id = product.get('category_id')
    back_callback = f"category:{category_id}" if category_id else "main_menu"
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data=back_callback),
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")
    )
    
    return builder.as_markup()



def get_products_list_keyboard(
    products: List[Dict[str, Any]],
    page: int = 0,
    has_more: bool = False,
    callback_prefix: str = "page"
) -> InlineKeyboardMarkup:
    """Mahsulotlar ro'yxati uchun klaviatura."""
    builder = InlineKeyboardBuilder()
    
    # Product buttons (2 per row)
    for i in range(0, len(products), 2):
        row_buttons = []
        for product in products[i:i+2]:
            title = product['title'][:25] + "..." if len(product['title']) > 25 else product['title']
            row_buttons.append(
                InlineKeyboardButton(
                    text=f"📦 {title}",
                    callback_data=f"product:{product['id']}"
                )
            )
        builder.row(*row_buttons)
    
    # Pagination
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"{callback_prefix}:{page-1}")
        )
    if has_more:
        nav_buttons.append(
            InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"{callback_prefix}:{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")
    )
    
    return builder.as_markup()


def get_categories_keyboard(
    categories: List[Dict[str, Any]],
    parent_id: int = 0
) -> InlineKeyboardMarkup:
    """Kategoriyalar uchun klaviatura."""
    builder = InlineKeyboardBuilder()
    
    for cat in categories:
        builder.row(
            InlineKeyboardButton(
                text=f"📁 {cat['title']}",
                callback_data=f"category:{cat['id']}"
            )
        )
    
    # Navigation buttons
    if parent_id > 0:
        # Go back to parent category
        builder.row(
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"category:{parent_id}"),
            InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")
        )
    else:
        # At root level - show only main menu
        builder.row(
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data="main_menu"),
            InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")
        )
    
    return builder.as_markup()


def get_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Buyurtma uchun klaviatura."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📋 Buyurtma tarkibi",
            callback_data=f"order_items:{order_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")
    )
    
    return builder.as_markup()


def get_back_keyboard(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """Orqaga qaytish tugmasi."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data=callback_data)
    )
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Bekor qilish tugmasi."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
    )
    return builder.as_markup()


def get_confirm_keyboard(action: str, item_id: int) -> InlineKeyboardMarkup:
    """Tasdiqlash klaviaturasi."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Ha",
            callback_data=f"confirm:{action}:{item_id}"
        ),
        InlineKeyboardButton(
            text="❌ Yo'q",
            callback_data="cancel"
        )
    )
    return builder.as_markup()
