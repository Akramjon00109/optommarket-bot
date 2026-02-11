"""
Admin Handler - Adminlar uchun maxsus buyruqlar
"""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from loguru import logger

from bot.config import settings
from bot.services.facebook_catalog import fb_catalog

router = Router(name="admin")

def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in settings.admin_id_list


@router.message(Command("sync_catalog"))
async def cmd_sync_catalog(message: Message):
    """Sync products to Facebook Catalog manually."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun.")
        return
    
    status_msg = await message.answer("🔄 Facebook Catalog bilan sinxronizatsiya boshlandi...")
    
    try:
        # Check service status first (get info)
        info = await fb_catalog.get_catalog_info()
        if "error" in info:
            await status_msg.edit_text(f"❌ Xatolik: API ulanishda muammo bor.\n\n{info['error']}")
            return

        # Start sync
        result = await fb_catalog.sync_products()
        
        if result["status"] == "success":
            text = (
                f"✅ <b>Sinxronizatsiya yakunlandi!</b>\n\n"
                f"📊 Jami mahsulotlar: {result['total']}\n"
                f"📤 Yuklandi/Yangilandi: {result['synced']}\n"
                f"❌ Xatolar: {result['errors']}"
            )
            
            if result["error_messages"]:
                # Show first 3 errors if any
                errors = "\n".join(result["error_messages"][:3])
                text += f"\n\n⚠️ Xatoliklar:\n{errors}"
                if len(result["error_messages"]) > 3:
                    text += f"\n...va yana {len(result['error_messages']) - 3} ta"
            
            await status_msg.edit_text(text, parse_mode="HTML")
            
        else:
            error_msg = result.get('error_messages', ['Noma\'lum xato'])[0]
            await status_msg.edit_text(
                f"❌ Sinxronizatsiya amalga oshmadi.\n\nSabab: {error_msg}"
            )
            
    except Exception as e:
        logger.error(f"Sync command error: {e}")
        await status_msg.edit_text(f"❌ Kutilmagan xatolik yuz berdi: {e}")
