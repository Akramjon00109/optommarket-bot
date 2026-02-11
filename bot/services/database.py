"""
Database Service for Moguta CMS
MySQL ulanish va Moguta CMS jadvallaridan ma'lumot olish.
"""

import aiomysql
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from loguru import logger

from bot.config import settings


class DatabaseService:
    """Moguta CMS MySQL database service."""
    
    def _fix_text(self, text: Any) -> Any:
        """Fix Mojibake encoding (CP866 -> CP1251)."""
        if isinstance(text, str):
            try:
                # Try to fix only if it looks like garbled CP1251
                return text.encode('cp866').decode('cp1251')
            except:
                return text
        return text
    
    def __init__(self):
        self.pool: Optional[aiomysql.Pool] = None
    
    async def connect(self) -> None:
        """Create database connection pool."""
        try:
            self.pool = await aiomysql.create_pool(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                db=settings.db_name,
                charset='utf8mb4',
                autocommit=True,
                minsize=1,
                maxsize=10,
            )
            logger.info("✅ Database connection pool created")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("Database connection closed")

    async def commit(self) -> None:
        """Commit current transaction (if not autocommit)."""
        # Note: aiomysql pool doesn't share a single connection, so committing on the pool 
        # isn't really a thing unless we're holding a specific connection.
        # But since we use autocommit=True in connect(), we might not need this.
        # However, if we need to force it, we need a way.
        pass
    
    @asynccontextmanager
    async def get_cursor(self):
        """Get database cursor context manager."""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                yield cursor
    
    # ==========================================
    # PRODUCTS (mg_product)
    # ==========================================
    
    async def get_products(
        self,
        search_query: Optional[str] = None,
        category_id: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        in_stock: bool = True,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Mahsulotlarni qidirish va filtrlash.
        
        Args:
            search_query: Qidiruv so'zi (nom yoki tavsifda)
            category_id: Kategoriya ID
            min_price: Minimal narx
            max_price: Maksimal narx
            in_stock: Faqat mavjud mahsulotlar
            limit: Natijalar soni
            offset: Sahifalash uchun offset
        
        Returns:
            Mahsulotlar ro'yxati
        """
        query = """
            SELECT 
                p.id,
                p.title,
                p.price,
                p.old_price,
                p.description,
                p.short_description,
                p.image_url,
                p.count as stock,
                p.cat_id as category_id,
                p.url,
                p.code as sku,
                c.title as category_name
            FROM mg_product p
            LEFT JOIN mg_category c ON p.cat_id = c.id
            WHERE p.activity = 1
        """
        params = []
        
        if search_query:
            # Split query into words for multi-keyword search
            keywords = search_query.split()
            for word in keywords:
                query += " AND (p.title LIKE %s OR p.description LIKE %s OR p.code LIKE %s)"
                search_param = f"%{word}%"
                params.extend([search_param, search_param, search_param])
        
        if category_id:
            query += " AND p.cat_id = %s"
            params.append(category_id)
        
        if min_price is not None:
            query += " AND p.price >= %s"
            params.append(min_price)
        
        if max_price is not None:
            query += " AND p.price <= %s"
            params.append(max_price)
        
        if in_stock:
            query += " AND (p.count > 0 OR p.count = -1)"
        
        query += " ORDER BY p.sort ASC, p.id DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        async with self.get_cursor() as cursor:
            await cursor.execute(query, params)
            products = await cursor.fetchall()
            fixed_products = []
            for p in products:
                d = dict(p)
                for k, v in d.items():
                    d[k] = self._fix_text(v)
                
                # Build full URL if cat_id is present
                if d.get('category_id'):
                    cat_path = await self.get_category_path(d['category_id'])
                    if cat_path and f"{cat_path}/" not in d['url']:
                        d['url'] = f"{cat_path}/{d['url']}"
                        
                fixed_products.append(d)
            return fixed_products
    
    async def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Mahsulotni ID bo'yicha olish."""
        query = """
            SELECT 
                p.id,
                p.title,
                p.price,
                p.old_price,
                p.description,
                p.short_description,
                p.image_url,
                p.count as stock,
                p.cat_id as category_id,
                p.url,
                p.code as sku,
                c.title as category_name
            FROM mg_product p
            LEFT JOIN mg_category c ON p.cat_id = c.id
            WHERE p.id = %s AND p.activity = 1
        """
        async with self.get_cursor() as cursor:
            await cursor.execute(query, (product_id,))
            product = await cursor.fetchone()
            if product:
                d = dict(product)
                for k, v in d.items():
                    d[k] = self._fix_text(v)
                
                # Build full URL if cat_id is present
                if d.get('category_id'):
                    cat_path = await self.get_category_path(d['category_id'])
                    if cat_path and f"{cat_path}/" not in d['url']:
                        d['url'] = f"{cat_path}/{d['url']}"
                        
                return d
            return None
    
    async def get_product_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Mahsulotni URL bo'yicha olish."""
        query = """
            SELECT 
                p.id,
                p.title,
                p.price,
                p.old_price,
                p.description,
                p.short_description,
                p.image_url,
                p.count as stock,
                p.cat_id as category_id,
                p.url,
                p.code as sku,
                c.title as category_name
            FROM mg_product p
            LEFT JOIN mg_category c ON p.cat_id = c.id
            WHERE p.url = %s AND p.activity = 1
        """
        async with self.get_cursor() as cursor:
            await cursor.execute(query, (url,))
            product = await cursor.fetchone()
            if product:
                d = dict(product)
                for k, v in d.items():
                    d[k] = self._fix_text(v)
                
                # Build full URL if cat_id is present
                if d.get('category_id'):
                    cat_path = await self.get_category_path(d['category_id'])
                    if cat_path and f"{cat_path}/" not in d['url']:
                        d['url'] = f"{cat_path}/{d['url']}"
                        
                return d
            return None
    
    async def get_popular_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Eng ko'p sotilgan mahsulotlarni olish."""
        query = """
            SELECT 
                p.id,
                p.title,
                p.price,
                p.image_url,
                p.count as stock,
                p.cat_id as category_id,
                p.url,
                c.title as category_name
            FROM mg_product p
            LEFT JOIN mg_category c ON p.cat_id = c.id
            WHERE p.activity = 1 AND p.count > 0
            ORDER BY p.views DESC, p.sort ASC
            LIMIT %s
        """
        async with self.get_cursor() as cursor:
            await cursor.execute(query, (limit,))
            products = await cursor.fetchall()
            fixed_products = []
            for p in products:
                d = dict(p)
                for k, v in d.items():
                    d[k] = self._fix_text(v)
                
                # Build full URL if category_id is present
                if d.get('category_id'):
                    cat_path = await self.get_category_path(d['category_id'])
                    if cat_path and f"{cat_path}/" not in d['url']:
                        d['url'] = f"{cat_path}/{d['url']}"
                        
                fixed_products.append(d)
            return fixed_products
    
    # ==========================================
    # CATEGORIES (mg_category)
    # ==========================================
    
    async def get_categories(self, parent_id: int = 0) -> List[Dict[str, Any]]:
        """Kategoriyalarni olish."""
        query = """
            SELECT 
                id,
                title,
                parent,
                url,
                image_url,
                sort
            FROM mg_category
            WHERE invisible = 0 AND parent = %s
            ORDER BY sort ASC, title ASC
        """
        async with self.get_cursor() as cursor:
            await cursor.execute(query, (parent_id,))
            categories = await cursor.fetchall()
            return [dict(c) for c in categories]
    
    async def get_all_categories(self) -> List[Dict[str, Any]]:
        """Barcha kategoriyalarni olish (tree uchun)."""
        query = """
            SELECT 
                id,
                title,
                parent,
                url,
                image_url,
                sort
            FROM mg_category
            WHERE invisible = 0
            ORDER BY parent ASC, sort ASC, title ASC
        """
        async with self.get_cursor() as cursor:
            await cursor.execute(query)
            categories = await cursor.fetchall()
            return [dict(c) for c in categories]
    
    async def get_category_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        """Kategoriyani ID bo'yicha olish."""
        query = """
            SELECT id, title, parent, url, image_url
            FROM mg_category
            WHERE id = %s AND invisible = 0
        """
        async with self.get_cursor() as cursor:
            await cursor.execute(query, (category_id,))
            category = await cursor.fetchone()
            return dict(category) if category else None
    
    async def get_category_path(self, category_id: int) -> str:
        """Build full category path for Moguta CMS URL (e.g., elektronika/televizory)."""
        path_parts = []
        current_id = category_id
        
        # Traverse up to 5 levels to prevent infinite loops
        for _ in range(5):
            if not current_id or current_id == 0:
                break
            
            category = await self.get_category_by_id(current_id)
            if not category:
                break
            
            if category.get('url'):
                path_parts.insert(0, category['url'])
            
            current_id = category.get('parent', 0)
        
        return '/'.join(path_parts) if path_parts else ''
    
    async def get_category_breadcrumbs(self, category_id: int) -> str:
        """Build human-readable category breadcrumbs (e.g., Elektronika > Televizorlar)."""
        path_names = []
        current_id = category_id
        
        # Traverse up to 5 levels to prevent infinite loops
        for _ in range(5):
            if not current_id or current_id == 0:
                break
            
            category = await self.get_category_by_id(current_id)
            if not category:
                break
            
            if category.get('title'):
                path_names.insert(0, category['title'])
            
            current_id = category.get('parent', 0)
        
        return ' > '.join(path_names) if path_names else 'Boshqa'
    
    # ==========================================
    # ORDERS (mg_order)
    # ==========================================
    
    async def get_order_by_id(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Buyurtmani ID bo'yicha olish."""
        query = """
            SELECT 
                id,
                status_id,
                summ as total,
                phone,
                email,
                name_buyer,
                address,
                comment,
                add_date as created_at,
                updata_date as updated_at
            FROM mg_order
            WHERE id = %s
        """
        async with self.get_cursor() as cursor:
            await cursor.execute(query, (order_id,))
            order = await cursor.fetchone()
            return dict(order) if order else None
    
    async def get_orders_by_phone(self, phone: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Telefon raqami bo'yicha buyurtmalarni olish."""
        # Telefon raqamini normalizatsiya qilish
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        query = """
            SELECT 
                id,
                status_id,
                summ as total,
                phone,
                name_buyer,
                add_date as created_at
            FROM mg_order
            WHERE REPLACE(REPLACE(REPLACE(phone, ' ', ''), '-', ''), '+', '') LIKE %s
            ORDER BY id DESC
            LIMIT %s
        """
        async with self.get_cursor() as cursor:
            await cursor.execute(query, (f"%{clean_phone}%", limit))
            orders = await cursor.fetchall()
            return [dict(o) for o in orders]
    
    async def get_order_items(self, order_id: int) -> List[Dict[str, Any]]:
        """Buyurtma tarkibini olish."""
        query = """
            SELECT 
                oc.id,
                oc.product_id,
                oc.name as product_name,
                oc.price,
                oc.count as quantity,
                oc.property as variants
            FROM mg_order_content oc
            WHERE oc.order_id = %s
        """
        async with self.get_cursor() as cursor:
            await cursor.execute(query, (order_id,))
            items = await cursor.fetchall()
            return [dict(i) for i in items]
    
    async def get_order_status_name(self, status_id: int) -> str:
        """Buyurtma statusi nomini olish."""
        status_map = {
            0: "Yangi buyurtma",
            1: "Qabul qilindi",
            2: "Jarayonda",
            3: "Yuborildi",
            4: "Yetkazildi",
            5: "Bekor qilindi"
        }
        return status_map.get(status_id, f"Status #{status_id}")
    
    # ==========================================
    # ANALYTICS
    # ==========================================
    
    async def get_products_count(self, in_stock: bool = True) -> int:
        """Mahsulotlar sonini olish."""
        query = "SELECT COUNT(*) as count FROM mg_product WHERE activity = 1"
        if in_stock:
            query += " AND count > 0"
        
        async with self.get_cursor() as cursor:
            await cursor.execute(query)
            result = await cursor.fetchone()
            return result['count'] if result else 0
    
    async def get_categories_count(self) -> int:
        """Kategoriyalar sonini olish."""
        query = "SELECT COUNT(*) as count FROM mg_category WHERE invisible = 0"
        async with self.get_cursor() as cursor:
            await cursor.execute(query)
            result = await cursor.fetchone()
        return result['count'] if result else 0

    async def get_all_category_names(self) -> str:
        """Kategoriyalar nomlarini olish (AI uchun)."""
        query = "SELECT title FROM mg_category WHERE invisible = 0 ORDER BY title ASC"
        async with self.get_cursor() as cursor:
            await cursor.execute(query)
            categories = await cursor.fetchall()
            if not categories:
                return ""
            return ", ".join([c['title'] for c in categories])

    async def create_order(self, user_data: Dict[str, Any], cart_items: list) -> int:
        """Create new order in Moguta CMS."""
        # 1. Insert into mg_order
        query_order = """
            INSERT INTO mg_order (
                add_date, 
                user_email, 
                phone, 
                address, 
                summ, 
                status_id, 
                delivery_id, 
                payment_id,
                name_buyer
            ) VALUES (
                NOW(), 
                %s, 
                %s, 
                %s, 
                %s, 
                1, 
                1, 
                1,
                %s
            )
        """
        
        # Prepare data
        email = user_data.get('email', '')  # Optional
        phone = user_data.get('phone', '')
        address = user_data.get('address', '')
        total_price = user_data.get('total_price', 0)
        name = user_data.get('name', '')
        
        async with self.get_cursor() as cursor:
            # Create order
            await cursor.execute(query_order, (email, phone, address, total_price, name))
            order_id = cursor.lastrowid
            
            # 2. Insert items into mg_order_product
            query_item = """
                INSERT INTO mg_order_product (
                    order_id, 
                    product_id, 
                    price, 
                    count
                ) VALUES (%s, %s, %s, %s)
            """
            
            items_data = []
            for item in cart_items:
                product = item['product']
                count = item['count']
                price = product.get('price', 0)
                items_data.append((order_id, product['id'], price, count))
            
            await cursor.executemany(query_item, items_data)
            
            return order_id


# Singleton instance
db = DatabaseService()
