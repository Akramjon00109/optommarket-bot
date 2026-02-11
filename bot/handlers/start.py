"""
Start Handler - /start va /help komandalar
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.product_service import product_service
from bot.keyboards.inline import get_main_menu_keyboard, get_back_keyboard, get_categories_keyboard, get_products_list_keyboard, get_product_keyboard
from bot.handlers.broadcast import add_user


router = Router(name="start")


class RegistrationStates(StatesGroup):
    waiting_for_contact = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject = None):
    """Handle /start command."""
    user = message.from_user
    logger.info(f"User {user.id} ({user.full_name}) started bot")
    
    # Save user for broadcast (legacy)
    add_user(user.id)
    ai_service.clear_user_context(user.id)

    # Check for Deep Link payload
    pending_product_id = None
    if command and command.args:
        args = command.args
        if args.startswith("product_"):
            try:
                pending_product_id = int(args.split("_")[1])
            except ValueError:
                pass

    # Check registration
    if not await user_service.exists(user.id):
        await state.set_state(RegistrationStates.waiting_for_contact)
        
        # Save pending product ID to state
        if pending_product_id:
            await state.update_data(pending_product_id=pending_product_id)
        
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer(
            f"Assalomu alaykum, {user.first_name}!\n\n"
            "Botdan to'liq foydalanish uchun telefon raqamingizni yuborishingiz kerak.",
            reply_markup=kb
        )
        return

    # If registered and has deep link, show product
    if pending_product_id:
        try:
            product = await product_service.get_product_details(pending_product_id)
            if product:
                # Show product card directly
                text = await product_service.format_product_card(product)
                
                if product.get('image_full_url'):
                    await message.answer_photo(
                        photo=product['image_full_url'],
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=get_product_keyboard(product)
                    )
                else:
                    await message.answer(
                        text,
                        parse_mode="HTML",
                        reply_markup=get_product_keyboard(product)
                    )
                return
        except Exception as e:
            logger.error(f"Deep link error: {e}")

    # Main Menu
    welcome_text = f"""
Assalomu alaykum, <b>{user.first_name}</b>! 👋

<b>OptomMarket</b> botiga xush kelibsiz!

🤖 Men sizga mahsulotlarni topishda, narxlarni bilishda va buyurtmalar holati haqida ma'lumot berishda yordam beraman.

<b>Nima qila olaman:</b>
• 🔍 Mahsulotlarni qidirish
• 📁 Kategoriyalar bo'yicha ko'rish
• 📦 Buyurtma holatini tekshirish
• 💬 Savollaringizga javob berish

Pastdagi menyudan foydalaning yoki menga to'g'ridan-to'g'ri yozing! 👇
"""
    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )


@router.message(RegistrationStates.waiting_for_contact)
async def process_contact(message: Message, state: FSMContext):
    """Process contact or phone text."""
    user = message.from_user
    
    # Get phone
    phone = ""
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text
        # Oddiy validatsiya
        if not phone or len(phone) < 9:
            await message.answer("Iltimos, to'g'ri telefon raqam kiriting yoki tugmani bosing.")
            return

    # Save user
    await user_service.save_user(user.id, {
        "name": user.full_name,
        "phone": phone,
        "username": user.username,
        "registered_at": str(message.date)
    })
    
    # Check for pending deep link
    data = await state.get_data()
    pending_product_id = data.get('pending_product_id')
    
    await state.clear()
    
    # Remove reply keyboard
    msg = await message.answer("✅ Rahmat! Ro'yxatdan o'tdingiz.", reply_markup=ReplyKeyboardRemove())
    
    # Process pending deep link if exists
    if pending_product_id:
        try:
            product = await product_service.get_product_details(pending_product_id)
            if product:
                text = await product_service.format_product_card(product)
                if product.get('image_full_url'):
                    await message.answer_photo(
                        photo=product['image_full_url'],
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=get_product_keyboard(product)
                    )
                else:
                    await message.answer(
                        text,
                        parse_mode="HTML",
                        reply_markup=get_product_keyboard(product)
                    )
                return
        except Exception as e:
            logger.error(f"Pending product error: {e}")
            # Fallback to main menu

    # Show main menu
    welcome_text = f"""
<b>OptomMarket</b> botiga xush kelibsiz, <b>{user.first_name}</b>! 🎉

Endi bemalol foydalanishingiz mumkin.
"""
    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    help_text = """
<b>📚 Yordam</b>

<b>Asosiy buyruqlar:</b>
/start - Botni qayta ishga tushirish
/help - Ushbu yordam xabari
/search - Mahsulot qidirish
/order - Buyurtma holatini tekshirish

<b>Qidiruv misollari:</b>
• "Ko'ylak" - oddiy qidiruv
• "100 mingdan arzon futbolkalar" - narx bo'yicha
• "Ayollar kiyimlari" - kategoriya bo'yicha

<b>Buyurtma tekshirish:</b>
Buyurtma raqami yoki telefon raqamingizni yuboring.

<b>Muammo bo'lsa:</b>
Operatorimiz bilan bog'laning: /contact
"""
    
    await message.answer(
        help_text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Handle help callback."""
    help_text = """
<b>📚 Yordam</b>

<b>Asosiy buyruqlar:</b>
/start - Botni qayta ishga tushirish
/search - Mahsulot qidirish
/order - Buyurtma holatini tekshirish

<b>Qidiruv misollari:</b>
• "Ko'ylak" - oddiy qidiruv
• "100 mingdan arzon futbolkalar" - narx bo'yicha

<b>Muammo bo'lsa:</b>
Operatorimiz bilan bog'laning: @akramjon0011
"""
    
    await callback.message.edit_text(
        help_text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Return to main menu."""
    user = callback.from_user
    
    welcome_text = f"""
<b>OptomMarket</b> 🛒

Xush kelibsiz, {user.first_name}!

Quyidagi menyudan tanlang yoki menga to'g'ridan-to'g'ri yozing:
"""
    
    # Try to edit text, if fails (photo message), delete and send new
    try:
        await callback.message.edit_text(
            welcome_text,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
    except Exception:
        # This is a photo message, delete it and send new text message
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(
            welcome_text,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
    await callback.answer()




@router.callback_query(F.data == "contact")
async def callback_contact(callback: CallbackQuery):
    """Show contact information."""
    contact_text = """
<b>📞 Aloqa ma'lumotlari</b>

📱 Telefon: +998 97 477 12 29
📧 Email: info@optommarket.uz
🌐 Veb-sayt: optommarket.uz

🕐 Ish vaqti: Dushanba - Shanba, 9:00 - 18:00

Telegram: @akramjon0011
"""
    
    await callback.message.edit_text(
        contact_text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "ai_help")
async def callback_ai_help(callback: CallbackQuery, state: FSMContext):
    """Show AI help information."""
    await state.clear()
    text = """
<b>🤖 AI Yordamchi</b>

Men **sun'iy intellekt** asosida ishlayman! 
Menga xohlagan savolingizni berishingiz mumkin.

<b>Masalan:</b>
• <i>Samsung televizor bormi?</i>
• <i>Konditsionerlar narxi qancha?</i>
• <i>Eng arzon changyutgichni topib ber</i>
• <i>Do'kon qayerda joylashgan?</i>

<b>Shunchaki menga xabar yozing 👇</b>
"""
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery):
    """Cancel current action."""
    await callback.message.edit_text(
        "❌ Bekor qilindi.\n\nBosh menyuga qaytish uchun tugmani bosing.",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()
