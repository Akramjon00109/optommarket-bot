"""
Broadcast Handler - Admin xabarlarni barcha foydalanuvchilarga yuborish
"""

import json
import csv
import os
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from bot.keyboards.inline import get_confirm_keyboard, get_back_keyboard
from bot.config import settings
from bot.services.user_service import user_service


router = Router(name="broadcast")

# Admin user IDs (from .env or hardcoded)
ADMIN_IDS = [6224477868]  # Add your admin Telegram IDs here

# Users storage file
USERS_FILE = Path(__file__).parent.parent.parent / "data" / "users.json"


class BroadcastStates(StatesGroup):
    """Broadcast FSM states."""
    waiting_for_message = State()
    confirm_broadcast = State()


def load_users() -> set:
    """Load user IDs from file."""
    if USERS_FILE.exists():
        with open(USERS_FILE, 'r') as f:
            data = json.load(f)
            return set(data.get('users', []))
    return set()


def save_users(users: set):
    """Save user IDs to file."""
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        json.dump({'users': list(users)}, f)


def add_user(user_id: int):
    """Add user to the list."""
    users = load_users()
    users.add(user_id)
    save_users(users)



def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in settings.admin_id_list


# ==========================================
# BROADCAST COMMANDS (Admin only)
# ==========================================

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    """Start broadcast process (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun.")
        return
    
    users = load_users()
    user_count = len(users)
    
    await state.set_state(BroadcastStates.waiting_for_message)
    
    await message.answer(
        f"📢 <b>Broadcast xabar yuborish</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{user_count}</b> ta\n\n"
        f"Yubormoqchi bo'lgan xabaringizni yozing.\n"
        f"(Rasm, video, matn yoki boshqa har qanday xabar)",
        parse_mode="HTML"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Show bot statistics (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun.")
        return
    
    users = load_users()
    
    await message.answer(
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{len(users)}</b> ta\n"
        f"🤖 Bot: @optommarketai_bot",
        parse_mode="HTML"
    )


@router.message(Command("get_logs"))
async def cmd_get_logs(message: Message):
    """Send today's log file to admin (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun.")
        return
    
    from datetime import datetime
    import glob
    
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    
    # Find log files
    log_files = list(logs_dir.glob("bot_*.log"))
    
    if not log_files:
        await message.answer("📂 Log fayllar topilmadi.")
        return
    
    # Get most recent log file
    latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
    
    try:
        await message.answer_document(
            FSInputFile(latest_log),
            caption=f"📋 Log fayli: {latest_log.name}\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")


@router.message(Command("newproducts"))
async def cmd_new_products(message: Message):
    """Manually send new products notification (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun.")
        return
    
    from bot.services.scheduler import scheduler_service
    
    await message.answer("🔄 Yangi mahsulotlar yuborilmoqda...")
    
    try:
        await scheduler_service.send_new_products_now()
        await message.answer("✅ Yangi mahsulotlar haqida xabar yuborildi!")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")


@router.message(Command("post"))
async def cmd_post(message: Message):
    """Manually post product to channel (admin only).
    Usage: /post 123
    """
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun.")
        return
        
    args = message.text.split()
    if len(args) != 2:
        await message.answer("⚠️ Ko'rsatma: /post <product_id>")
        return
        
    try:
        product_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID raqam bo'lishi kerak.")
        return
        
    from bot.services.channel import channel_service
    channel_service.set_bot(message.bot)
    
    await message.answer(f"🔄 Mahsulot {product_id} kanalga chiqarilmoqda...")
    
    if await channel_service.post_product(product_id):
        await message.answer(f"✅ Mahsulot {product_id} muvaffaqiyatli chiqarildi!")
    else:
        await message.answer(f"❌ Xatolik yuz berdi. ID to'g'riligini tekshiring.")


@router.message(BroadcastStates.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Process the broadcast message content."""
    # Store message details
    await state.update_data(
        broadcast_message_id=message.message_id,
        broadcast_chat_id=message.chat.id,
        broadcast_content_type=message.content_type
    )
    
    users = load_users()
    
    await state.set_state(BroadcastStates.confirm_broadcast)
    
    await message.answer(
        f"📢 Xabaringiz qabul qilindi!\n\n"
        f"Bu xabar <b>{len(users)}</b> ta foydalanuvchiga yuboriladi.\n\n"
        f"Tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=get_confirm_keyboard("broadcast", 0)
    )


@router.callback_query(F.data == "confirm:broadcast:0")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Confirm and send broadcast."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q", show_alert=True)
        return
    
    data = await state.get_data()
    await state.clear()
    
    message_id = data.get('broadcast_message_id')
    chat_id = data.get('broadcast_chat_id')
    
    if not message_id or not chat_id:
        await callback.message.edit_text("❌ Xato: Xabar topilmadi")
        return
    
    users = load_users()
    
    await callback.message.edit_text(
        f"📤 Xabar yuborilmoqda... 0/{len(users)}",
        parse_mode="HTML"
    )
    
    success_count = 0
    fail_count = 0
    
    for i, user_id in enumerate(users):
        try:
            await callback.bot.copy_message(
                chat_id=user_id,
                from_chat_id=chat_id,
                message_id=message_id
            )
            success_count += 1
        except Exception as e:
            fail_count += 1
            logger.warning(f"Failed to send to {user_id}: {e}")
        
        # Update progress every 10 users
        if (i + 1) % 10 == 0:
            try:
                await callback.message.edit_text(
                    f"📤 Xabar yuborilmoqda... {i + 1}/{len(users)}",
                    parse_mode="HTML"
                )
            except:
                pass
    
    await callback.message.edit_text(
        f"✅ <b>Broadcast yakunlandi!</b>\n\n"
        f"📨 Yuborildi: <b>{success_count}</b>\n"
        f"❌ Xato: <b>{fail_count}</b>\n"
        f"👥 Jami: <b>{len(users)}</b>",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )
    
    logger.info(f"Broadcast completed: {success_count} success, {fail_count} failed")
    await callback.answer("✅ Broadcast yakunlandi!")


@router.callback_query(F.data == "cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Cancel broadcast."""
    current_state = await state.get_state()
    if current_state and current_state.startswith("BroadcastStates"):
        await state.clear()
        await callback.message.edit_text(
            "❌ Broadcast bekor qilindi.",
            reply_markup=get_back_keyboard()
        )
    await callback.answer()


@router.message(Command("kontakt"))
async def cmd_kontakt(message: Message):
    """Barcha kontaktlarni yuborish (Admin only)."""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return

    users = await user_service.get_all_users()
    
    if not users:
        await message.answer("Foydalanuvchilar topilmadi.")
        return

    # Create CSV file with UTF-8 BOM for Excel
    file_path = "users_export.csv"
    with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["ID", "Ism", "Telefon", "Username", "Sana"])
        
        for uid, data in users.items():
            writer.writerow([
                uid,
                data.get("name", ""),
                data.get("phone", ""),
                data.get("username", "") or "",
                data.get("registered_at", "")
            ])
            
    # Send file
    await message.answer_document(
        FSInputFile(file_path),
        caption=f"📊 Jami foydalanuvchilar: {len(users)} ta"
    )
    
    # Clean up
    os.remove(file_path)
