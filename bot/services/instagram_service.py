"""
Instagram Service
Instagram Direct API va Meta Graph API bilan ishlash uchun xizmat.
"""

import re
from typing import Any, Dict, Optional, Tuple

import httpx
from loguru import logger

from bot.config import settings


# ... imports ...
from bot.services.database import db
from bot.services.product_service import product_service
from bot.services.ai_service import ai_service

class InstagramService:
    """Service for Instagram Direct Messaging, comments, and follow checks."""

    GRAPH_API_VERSION = "v19.0"
    GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    def __init__(self):
        # Fallback to META_ACCESS_TOKEN if dedicated IG token is not set.
        self.access_token = settings.instagram_page_access_token or settings.meta_access_token
        self.page_id = settings.instagram_page_id

    async def handle_message(self, sender_id: str, text: str):
        """Handle incoming Instagram DM text with AI."""
        logger.info(f"Instagram DM from {sender_id}: {text}")

        # 1. AI Product Search & Intent Detection
        products, is_product_search = await product_service.ai_search(text)

        # 2. Check follow status if it's a product search
        if is_product_search:
            is_follower = await self.check_follow_status(sender_id)
            if not is_follower:
                 await self.send_dm(
                    sender_id,
                    (
                        "Iltimos, avval sahifamizga obuna bo'ling.\n"
                        "Shundan keyin barcha narxlar va bot havolasini yuboramiz."
                    ),
                )
                 return

        # 3. Generate AI Response
        ai_response, _ = await ai_service.get_response(
            user_id=int(sender_id) if sender_id.isdigit() else 0, # Use 0 or hash for non-integer IDs if needed
            user_message=text,
            products_context=products
        )

        # 4. Send Response
        await self.send_dm(recipient_id=sender_id, text=ai_response)


    async def handle_comment(
        self,
        comment_id: str,
        sender_id: str,
        sender_name: Optional[str],
        text: str,
        media_id: str,
    ):
        """
        Handle comment with AI:
        1. Analyze comment intent.
        2. Public reply (polite/engaging).
        3. Private reply (AI answer with product info).
        """
        sender_name = sender_name or "foydalanuvchi"
        logger.info(f"Instagram comment from {sender_name} ({sender_id}): {text}")

        # 1. AI Analysis (Reuse product search for intent)
        products, is_product_search = await product_service.ai_search(text)
        
        # If it's just a polluted/spam comment or very short generic one, maybe skip?
        # For now, let's respond to everything to drive engagement, or filter based on length.
        if len(text.split()) > 20: 
             # Skip very long comments to avoid AI costs on spam
             pass

        # 2. Public Reply
        public_text = f"@{sender_name} Javobni direktga yubordik! 📩"
        await self.reply_to_comment(comment_id, public_text)

        # 3. Generate Private AI Response
        ai_response, _ = await ai_service.get_response(
            user_id=int(sender_id) if sender_id.isdigit() else 0,
            user_message=text,
            products_context=products
        )
        
        # Prefix with greeting for context
        private_message = f"Assalomu alaykum, {sender_name}!\n\n{ai_response}"

        # 4. Send Private Reply
        # Try private_replies endpoint first
        sent = await self.send_private_reply(comment_id, private_message)
        if not sent:
            # Fallback to direct message
            sent = await self.send_dm(sender_id, private_message, use_human_agent=True)
        if not sent:
            sent = await self.send_dm(sender_id, private_message, use_human_agent=False)

        logger.info(
            f"Comment flow finished for comment_id={comment_id}, sender_id={sender_id}, sent={sent}"
        )

    # ... process_product_query removed as it is now integrated into handle_message ...

    async def check_follow_status(self, user_id: str) -> bool:
        """Check follow status (currently permissive)."""
        if not self.access_token:
            return True
        return True

    async def _post_graph(
        self,
        url: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        json_payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Unified POST helper for Graph API calls."""
        if not self.access_token:
            logger.warning("Instagram access token is not configured")
            return False, {}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    url,
                    params={"access_token": self.access_token},
                    data=data,
                    json=json_payload,
                )
            try:
                payload = response.json()
            except ValueError:
                payload = {"raw": response.text}

            if 200 <= response.status_code < 300 and not payload.get("error"):
                return True, payload

            logger.error(
                f"Graph API error status={response.status_code}, url={url}, payload={payload}"
            )
            return False, payload
        except Exception as e:
            logger.error(f"Graph API connection error: {e}")
            return False, {}

    async def reply_to_comment(self, comment_id: str, text: str) -> bool:
        """Write a public reply under a comment."""
        url = f"{self.GRAPH_API_BASE}/{comment_id}/replies"
        ok, _ = await self._post_graph(url, data={"message": text})
        if ok:
            logger.info(f"Replied to comment {comment_id}")
        return ok

    async def send_private_reply(self, comment_id: str, text: str) -> bool:
        """Send private reply linked to an Instagram comment event."""
        url = f"{self.GRAPH_API_BASE}/{comment_id}/private_replies"
        ok, _ = await self._post_graph(url, data={"message": text})
        if ok:
            logger.info(f"Private reply sent for comment {comment_id}")
        return ok

    async def send_dm(self, recipient_id: str, text: str, use_human_agent: bool = False) -> bool:
        """Send an Instagram DM via Send API."""
        endpoint_id = self.page_id or "me"
        url = f"{self.GRAPH_API_BASE}/{endpoint_id}/messages"

        payload: Dict[str, Any] = {
            "recipient": {"id": recipient_id},
            "message": {"text": text},
            "messaging_type": "RESPONSE",
        }
        if use_human_agent:
            payload["messaging_type"] = "MESSAGE_TAG"
            payload["tag"] = "HUMAN_AGENT"

        ok, _ = await self._post_graph(url, json_payload=payload)
        if ok:
            logger.info(f"DM sent to {recipient_id}")
        return ok


# Singleton
instagram_service = InstagramService()
