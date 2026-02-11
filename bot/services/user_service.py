import json
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

class UserService:
    """Service for managing user profiles."""
    
    def __init__(self):
        self.file_path = Path(__file__).parent.parent.parent / "data" / "user_profiles.json"
        self._ensure_file()
    
    def _ensure_file(self):
        """Create file if not exists."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            with open(self.file_path, 'w') as f:
                json.dump({}, f)
    
    def _load_users(self) -> Dict[str, Any]:
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load users: {e}")
            return {}
    
    def _save_users(self, users: Dict[str, Any]):
        try:
            with open(self.file_path, 'w') as f:
                json.dump(users, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save users: {e}")

    async def exists(self, user_id: int) -> bool:
        """Check if user exists and has phone number."""
        users = self._load_users()
        return str(user_id) in users

    async def save_user(self, user_id: int, data: Dict[str, Any]):
        """Save user data."""
        users = self._load_users()
        users[str(user_id)] = data
        self._save_users(users)
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user data."""
        users = self._load_users()
        return users.get(str(user_id))

    async def get_all_users(self) -> Dict[str, Any]:
        """Get all users."""
        return self._load_users()

user_service = UserService()
