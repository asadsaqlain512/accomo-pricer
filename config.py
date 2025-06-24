import os
from typing import Dict, List

class Config:
    """Configuration class for the accommodation price crawler"""
    
    # API Settings
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    DEBUG = True
    
    # WebSocket Settings
    WS_PING_INTERVAL = 20
    WS_PING_TIMEOUT = 20
    
    # MongoDB Settings
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "accomopricer")
    MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "crawled_prices")
    
    # Redis Settings (for caching)
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
    CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))  # 1 hour default
    
    # Platform Configuration - Enable/Disable platforms
    PLATFORMS = {
        "airbnb": {
            "enabled": True,
            "base_url": "https://www.airbnb.com",
            "search_url": "https://www.airbnb.com/s/",
            "delay_between_requests": 2,
            "max_retries": 3
        },
        "booking": {
            "enabled": True,
            "base_url": "https://www.booking.com",
            "search_url": "https://www.booking.com/search.html",
            "delay_between_requests": 3,
            "max_retries": 3
        },
        "expedia": {
            "enabled": True,
            "base_url": "https://www.expedia.com",
            "search_url": "https://www.expedia.com/Hotel-Search",
            "delay_between_requests": 2,
            "max_retries": 3
        },
        "hotels": {
            "enabled": True,
            "base_url": "https://www.hotels.com",
            "search_url": "https://www.hotels.com/search.do",
            "delay_between_requests": 2,
            "max_retries": 3
        },
        "tripadvisor": {
            "enabled": True,
            "base_url": "https://www.tripadvisor.com",
            "search_url": "https://www.tripadvisor.com/Hotels",
            "delay_between_requests": 3,
            "max_retries": 3
        },
        "vrbo": {
            "enabled": True,
            "base_url": "https://www.vrbo.com",
            "search_url": "https://www.vrbo.com/search",
            "delay_between_requests": 2,
            "max_retries": 3
        }
    }
    
    # Proxy Settings (optional - for production use)
    USE_PROXIES = False
    PROXY_LIST = [
        # Add your proxy list here if needed
        # "http://proxy1:port",
        # "http://proxy2:port",
    ]
    
    # Request Settings
    REQUEST_TIMEOUT = 30
    MAX_CONCURRENT_REQUESTS = 5
    
    # User Agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    
    # Job Settings
    JOB_TIMEOUT = 300  # 5 minutes
    MAX_PRICE_RESULTS_PER_PLATFORM = 10
    
    @classmethod
    def get_enabled_platforms(cls) -> List[str]:
        """Get list of enabled platforms"""
        return [name for name, config in cls.PLATFORMS.items() if config["enabled"]]
    
    @classmethod
    def get_platform_config(cls, platform: str) -> Dict:
        """Get configuration for a specific platform"""
        return cls.PLATFORMS.get(platform, {}) 