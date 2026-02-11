"""
Utility helpers for the bot.
"""

import re
from typing import Optional


def clean_phone_number(phone: str) -> str:
    """Clean phone number to digits only."""
    return ''.join(filter(str.isdigit, phone))


def format_phone_number(phone: str) -> str:
    """Format phone number for display."""
    digits = clean_phone_number(phone)
    
    if len(digits) == 12 and digits.startswith('998'):
        return f"+{digits[:3]} ({digits[3:5]}) {digits[5:8]}-{digits[8:10]}-{digits[10:12]}"
    elif len(digits) == 9:
        return f"+998 ({digits[:2]}) {digits[2:5]}-{digits[5:7]}-{digits[7:9]}"
    
    return phone


def format_price(price: float) -> str:
    """Format price with space separators."""
    return f"{price:,.0f}".replace(",", " ")


def clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text)


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def is_valid_order_id(text: str) -> bool:
    """Check if text is a valid order ID."""
    return text.isdigit() and int(text) > 0


def is_phone_number(text: str) -> bool:
    """Check if text looks like a phone number."""
    digits = clean_phone_number(text)
    return len(digits) >= 9 and len(digits) <= 15


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def get_stock_status(count: Optional[int]) -> tuple[str, str]:
    """Get stock status emoji and text."""
    if count is None:
        return "❓", "Noma'lum"
    elif count > 10:
        return "✅", "Mavjud"
    elif count > 0:
        return "⚠️", f"Kam qoldi ({count} dona)"
    else:
        return "❌", "Tugagan"
