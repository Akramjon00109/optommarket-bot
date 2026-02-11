"""
AI Service - Google Gemini Integration (new google-genai SDK)
RAG tizimi va tabiiy tilda qidiruv.
"""

import json
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from google import genai
from google.genai import types
from loguru import logger

from bot.config import settings


class AIService:
    """AI Assistant using Google Gemini API (new SDK)."""
    
    def __init__(self):
        # Initialize client with API key
        try:
            self.client = genai.Client(api_key=settings.gemini_api_key)
            self.model_id = "gemini-2.0-flash-lite"
            logger.info(f"Google GenAI client initialized with {self.model_id}")
        except Exception as e:
            logger.error(f"Failed to init GenAI client: {e}")
            self.client = None
        
        # Load knowledge base
        self.knowledge_base = self._load_knowledge_base()
        
        # User session contexts
        self.user_contexts: Dict[int, List[Dict]] = {}
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load company knowledge base from JSON file."""
        kb_path = Path(__file__).parent.parent.parent / "data" / "knowledge_base.json"
        
        if kb_path.exists():
            with open(kb_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Default knowledge base
        return {
            "company_info": {
                "name": "OptomMarket",
                "description": "Optom va chakana savdo do'koni",
                "delivery": "Toshkent bo'ylab bepul yetkazib berish. Viloyatlarga pochta orqali.",
                "payment": "Naqd, karta (Uzcard, Humo), Click, Payme",
                "working_hours": "Dushanba - Shanba: 9:00 - 18:00",
                "phone": "+998 97 477 12 29",
                "address": "Toshkent shahri",
                "minimal_order": "Minimal buyurtma miqdori yoki summasi yo'q. Istalgan miqdorda (1 dona bo'lsa ham) xarid qilishingiz mumkin."
            },
            "tone_of_voice": "Professional, do'stona va yordamga tayyor sotuvchi konsultant. O'zbek tilida muloqot.",
            "greeting": "Assalomu alaykum! OptomMarket botiga xush kelibsiz. Sizga qanday yordam bera olaman?",
            "capabilities": [
                "Mahsulotlarni qidirish va tavsiya qilish",
                "Narxlar haqida ma'lumot berish",
                "Buyurtma holatini tekshirish",
                "Yetkazib berish va to'lov haqida ma'lumot"
            ]
        }
    
    def save_knowledge_base(self, data: Dict[str, Any]) -> bool:
        """Save knowledge base to JSON file."""
        kb_path = Path(__file__).parent.parent.parent / "data" / "knowledge_base.json"
        kb_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(kb_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.knowledge_base = data
            return True
        except Exception as e:
            logger.error(f"Failed to save knowledge base: {e}")
            return False
    
    def _format_products_context(self, products: List[Dict[str, Any]]) -> str:
        """Format products for AI context."""
        if not products:
            return "Hozircha mos mahsulotlar topilmadi."
        
        lines = []
        for p in products[:5]:
            try:
                price_val = float(p.get('price', 0) or 0)
                price = f"{price_val:,.0f}".replace(",", " ")
            except (ValueError, TypeError):
                price = "0"
            stock_status = "✅ Mavjud" if p.get('stock', 0) > 0 else "❌ Tugagan"
            lines.append(
                f"- ID: {p['id']} | {p['title']} | {price} so'm | {stock_status}"
            )
        
        return "\n".join(lines)

    async def _build_system_prompt(self, products_context: str = "") -> str:
        """Build system prompt with RAG context."""
        company = self.knowledge_base.get("company_info", {})
        tone = self.knowledge_base.get("tone_of_voice", "")
        
        # Fetch categories from DB
        try:
            from bot.services.database import DatabaseService
            db = DatabaseService()
            categories = await db.get_all_category_names()
        except Exception as e:
            categories = ""

        prompt = f"""Siz \"{company.get('name', 'OptomMarket')}\" do'konining AI yordamchisisiz.

## Kompaniya haqida:
- Tavsif: {company.get('description', '')}
- Yetkazib berish: {company.get('delivery', '')}
- To'lov usullari: {company.get('payment', '')}
- Ish vaqti: {company.get('working_hours', '')}
- Telefon: {company.get('phone', '')}
- Manzil: {company.get('address', '')}

## Mavjud Kategoriyalar:
{categories if categories else "Ma'lumot yo'q"}

## Muloqot uslubi:
{tone}

## Qoidalar:
1. Har doim O'zbek tilida javob bering
2. Qisqa va aniq javob bering
3. Mahsulot so'ralganda, bazadan topilgan ma'lumotlarni ishlating
4. Narxlarni formatlang (masalan: 150,000 so'm)
5. Agar mahsulot topilmasa, shunga o'xshash mahsulotlarni tavsiya qiling
6. Foydalanuvchiga do'stona munosabatda bo'ling
7. Agar foydalanuvchi "kategoriyalar" haqida so'rasa, yuqoridagi ro'yxatdan foydalaning.

## Imkoniyatlaringiz:
- Mahsulotlarni qidirish va tavsiya qilish
- Narxlar haqida ma'lumot berish
- Buyurtma holatini tekshirish
- Yetkazib berish va to'lov haqida ma'lumot berish

"""
        
        if products_context:
            prompt += f"""
## Bazadagi tegishli mahsulotlar:
{products_context}

Foydalanuvchi so'roviga mos ravishda yuqoridagi mahsulotlardan foydalaning.
"""
        
        return prompt

    async def extract_search_params(self, user_message: str) -> Dict[str, Any]:
        """
        Extract search parameters from natural language query.
        Returns: {search_query, min_price, max_price, category_hint}
        """
        extraction_prompt = f"""Foydalanuvchi xabaridan qidiruv parametrlarini ajratib oling.

Xabar: "{user_message}"

DIQQAT: Bazadagi mahsulotlar asosan RUS tilida nomlangan bo'lishi mumkin.
Shuning uchun "translated_keywords" maydoniga mahsulot nomini RUS tilidagi tarjimasini ham qo'shing.

Javobni FAQAT quyidagi JSON formatida qaytaring (boshqa so'z qo'shmang):
{{
    "search_query": "mahsulot nomi yoki kalit so'z (asl tilda)",
    "translated_keywords": "mahsulot nomi (Rus tilida) yoki null",
    "min_price": null yoki raqam (so'm),
    "max_price": null yoki raqam (so'm),
    "category_hint": "kategoriya nomi yoki null",
    "is_product_search": true/false (bu mahsulot qidiruv so'rovi yoki yo'q)
}}
"""

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_id,
                contents=extraction_prompt
            )
            text = response.text.strip()

            # Robust JSON extraction: find first '{' and last '}'
            start = text.find('{')
            end = text.rfind('}')
            
            if start != -1 and end != -1:
                json_str = text[start:end+1]
                params = json.loads(json_str)
                logger.info(f"🔍 Extracted params: {params}")
                return params
            else:
                 logger.warning(f"⚠️ JSON parsing failed, text: {text}")
                 raise ValueError("No JSON found")

        except Exception as e:
            logger.error(f"Failed to extract search params: {e}")
            # Fallback: treat short messages as simple search
            if len(user_message.split()) <= 3:
                logger.info(f"⚠️ Search extraction failed, using fallback for: {user_message}")
                return {
                    "search_query": user_message,
                    "translated_keywords": None,
                    "min_price": None,
                    "max_price": None,
                    "category_hint": None,
                    "is_product_search": True
                }
            
            return {
                "search_query": user_message,
                "min_price": None,
                "max_price": None,
                "category_hint": None,
                "is_product_search": False
            }

    async def get_response(
        self,
        user_id: int,
        user_message: str,
        products_context: List[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Generate AI response with RAG context.
        
        Returns:
            Tuple of (response_text, mentioned_products)
        """
        # Format products for context
        products_str = self._format_products_context(products_context or [])
        
        # Build system prompt
        system_prompt = await self._build_system_prompt(products_str)
        
        # Get user context (last 5 messages)
        user_history = self.user_contexts.get(user_id, [])[-5:]
        
        # Build conversation contents
        contents = []
        
        # Add history
        for msg in user_history:
            contents.append(types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["text"])]
            ))
        
        # Add current user message
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)]
        ))
        
        # Retry loop for rate limits
        max_retries = 4
        base_delay = 3
        
        for attempt in range(max_retries):
            try:
                # Generate response using new SDK
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_id,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt
                    )
                )
                
                ai_response = response.text.strip()
                
                # Update user context
                if user_id not in self.user_contexts:
                    self.user_contexts[user_id] = []
                
                self.user_contexts[user_id].append({"role": "user", "text": user_message})
                self.user_contexts[user_id].append({"role": "model", "text": ai_response})
                
                # Keep only last 10 messages
                self.user_contexts[user_id] = self.user_contexts[user_id][-10:]
                
                return ai_response, products_context or []
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "ResourceExhausted" in error_msg:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"AI Rate limit hit, retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        continue
                
                logger.error(f"AI Chat Error (Attempt {attempt+1}): {e}")
                if attempt == max_retries - 1:
                    return (
                        "Kechirasiz, hozirda texnik xatolik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring.",
                        []
                    )

        return (
            "Kechirasiz, javob olishning imkoni bo'lmadi.",
            []
        )
    
    def clear_user_context(self, user_id: int) -> None:
        """Clear user conversation context."""
        if user_id in self.user_contexts:
            del self.user_contexts[user_id]


# Singleton instance
ai_service = AIService()
