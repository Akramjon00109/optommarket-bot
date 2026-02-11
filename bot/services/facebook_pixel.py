"""
Facebook Pixel / Conversions API Service
"""

import time
import hashlib
import httpx
from typing import Dict, Any, Optional
from loguru import logger

from bot.config import settings

class FacebookPixelService:
    """Service for sending server-side events to Facebook Conversions API."""
    
    GRAPH_API_VERSION = "v19.0"
    GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
    
    def __init__(self):
        self.pixel_id = settings.meta_pixel_id
        self.access_token = settings.meta_access_token
        
    def _hash_data(self, data: str) -> str:
        """SHA256 hash of normalized data."""
        if not data:
            return ""
        return hashlib.sha256(data.strip().lower().encode('utf-8')).hexdigest()
        
    async def send_event(
        self, 
        event_name: str, 
        user_data: Dict[str, Any], 
        custom_data: Optional[Dict[str, Any]] = None,
        event_source_url: str = None
    ) -> bool:
        """
        Send an event to Facebook Conversions API.
        
        Args:
            event_name: Standard event name (e.g., ViewContent, AddToCart, Purchase)
            user_data: Dict containing user info. Keys should match FB requirements:
                       - id (telegram_id) -> external_id
                       - phone -> ph (hashed)
                       - first_name -> fn (hashed)
                       - last_name -> ln (hashed)
                       - client_ip_address
                       - client_user_agent
            custom_data: Additional event data (value, currency, content_ids, etc.)
            event_source_url: URL where the event occurred (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.pixel_id or not self.access_token:
            logger.warning(
                "Facebook Pixel config missing (META_PIXEL_ID or META_ACCESS_TOKEN). Event skipped."
            )
            return False
            
        url = f"{self.GRAPH_API_BASE}/{self.pixel_id}/events"
        
        # Prepare User Data
        fb_user_data = {}
        
        if "id" in user_data:
            fb_user_data["external_id"] = self._hash_data(str(user_data["id"]))
            
        if "phone" in user_data:
            phone = user_data["phone"]
            # Remove symbols, keep only digits
            import re
            phone = re.sub(r'\D', '', str(phone))
            fb_user_data["ph"] = self._hash_data(phone)
            
        if "first_name" in user_data:
            fb_user_data["fn"] = self._hash_data(user_data["first_name"])
            
        if "last_name" in user_data:
            fb_user_data["ln"] = self._hash_data(user_data["last_name"])
            
        if "client_ip_address" in user_data:
            fb_user_data["client_ip_address"] = user_data["client_ip_address"]
            
        if "client_user_agent" in user_data:
            fb_user_data["client_user_agent"] = user_data["client_user_agent"]
            
        # Prepare Event
        event = {
            "event_name": event_name,
            "event_time": int(time.time()),
            "user_data": fb_user_data,
            "action_source": "chat",
        }

        # Meta requires some user identifier hash in most cases.
        if not fb_user_data:
            logger.warning(f"Pixel event skipped due to empty user_data: {event_name}")
            return False
        
        if custom_data:
            event["custom_data"] = custom_data
            
        if event_source_url:
            event["event_source_url"] = event_source_url
            
        payload = {
            "data": [event],
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    params={"access_token": self.access_token},
                    json=payload
                )
                try:
                    data = response.json()
                except ValueError:
                    data = {"raw": response.text}

                if response.status_code == 200 and data.get("events_received", 0) > 0:
                    logger.info(
                        f"Pixel event sent: {event_name} "
                        f"(received={data.get('events_received')})"
                    )
                    return True

                logger.warning(f"Pixel event failed: status={response.status_code}, body={data}")
                return False
        except Exception as e:
            logger.error(f"Pixel connection error: {e}")
            return False

# Singleton
fb_pixel = FacebookPixelService()
