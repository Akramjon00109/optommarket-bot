
import asyncio
from bot.services.database import db
from bot.config import settings
from bot.services.product_service import product_service

async def main():
    try:
        await db.connect()
        products = await product_service.search_products('CN55', limit=1)
        if products:
            product = products[0]
            print(f"ID: {product['id']}")
            print(f"Title: {product['title']}")
            print(f"Link: https://t.me/{settings.bot_username}?start=product_{product['id']}")
        else:
            print("Product not found")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
