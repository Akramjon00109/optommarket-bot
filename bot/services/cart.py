"""
Cart Service - Savat bilan ishlash
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

from bot.services.product_service import product_service


class CartService:
    """Shopping cart manager using JSON file storage."""
    
    def __init__(self):
        self.file_path = Path(__file__).parent.parent.parent / "data" / "carts.json"
        self._ensure_file()
    
    def _ensure_file(self):
        """Create carts file if not exists."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            with open(self.file_path, 'w') as f:
                json.dump({}, f)
    
    def _load_carts(self) -> Dict[str, Any]:
        """Load carts from file."""
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load carts: {e}")
            return {}
    
    def _save_carts(self, carts: Dict[str, Any]):
        """Save carts to file."""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(carts, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save carts: {e}")
    
    def add_item(self, user_id: int, product_id: int, count: int = 1) -> bool:
        """Add item to user's cart."""
        user_id = str(user_id)
        product_id = str(product_id)
        
        carts = self._load_carts()
        
        if user_id not in carts:
            carts[user_id] = {"items": {}}
        
        items = carts[user_id]["items"]
        
        if product_id in items:
            items[product_id] += count
        else:
            items[product_id] = count
            
        self._save_carts(carts)
        return True
    
    def remove_item(self, user_id: int, product_id: int) -> bool:
        """Remove item from cart."""
        user_id = str(user_id)
        product_id = str(product_id)
        
        carts = self._load_carts()
        
        if user_id in carts and product_id in carts[user_id]["items"]:
            del carts[user_id]["items"][product_id]
            
            # If cart is empty, remove user entry
            if not carts[user_id]["items"]:
                del carts[user_id]
                
            self._save_carts(carts)
            return True
        return False
    
    def clear_cart(self, user_id: int):
        """Clear user's cart."""
        user_id = str(user_id)
        carts = self._load_carts()
        
        if user_id in carts:
            del carts[user_id]
            self._save_carts(carts)
    
    def get_cart_items(self, user_id: int) -> Dict[str, int]:
        """Get raw cart items {product_id: count}."""
        user_id = str(user_id)
        carts = self._load_carts()
        return carts.get(user_id, {}).get("items", {})
    
    async def get_cart_details(self, user_id: int) -> Dict[str, Any]:
        """Get full cart details with product info."""
        items = self.get_cart_items(user_id)
        
        if not items:
            return {"items": [], "total_price": 0, "total_count": 0}
        
        result_items = []
        total_price = 0
        total_count = 0
        
        for pid, count in items.items():
            product = await product_service.get_product_details(int(pid))
            if product:
                price = float(product.get('price', 0) or 0)
                subtotal = price * count
                
                result_items.append({
                    "product": product,
                    "count": count,
                    "subtotal": subtotal,
                    "formatted_price": product_service.format_price(price),
                    "formatted_subtotal": product_service.format_price(subtotal)
                })
                
                total_price += subtotal
                total_count += count
        
        return {
            "items": result_items,
            "total_price": total_price,
            "formatted_total_price": product_service.format_price(total_price),
            "total_count": total_count
        }


cart_service = CartService()
