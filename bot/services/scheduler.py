"""
Scheduler Service - Avtomatik kunlik xabarlar
Har kuni yangi mahsulotlarni foydalanuvchilarga yuborish.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from bot.services.database import db
from bot.services.product_service import product_service
from bot.services.channel import channel_service
from bot.services.state import state_service


class SchedulerService:
    """Daily notifications scheduler."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
        self.bot = None
        self.last_check_time = None
    
    def set_bot(self, bot):
        """Set bot instance for sending messages."""
        self.bot = bot
        # Also set bot for channel service
        channel_service.set_bot(bot)
    
    def start(self):
        """Start the scheduler."""
        # Run daily at 10:00 AM Tashkent time
        self.scheduler.add_job(
            self.send_daily_new_products,
            CronTrigger(hour=10, minute=0),
            id="daily_new_products",
            replace_existing=True
        )
        
        # Run every 30 minutes to check for new products for channel
        self.scheduler.add_job(
            self.check_new_products_for_channel,
            CronTrigger(minute='*/30'),
            id="channel_new_products",
            replace_existing=True
        )
        
        # Sync products to Facebook Catalog daily at 6:00 AM
        self.scheduler.add_job(
            self.sync_facebook_catalog,
            CronTrigger(hour=6, minute=0),
            id="facebook_catalog_sync",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("📅 Scheduler started - daily notifications at 10:00 AM, FB sync at 6:00 AM")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    async def get_new_products(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recently added products (by highest ID - newest products have higher IDs)."""
        # Since Moguta CMS doesn't have add_date, we get the 10 most recent products by ID
        query = """
            SELECT 
                p.id,
                p.title,
                p.price,
                p.old_price,
                p.image_url,
                p.url,
                p.count as stock,
                p.cat_id as category_id,
                c.title as category_name
            FROM mg_product p
            LEFT JOIN mg_category c ON p.cat_id = c.id
            WHERE p.activity = 1
            ORDER BY p.id DESC
            LIMIT 10
        """
        
        async with db.get_cursor() as cursor:
            await cursor.execute(query)
            products = await cursor.fetchall()
            
            result = []
            for p in products:
                product = dict(p)
                product['full_url'] = await product_service.get_product_url(product)
                product['image_full_url'] = product_service.get_product_image_url(product)
                product['formatted_price'] = product_service.format_price(product.get('price', 0))
                result.append(product)
            
            return result
    
    async def send_daily_new_products(self):
        """Send daily new products notification to all users."""
        if not self.bot:
            logger.error("Bot not set for scheduler")
            return
        
        logger.info("🔔 Running daily new products notification...")
        
        # Get new products
        new_products = await self.get_new_products()
        
        if not new_products:
            logger.info("No products found")
            return
        
        # Load users
        users = load_users()
        if not users:
            logger.info("No users to notify")
            return
        
        success_count = 0
        fail_count = 0
        
        # Import here to avoid circular imports
        from bot.keyboards.inline import get_product_keyboard
        
        for user_id in users:
            try:
                # Send header message
                await self.bot.send_message(
                    chat_id=user_id,
                    text="🆕 <b>Eng so'nggi mahsulotlar!</b>\n\nBizning yangi mahsulotlarimiz bilan tanishing:",
                    parse_mode="HTML"
                )
                
                # Send each product as a card
                for product in new_products[:5]:  # Max 5 products
                    text = f"""🏷 <b>{product['title']}</b>

💰 Narxi: <b>{product['formatted_price']}</b> so'm"""
                    
                    # Add old price if exists
                    if product.get('old_price') and float(product.get('old_price', 0) or 0) > 0:
                        old_price = product_service.format_price(product['old_price'])
                        text += f"\n🏷 Eski narxi: <s>{old_price}</s> so'm"
                    
                    # Add stock status
                    stock = product.get('stock', 0)
                    if stock and int(stock) > 0:
                        text += f"\n📦 Holati: ✅ Mavjud"
                    else:
                        text += f"\n📦 Holati: ❌ Tugagan"
                    
                    # Add category
                    if product.get('category_name'):
                        text += f"\n📁 Kategoriya: {product['category_name']}"
                    
                    # Try to send with image
                    if product.get('image_full_url'):
                        try:
                            await self.bot.send_photo(
                                chat_id=user_id,
                                photo=product['image_full_url'],
                                caption=text,
                                parse_mode="HTML",
                                reply_markup=get_product_keyboard(product)
                            )
                        except:
                            await self.bot.send_message(
                                chat_id=user_id,
                                text=text,
                                parse_mode="HTML",
                                reply_markup=get_product_keyboard(product)
                            )
                    else:
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=text,
                            parse_mode="HTML",
                            reply_markup=get_product_keyboard(product)
                        )
                    
                    await asyncio.sleep(0.1)  # Small delay between messages
                
                success_count += 1
                await asyncio.sleep(0.5)  # Delay between users
                
            except Exception as e:
                fail_count += 1
                logger.warning(f"Failed to send to {user_id}: {e}")
        
        logger.info(f"✅ Daily notification sent: {success_count} success, {fail_count} failed")
    
    async def send_new_products_now(self):
        """Manually trigger new products notification (for testing)."""
        await self.send_daily_new_products()

    async def check_new_products_for_channel(self):
        """Check for new products and post to channel."""
        logger.info("running channel update")
        
        if not self.bot:
            logger.error("Bot not set for channel update")
            return

        # 1. Get last posted ID (async)
        last_id = await state_service.get_last_posted_id()
        
        # 2. Get max ID from DB
        query = "SELECT MAX(id) as max_id FROM mg_product WHERE activity = 1"
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute(query)
                result = await cursor.fetchone()
                max_id = result['max_id'] if result else 0
        except Exception as e:
            logger.error(f"Failed to get max product ID: {e}")
            return

        # If we have no state (first run), just save current max_id and exit
        # to avoid posting 1000s of old products
        if last_id == 0:
            await state_service.set_last_posted_id(max_id)
            logger.info(f"Initialized last posted ID to {max_id}")
            return
            
        if max_id <= last_id:
            logger.info("No new products for channel")
            return
            
        # 3. Get new products
        # Get products with ID > last_id
        # Limit to 5 products at a time to avoid spamming
        query_new = """
            SELECT id FROM mg_product 
            WHERE id > %s AND activity = 1 
            ORDER BY id ASC 
            LIMIT 5
        """
        
        try:
            posted_count = 0
            async with db.get_cursor() as cursor:
                await cursor.execute(query_new, (last_id,))
                products = await cursor.fetchall()
                
            for p in products:
                prod_id = p['id']
                if await channel_service.post_product(prod_id):
                    await state_service.set_last_posted_id(prod_id)
                    posted_count += 1
                    await asyncio.sleep(3)  # Delay between posts
            
            if posted_count > 0:
                logger.info(f"Posted {posted_count} new products to channel")
                    
        except Exception as e:
            logger.error(f"Failed to process channel posts: {e}")

    async def sync_facebook_catalog(self):
        """Sync all products to Facebook Catalog."""
        logger.info("📦 Starting Facebook Catalog sync...")
        
        try:
            from bot.services.facebook_catalog import fb_catalog
            result = await fb_catalog.sync_products()
            
            if result.get("status") == "success":
                logger.info(f"✅ Facebook Catalog synced: {result.get('synced', 0)}/{result.get('total', 0)} products")
            elif result.get("status") == "skipped":
                logger.info(f"⏭️ Facebook Catalog sync skipped: {result.get('reason', 'unknown')}")
            else:
                logger.error(f"❌ Facebook Catalog sync failed: {result.get('error_messages', [])}")
                
        except Exception as e:
            logger.error(f"❌ Facebook Catalog sync error: {e}")


# Singleton instance
scheduler_service = SchedulerService()
