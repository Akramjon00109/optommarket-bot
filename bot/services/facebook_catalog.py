"""
Facebook/Meta Catalog API Service
Mahsulotlarni Facebook Ads katalogiga sinxronizatsiya qilish.
"""

import httpx
from typing import Optional, List, Dict, Any
from loguru import logger

from bot.config import settings
from bot.services.database import db


class FacebookCatalogService:
    """Meta Catalog API integration for product sync."""
    
    GRAPH_API_VERSION = "v19.0"
    GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
    
    def __init__(self):
        self.access_token = settings.meta_access_token
        self.catalog_id = settings.meta_catalog_id
        self.base_url = settings.moguta_url
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers."""
        return {
            "Content-Type": "application/json",
        }
    
    def _product_to_facebook_format(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Moguta CMS product to Facebook Catalog format.
        
        Facebook required fields:
        - id (retailer_id)
        - title
        - description
        - availability
        - condition
        - price
        - link
        - image_link
        - brand
        """
        # Build full product URL
        if getattr(settings, 'bot_username', None):
            product_url = f"https://t.me/{settings.bot_username}?start=product_{product['id']}"
        else:
            product_url = f"{self.base_url}/{product.get('url', '')}"
        
        # Build full image URL
        image_url = product.get('image_url', '')
        if image_url and not image_url.startswith('http'):
            image_url = f"{self.base_url}/uploads/{image_url}"
        
        # Determine availability
        stock = product.get('stock', 0)
        if stock == -1:  # Unlimited stock in Moguta
            availability = "in stock"
        elif stock > 0:
            availability = "in stock"
        else:
            availability = "out of stock"
        
        # Price formatting (Facebook needs currency code)
        price = product.get('price', 0)
        price_str = f"{int(price)} UZS"
        
        # Description - clean HTML if present
        description = product.get('description', '') or product.get('short_description', '') or product.get('title', '')
        # Remove HTML tags
        import re
        description = re.sub(r'<[^>]+>', '', description)
        description = description[:5000]  # Facebook limit
        
        return {
            "retailer_id": str(product['id']),
            "name": product.get('title', '')[:150],
            "description": description,
            "availability": availability,
            "condition": "new",
            "price": int(price),
            "currency": "UZS",
            "url": product_url,
            "image_url": image_url,
            "brand": "Optom Market",
            "category": product.get('category_name', 'Other'),
        }
    
    async def sync_products(self) -> Dict[str, Any]:
        """
        Sync all products from database to Facebook Catalog.
        
        Returns:
            dict with sync results (added, updated, errors)
        """
        if not self.access_token:
            logger.warning("Meta Access Token not configured, skipping catalog sync")
            return {"status": "skipped", "reason": "no_access_token"}
        
        result = {
            "status": "success",
            "total": 0,
            "synced": 0,
            "errors": 0,
            "error_messages": []
        }
        
        try:
            # Get all active products from database
            products = await db.get_products(limit=10000, in_stock=False)
            result["total"] = len(products)
            
            if not products:
                logger.info("No products found to sync")
                return result
            
            # Prepare batch request (Facebook allows up to 5000 items per batch)
            batch_size = 1000
            for i in range(0, len(products), batch_size):
                batch = products[i:i + batch_size]
                batch_result = await self._sync_batch(batch)
                result["synced"] += batch_result.get("synced", 0)
                result["errors"] += batch_result.get("errors", 0)
                if batch_result.get("error_messages"):
                    result["error_messages"].extend(batch_result["error_messages"])
            
            logger.info(f"✅ Facebook Catalog sync complete: {result['synced']}/{result['total']} products")
            
        except Exception as e:
            logger.error(f"❌ Facebook Catalog sync failed: {e}")
            result["status"] = "error"
            result["error_messages"].append(str(e))
        
        return result
    
    async def _sync_batch(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sync a batch of products using Facebook Batch API."""
        result = {"synced": 0, "errors": 0, "error_messages": []}
        
        # Build requests array for batch
        requests = []
        for product in products:
            fb_product = self._product_to_facebook_format(product)
            retailer_id = fb_product["retailer_id"]
            
            # Create data payload without retailer_id
            product_data = fb_product.copy()
            if "retailer_id" in product_data:
                del product_data["retailer_id"]
            
            requests.append({
                "method": "UPDATE",
                "retailer_id": retailer_id,
                "data": product_data
            })
        
        # Facebook Catalog Batch API endpoint
        url = f"{self.GRAPH_API_BASE}/{self.catalog_id}/batch"
        
        logger.info(f"Sending batch with {len(requests)} items")
        
        payload = {
            "access_token": self.access_token,
            "requests": requests,
            "item_type": "PRODUCT_ITEM"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload)
                response_data = response.json()
                
                if response.status_code == 200:
                    # Parse handles array
                    handles = response_data.get("handles", [])
                    # Note: Facebook returns handles for batch jobs. 
                    # Each handle can represent multiple items.
                    # If we got handles and no immediate errors, we consider all items submitted.
                    result["synced"] = len(products)
                    
                    # Check for validation errors
                    validation_status = response_data.get("validation_status", [])
                    for status in validation_status:
                        if status.get("errors"):
                            # If there's a validation error for an item, it won't be synced
                            result["synced"] -= 1
                            result["errors"] += 1
                            result["error_messages"].append(str(status.get("errors")))
                else:
                    error_msg = response_data.get("error", {}).get("message", "Unknown error")
                    result["errors"] = len(products)
                    result["error_messages"].append(error_msg)
                    logger.error(f"Facebook API error: {error_msg}")
                    
            except Exception as e:
                result["errors"] = len(products)
                result["error_messages"].append(str(e))
                logger.error(f"Batch sync error: {e}")
        
        return result
    
    async def add_product(self, product: Dict[str, Any]) -> bool:
        """Add a single product to Facebook Catalog."""
        if not self.access_token:
            return False
        
        fb_product = self._product_to_facebook_format(product)
        url = f"{self.GRAPH_API_BASE}/{self.catalog_id}/products"
        
        params = {
            "access_token": self.access_token,
            **fb_product
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, data=params)
                if response.status_code == 200:
                    logger.info(f"Product {product['id']} added to Facebook Catalog")
                    return True
                else:
                    error = response.json().get("error", {})
                    logger.error(f"Failed to add product: {error}")
                    return False
            except Exception as e:
                logger.error(f"Add product error: {e}")
                return False
    
    async def delete_product(self, product_id: str) -> bool:
        """Delete a product from Facebook Catalog."""
        if not self.access_token:
            return False
        
        url = f"{self.GRAPH_API_BASE}/{self.catalog_id}/products"
        
        params = {
            "access_token": self.access_token,
            "requests": [{"method": "DELETE", "retailer_id": product_id}]
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=params)
                return response.status_code == 200
            except Exception as e:
                logger.error(f"Delete product error: {e}")
                return False
    
    async def get_catalog_info(self) -> Dict[str, Any]:
        """Get catalog statistics from Facebook."""
        if not self.access_token:
            return {"error": "no_access_token"}
        
        url = f"{self.GRAPH_API_BASE}/{self.catalog_id}"
        params = {
            "access_token": self.access_token,
            "fields": "name,product_count,vertical"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": response.json().get("error", {}).get("message", "Unknown")}
            except Exception as e:
                return {"error": str(e)}

    async def get_products(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Get products from Facebook Catalog."""
        if not self.access_token:
            return []
        
        url = f"{self.GRAPH_API_BASE}/{self.catalog_id}/products"
        params = {
            "access_token": self.access_token,
            "fields": "id,retailer_id,name,description,price,availability,image_url",
            "limit": limit
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", [])
                else:
                    logger.error(f"Failed to get products: {response.text}")
                    return []
            except Exception as e:
                logger.error(f"Get products error: {e}")
                return []

    async def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search products in Facebook Catalog."""
        if not self.access_token:
            return []
        
        # Note: Graph API filtering syntax
        import json
        params = {
            "access_token": self.access_token,
            "fields": "id,retailer_id,name,description,price,availability,image_url",
            "filter": json.dumps({"name": {"i_contains": query}}),
            "limit": limit
        }
        
        url = f"{self.GRAPH_API_BASE}/{self.catalog_id}/products"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", [])
                else:
                    logger.error(f"Failed to search products: {response.text}")
                    return []
            except Exception as e:
                logger.error(f"Search products error: {e}")
                return []


# Singleton instance
fb_catalog = FacebookCatalogService()
