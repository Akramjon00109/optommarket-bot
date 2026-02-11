"""
Channel Service - Kanalga mahsulot chiqarish
"""

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger
from bot.config import settings
from bot.services.product_service import product_service

class ChannelService:
    """Service for posting to Telegram channel."""
    
    def __init__(self):
        self.bot: Bot = None
        
    def set_bot(self, bot: Bot):
        """Set bot instance."""
        self.bot = bot
        
    async def post_product(self, product_id: int) -> bool:
        """
        Post a product to the channel.
        
        Args:
            product_id: ID of the product to post.
            
        Returns:
            True if posted successfully, False otherwise.
        """
        if not self.bot:
            logger.error("Bot instance not set in ChannelService")
            return False
            
        try:
            # 1. Get product details
            from bot.services.database import db
            product = await db.get_product_by_id(product_id)
            
            if not product:
                logger.warning(f"Product {product_id} not found")
                return False
                
            # 2. Enrich product data
            product['full_url'] = await product_service.get_product_url(product)
            product['image_full_url'] = product_service.get_product_image_url(product)
            product['formatted_price'] = product_service.format_price(product.get('price', 0))
            
            # 3. Format message
            text = f"🆕 <b>Yangi mahsulot!</b>\n\n"
            text += f"🏷 <b>{product['title']}</b>\n\n"
            
            if product.get('short_description'):
                # Clean HTML tags if needed, simple implementation for now
                desc = product['short_description'].replace('<p>', '').replace('</p>', '').strip()
                if len(desc) > 100:
                    desc = desc[:100] + "..."
                text += f"ℹ️ {desc}\n\n"
            
            text += f"💰 Narxi: <b>{product['formatted_price']}</b> so'm"
            
            if product.get('old_price') and float(product.get('old_price', 0) or 0) > 0:
                old_price = product_service.format_price(product['old_price'])
                text += f"\n🏷 Eski narxi: <s>{old_price}</s> so'm"
                
            text += f"\n\n📦 <a href='{product['full_url']}'>Batafsil ko'rish va buyurtma berish</a>"
            
            # 4. Create keyboard
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛒 Sotib olish",
                        url=product['full_url']  # Direct link to product in web app/site
                    )
                ]
            ])
            
            # 5. Send to channel
            if product.get('image_full_url'):
                await self.bot.send_photo(
                    chat_id=settings.channel_id,
                    photo=product['image_full_url'],
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                await self.bot.send_message(
                    chat_id=settings.channel_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                
            logger.info(f"✅ Product {product_id} posted to channel {settings.channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to post product {product_id} to channel: {e}")
            return False

# Singleton instance
channel_service = ChannelService()
