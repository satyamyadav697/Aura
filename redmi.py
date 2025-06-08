import redis
from config import REDIS_URL

class RedisManager:
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL)
    
    def get_user_data(self, user_id: int) -> dict:
        """Get all data for a user."""
        user_key = f"user:{user_id}"
        data = self.redis.hgetall(user_key)
        
        # Convert bytes to strings/ints
        return {
            'xp': int(data.get(b'xp', 0)),
            'level': int(data.get(b'level', 1)),
            'messages': int(data.get(b'messages', 0))
        }
    
    def increment_xp(self, user_id: int, amount: int = 1) -> int:
        """Increment user's XP and return new value."""
        user_key = f"user:{user_id}"
        return self.redis.hincrby(user_key, "xp", amount)
    
    def increment_level(self, user_id: int, amount: int = 1) -> int:
        """Increment user's level and return new value."""
        user_key = f"user:{user_id}"
        return self.redis.hincrby(user_key, "level", amount)
    
    def increment_messages(self, user_id: int, amount: int = 1) -> int:
        """Increment user's message count and return new value."""
        user_key = f"user:{user_id}"
        return self.redis.hincrby(user_key, "messages", amount)
    
    def get_leaderboard(self, limit: int = 10) -> list:
        """Get top users sorted by level and XP."""
        user_keys = self.redis.keys("user:*")
        users = []
        
        for key in user_keys:
            user_id = key.decode().split(":")[1]
            data = self.get_user_data(user_id)
            if data['level'] > 0:
                users.append({
                    'user_id': user_id,
                    'level': data['level'],
                    'xp': data['xp'],
                    'messages': data['messages']
                })
        
        # Sort by level (desc), then XP (desc)
        users.sort(key=lambda x: (-x['level'], -x['xp']))
        return users[:limit]
    
    def reset_user(self, user_id: int) -> None:
        """Reset a user's data."""
        user_key = f"user:{user_id}"
        self.redis.hset(user_key, "xp", 0)
        self.redis.hset(user_key, "level", 1)
        self.redis.hset(user_key, "messages", 0)
    
    def delete_user(self, user_id: int) -> None:
        """Delete a user's data."""
        user_key = f"user:{user_id}"
        self.redis.delete(user_key)
    
    def get_total_users(self) -> int:
        """Get total number of tracked users."""
        return len(self.redis.keys("user:*"))

# Singleton instance
redis_manager = RedisManager()
