"""
Bot Configuration Module
Barcha environment variables va sozlamalar shu yerda boshqariladi.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Telegram Bot
    bot_token: str = Field(..., env="BOT_TOKEN")
    bot_username: str = Field(default="optommarketai_bot", env="BOT_USERNAME")
    channel_id: str = Field(default="@optommarket7", env="CHANNEL_ID")
    
    # Database (Beget MySQL)
    db_host: str = Field(..., env="DB_HOST")
    db_port: int = Field(default=3306, env="DB_PORT")
    db_name: str = Field(..., env="DB_NAME")
    db_user: str = Field(..., env="DB_USER")
    db_password: str = Field(..., env="DB_PASSWORD")
    
    # AI (Gemini)
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    
    # Moguta CMS
    moguta_url: str = Field(..., env="MOGUTA_URL")
    
    # Admin Panel
    admin_secret_key: str = Field(default="change-me", env="ADMIN_SECRET_KEY")
    admin_username: str = Field(default="admin", env="ADMIN_USERNAME")
    admin_password: str = Field(default="admin", env="ADMIN_PASSWORD")
    
    # Telegram Admins
    admin_ids: str = Field(default="6224477868", env="ADMIN_IDS")
    
    @property
    def admin_id_list(self) -> list[int]:
        """Get list of admin IDs."""
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]
    
    # Webhook Settings
    use_webhook: bool = Field(default=False, env="USE_WEBHOOK")
    webhook_url: Optional[str] = Field(default=None, env="WEBHOOK_URL")
    webhook_secret: Optional[str] = Field(default=None, env="WEBHOOK_SECRET")
    
    # Instagram Integration
    meta_verify_token: Optional[str] = Field(default="optom_market_verify_2026", env="META_VERIFY_TOKEN")
    instagram_page_access_token: Optional[str] = Field(default=None, env="INSTAGRAM_PAGE_ACCESS_TOKEN")
    instagram_page_id: Optional[str] = Field(default=None, env="INSTAGRAM_PAGE_ID")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Meta/Facebook Catalog API
    meta_app_id: Optional[str] = Field(default=None, env="META_APP_ID")
    meta_app_secret: Optional[str] = Field(default=None, env="META_APP_SECRET")
    meta_access_token: Optional[str] = Field(default=None, env="META_ACCESS_TOKEN")
    meta_catalog_id: Optional[str] = Field(default=None, env="META_CATALOG_ID")
    meta_pixel_id: Optional[str] = Field(default=None, env="META_PIXEL_ID")

    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Shortcut for accessing settings
settings = get_settings()
