"""
Product Service
Mahsulotlar bilan ishlash uchun biznes logikasi.
"""

from typing import Optional, List, Dict, Any
from loguru import logger

from bot.services.database import db
from bot.services.ai_service import ai_service
from bot.config import settings


class ProductService:
    """Product business logic service."""
    
    @staticmethod
    def format_price(price) -> str:
        """Format price with spaces as thousand separator."""
        try:
            price_float = float(price) if price else 0
            return f"{price_float:,.0f}".replace(",", " ")
        except (ValueError, TypeError):
            return "0"
    
    async def get_product_url(self, product: Dict[str, Any]) -> str:
        """Get full product URL for Moguta CMS with category path."""
        base_url = settings.moguta_url.rstrip('/')
        product_url = product.get('url', '')
        category_id = product.get('category_id')
        
        if product_url and category_id:
            # Build full path: base/category-path/product-slug
            category_path = await db.get_category_path(category_id)
            if category_path and f"{category_path}/" not in product_url:
                return f"{base_url}/{category_path}/{product_url}"
            return f"{base_url}/{product_url}"
        
        # Fallback to direct URL or ID
        if product_url:
            return f"{base_url}/{product_url}"
        return f"{base_url}/product/{product['id']}"
    
    @staticmethod
    def get_product_image_url(product: Dict[str, Any]) -> Optional[str]:
        """Get full image URL for Moguta CMS."""
        image = product.get('image_url', '')
        if not image:
            return None
        
        base_url = settings.moguta_url.rstrip('/')
        
        # If already a full URL, return as is
        if image.startswith('http'):
            return image
        
        product_id = product.get('id')
        
        # Moguta CMS structure: /uploads/product/[DIR]/[ID]/[FILENAME]
        # DIR is based on ID range: 000 for 0-999, 001 for 1000-1999, etc.
        if product_id:
            directory = str(product_id // 1000).zfill(3)
            return f"{base_url}/uploads/product/{directory}/{product_id}/{image}"
        
        # Fallback to simple path
        return f"{base_url}/uploads/{image}"
    
    async def search_products(
        self,
        query: str = None,
        category_id: int = None,
        min_price: float = None,
        max_price: float = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search products with optional filters.
        """
        products = await db.get_products(
            search_query=query,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            limit=limit,
            offset=offset
        )
        
        # Enrich products with URLs
        for product in products:
            product['full_url'] = await self.get_product_url(product)
            product['image_full_url'] = self.get_product_image_url(product)
            product['formatted_price'] = self.format_price(product['price'])
        
        return products
    
    async def get_products_by_category(
        self,
        category_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get products by category ID."""
        return await self.search_products(category_id=category_id, limit=limit, offset=offset)
    
    async def ai_search(self, user_message: str) -> tuple[List[Dict], bool]:
        """
        AI-powered natural language search.
        
        Returns:
            Tuple of (products, is_product_search)
        """
        # Extract search parameters from natural language
        params = await ai_service.extract_search_params(user_message)
        
        is_product_search = params.get('is_product_search', False)
        
        if not is_product_search:
            return [], False
        
        # Search products with extracted parameters
        query = params.get('search_query')
        translated = params.get('translated_keywords')
        
        products = await self.search_products(
            query=query,
            min_price=params.get('min_price'),
            max_price=params.get('max_price'),
            limit=5
        )
        
        # If translated keyword exists and is different, search again (Rus tilida)
        if translated and query and translated.lower() != query.lower():
            more_products = await self.search_products(
                query=translated,
                min_price=params.get('min_price'),
                max_price=params.get('max_price'),
                limit=5
            )
            
            # Merge results (avoid duplicates by ID)
            existing_ids = {p['id'] for p in products}
            for p in more_products:
                if p['id'] not in existing_ids:
                    products.append(p)
        
        return products, True
    
    async def get_product_details(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed product information."""
        product = await db.get_product_by_id(product_id)
        
        if product:
            product['full_url'] = await self.get_product_url(product)
            product['image_full_url'] = self.get_product_image_url(product)
            product['formatted_price'] = self.format_price(product['price'])
            
            if product.get('old_price'):
                product['formatted_old_price'] = self.format_price(product['old_price'])
        
        return product
    
    async def get_categories_tree(self) -> List[Dict[str, Any]]:
        """Get categories as a tree structure."""
        all_categories = await db.get_all_categories()
        
        # Build tree
        categories_map = {c['id']: {**c, 'children': []} for c in all_categories}
        root_categories = []
        
        for cat in all_categories:
            if cat['parent'] == 0:
                root_categories.append(categories_map[cat['id']])
            else:
                parent = categories_map.get(cat['parent'])
                if parent:
                    parent['children'].append(categories_map[cat['id']])
        
        return root_categories
    
    async def format_product_card(self, product: Dict[str, Any]) -> str:
        """Format product for Telegram message."""
        stock_emoji = "✅" if product.get('stock', 0) > 0 else "❌"
        stock_text = "Mavjud" if product.get('stock', 0) > 0 else "Tugagan"
        
        # Get category breadcrumbs
        category_id = product.get('category_id')
        breadcrumbs = await db.get_category_breadcrumbs(category_id) if category_id else "Boshqa"
        
        text = f"""
🏷 <b>{product['title']}</b>

💰 Narxi: <b>{product['formatted_price']} so'm</b>
{f"🏷 Eski narx: <s>{product['formatted_old_price']} so'm</s>" if product.get('formatted_old_price') else ""}
📦 Holati: {stock_emoji} {stock_text}
📁 Kategoriya: {breadcrumbs}
"""
        
        if product.get('short_description'):
            # Truncate description
            desc = product['short_description'][:200]
            if len(product['short_description']) > 200:
                desc += "..."
            text += f"\n📝 {desc}"
        
        return text.strip()


# Singleton instance
product_service = ProductService()
