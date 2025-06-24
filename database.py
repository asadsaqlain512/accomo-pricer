import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
import redis
from redis import Redis

from config import Config
from models import CrawledPriceRecord, SearchResult, CacheKey

class DatabaseService:
    """Service for handling MongoDB and Redis operations"""
    
    def __init__(self):
        self.logger = logging.getLogger("database_service")
        self.mongo_client: Optional[MongoClient] = None
        self.mongo_db: Optional[Database] = None
        self.mongo_collection: Optional[Collection] = None
        self.redis_client: Optional[Redis] = None
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialize MongoDB and Redis connections"""
        try:
            # Initialize MongoDB
            self.mongo_client = MongoClient(Config.MONGODB_URI)
            self.mongo_db = self.mongo_client[Config.MONGODB_DATABASE]
            self.mongo_collection = self.mongo_db[Config.MONGODB_COLLECTION]
            
            # Create indexes for efficient querying
            self._create_indexes()
            
            self.logger.info(f"Connected to MongoDB: {Config.MONGODB_URI}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
        
        try:
            # Initialize Redis
            self.redis_client = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                password=Config.REDIS_PASSWORD,
                decode_responses=True
            )
            
            # Test Redis connection
            self.redis_client.ping()
            self.logger.info(f"Connected to Redis: {Config.REDIS_HOST}:{Config.REDIS_PORT}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    
    def _create_indexes(self):
        """Create indexes for efficient querying"""
        try:
            # Create compound index for search criteria
            self.mongo_collection.create_index([
                ("hotel_name", 1),
                ("city", 1),
                ("country", 1),
                ("checkin_date", 1),
                ("checkout_date", 1)
            ])
            
            # Create index for crawled_at for time-based queries
            self.mongo_collection.create_index([("crawled_at", -1)])
            
            # Create index for job_id
            self.mongo_collection.create_index([("job_id", 1)])
            
            self.logger.info("MongoDB indexes created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to create indexes: {str(e)}")
    
    def _serialize_for_cache(self, data: Any) -> str:
        """Serialize data for Redis cache"""
        if isinstance(data, CrawledPriceRecord):
            return data.json()
        return json.dumps(data, default=str)
    
    def _deserialize_from_cache(self, data: str, model_class=None):
        """Deserialize data from Redis cache"""
        if model_class == CrawledPriceRecord:
            return CrawledPriceRecord.parse_raw(data)
        return json.loads(data)
    
    def get_cache_key(self, hotel_name: str, city: str, country: str, 
                     checkin_date: date, checkout_date: date, state: Optional[str] = None) -> str:
        """Generate cache key for the search criteria"""
        cache_key = CacheKey(
            hotel_name=hotel_name,
            city=city,
            country=country,
            checkin_date=checkin_date,
            checkout_date=checkout_date,
            state=state
        )
        return cache_key.to_key()
    
    async def get_cached_prices(self, hotel_name: str, city: str, country: str,
                              checkin_date: date, checkout_date: date, 
                              state: Optional[str] = None) -> Optional[CrawledPriceRecord]:
        """Get prices from cache if available"""
        try:
            cache_key = self.get_cache_key(hotel_name, city, country, checkin_date, checkout_date, state)
            
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                self.logger.info(f"Cache hit for key: {cache_key}")
                return self._deserialize_from_cache(cached_data, CrawledPriceRecord)
            
            self.logger.info(f"Cache miss for key: {cache_key}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting cached prices: {str(e)}")
            return None
    
    async def cache_prices(self, price_record: CrawledPriceRecord) -> bool:
        """Cache prices in Redis"""
        try:
            cache_key = self.get_cache_key(
                price_record.hotel_name,
                price_record.city,
                price_record.country,
                price_record.checkin_date,
                price_record.checkout_date,
                price_record.state
            )
            
            serialized_data = self._serialize_for_cache(price_record)
            self.redis_client.setex(cache_key, Config.CACHE_TTL, serialized_data)
            
            self.logger.info(f"Cached prices for key: {cache_key} with TTL: {Config.CACHE_TTL}s")
            return True
            
        except Exception as e:
            self.logger.error(f"Error caching prices: {str(e)}")
            return False
    
    async def save_prices_to_mongodb(self, price_record: CrawledPriceRecord) -> bool:
        """Save crawled prices to MongoDB"""
        try:
            # Convert to dict for MongoDB insertion
            price_dict = price_record.dict()
            
            # Insert into MongoDB
            result = self.mongo_collection.insert_one(price_dict)
            
            self.logger.info(f"Saved prices to MongoDB with ID: {result.inserted_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving prices to MongoDB: {str(e)}")
            return False
    
    async def get_prices_from_mongodb(self, hotel_name: str, city: str, country: str,
                                    checkin_date: date, checkout_date: date,
                                    state: Optional[str] = None) -> Optional[CrawledPriceRecord]:
        """Get prices from MongoDB"""
        try:
            # Build query
            query = {
                "hotel_name": hotel_name,
                "city": city,
                "country": country,
                "checkin_date": checkin_date.isoformat(),
                "checkout_date": checkout_date.isoformat()
            }
            
            if state:
                query["state"] = state
            
            # Get the most recent result
            result = self.mongo_collection.find_one(
                query,
                sort=[("crawled_at", -1)]
            )
            
            if result:
                # Convert MongoDB document back to CrawledPriceRecord
                # Handle date conversion
                result["checkin_date"] = datetime.fromisoformat(result["checkin_date"]).date()
                result["checkout_date"] = datetime.fromisoformat(result["checkout_date"]).date()
                result["crawled_at"] = datetime.fromisoformat(result["crawled_at"])
                
                return CrawledPriceRecord(**result)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting prices from MongoDB: {str(e)}")
            return None
    
    async def save_search_results(self, hotel_name: str, city: str, country: str,
                                checkin_date: date, checkout_date: date,
                                state: Optional[str], latitude: Optional[float],
                                longitude: Optional[float], job_id: str,
                                results: List[SearchResult]) -> bool:
        """Save search results to both MongoDB and cache"""
        try:
            # Group results by platform
            platform_prices: Dict[str, List[SearchResult]] = {}
            for result in results:
                if result.platform not in platform_prices:
                    platform_prices[result.platform] = []
                platform_prices[result.platform].append(result)
            
            # Create price record
            price_record = CrawledPriceRecord(
                hotel_name=hotel_name,
                city=city,
                country=country,
                checkin_date=checkin_date,
                checkout_date=checkout_date,
                state=state,
                latitude=latitude,
                longitude=longitude,
                platform_prices=platform_prices,
                total_results=len(results),
                job_id=job_id
            )
            
            # Save to MongoDB
            mongo_success = await self.save_prices_to_mongodb(price_record)
            
            # Cache the results
            cache_success = await self.cache_prices(price_record)
            
            if mongo_success and cache_success:
                self.logger.info(f"Successfully saved and cached {len(results)} results for job {job_id}")
                return True
            else:
                self.logger.warning(f"Partial save: MongoDB={mongo_success}, Cache={cache_success}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error saving search results: {str(e)}")
            return False
    
    def close_connections(self):
        """Close database connections"""
        try:
            if self.mongo_client:
                self.mongo_client.close()
                self.logger.info("MongoDB connection closed")
            
            if self.redis_client:
                self.redis_client.close()
                self.logger.info("Redis connection closed")
                
        except Exception as e:
            self.logger.error(f"Error closing connections: {str(e)}")

# Global database service instance
db_service: Optional[DatabaseService] = None

def get_db_service() -> DatabaseService:
    """Get the global database service instance"""
    global db_service
    if db_service is None:
        db_service = DatabaseService()
    return db_service 