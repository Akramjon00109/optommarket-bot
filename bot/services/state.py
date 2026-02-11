"""
StateService - Bot holatini boshqarish (Database orqali)
Render kabi platformalarda fayl tizimi vaqtincha bo'lgani uchun
holatni (masalan, last_posted_id) bazada saqlash kerak.
"""

from typing import Dict, Any, Optional
from loguru import logger

class StateService:
    """Database-backed state manager."""
    
    async def get_last_posted_id(self) -> int:
        """Get ID of the last product posted to channel from mg_setting."""
        # Import here to avoid circular dependency and use the connected instance
        from bot.services.database import db
        
        query = "SELECT value FROM mg_setting WHERE `option` = 'bot_last_posted_id'"
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute(query)
                result = await cursor.fetchone()
                logger.debug(f"State Service Get Result: {result}")
                if result and result['value']:
                    return int(result['value'])
                return 0
        except Exception as e:
            logger.error(f"Failed to get last posted ID: {e}")
            return 0
        
    async def set_last_posted_id(self, product_id: int):
        """Update last posted product ID in mg_setting."""
        from bot.services.database import db
        
        # INSERT ... ON DUPLICATE KEY UPDATE logic for MySQL
        query = """
            INSERT INTO mg_setting (`option`, `value`, `active`, `name`)
            VALUES ('bot_last_posted_id', %s, 'N', 'BOT_LAST_POSTED_ID')
            ON DUPLICATE KEY UPDATE `value` = %s
        """
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute(query, (str(product_id), str(product_id)))
                # Connection is returned to pool, and with autocommit=True, it should be saved.
                # db.pool usage was wrong.
        except Exception as e:
            logger.error(f"Failed to set last posted ID: {e}")

# Singleton instance
state_service = StateService()
