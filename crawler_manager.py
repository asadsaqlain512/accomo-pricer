import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime

from config import Config
from models import SearchResult, PriceRequest
from crawlers.airbnb_crawler import AirbnbCrawler
from crawlers.booking_crawler import BookingCrawler
from crawlers.expedia_crawler import ExpediaCrawler
from crawlers.hotels_crawler import HotelsCrawler
from crawlers.tripadvisor_crawler import TripAdvisorCrawler
from crawlers.vrbo_crawler import VRBOCrawler

class CrawlerManager:
    """Manages all platform crawlers and coordinates searches"""
    
    def __init__(self):
        self.logger = logging.getLogger("crawler_manager")
        self.crawlers = {}
        self._initialize_crawlers()
    
    def _initialize_crawlers(self):
        """Initialize crawlers for enabled platforms"""
        enabled_platforms = Config.get_enabled_platforms()
        
        for platform in enabled_platforms:
            try:
                if platform == "airbnb":
                    self.crawlers[platform] = AirbnbCrawler()
                elif platform == "booking":
                    self.crawlers[platform] = BookingCrawler()
                elif platform == "expedia":
                    self.crawlers[platform] = ExpediaCrawler()
                elif platform == "hotels":
                    self.crawlers[platform] = HotelsCrawler()
                elif platform == "tripadvisor":
                    self.crawlers[platform] = TripAdvisorCrawler()
                elif platform == "vrbo":
                    self.crawlers[platform] = VRBOCrawler()
                else:
                    self.logger.warning(f"No crawler implementation for platform: {platform}")
            except Exception as e:
                self.logger.error(f"Failed to initialize crawler for {platform}: {str(e)}")
        
        self.logger.info(f"Initialized {len(self.crawlers)} crawlers: {list(self.crawlers.keys())}")
    
    async def search_all_platforms(self, request: PriceRequest) -> List[SearchResult]:
        """Search all enabled platforms for the given request"""
        all_results = []
        
        # Convert dates to string format
        checkin_str = request.checkin_date.strftime('%Y-%m-%d')
        checkout_str = request.checkout_date.strftime('%Y-%m-%d')
        
        # Prepare search parameters
        search_params = {
            'hotel_name': request.hotel_name,
            'city': request.city,
            'checkin_date': checkin_str,
            'checkout_date': checkout_str,
            'guests': 1,  # Default to 1 guest
            'state': request.state,
            'country': request.country,
            'latitude': request.latitude,
            'longitude': request.longitude
        }
        
        self.logger.info(f"Starting search across {len(self.crawlers)} platforms")
        
        # Create tasks for all crawlers
        tasks = []
        for platform, crawler in self.crawlers.items():
            task = self._search_platform(platform, crawler, search_params)
            tasks.append(task)
        
        # Execute all searches concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                platform = list(self.crawlers.keys())[i]
                
                if isinstance(result, Exception):
                    self.logger.error(f"Error searching {platform}: {str(result)}")
                elif isinstance(result, list):
                    all_results.extend(result)
                    self.logger.info(f"Found {len(result)} results from {platform}")
                else:
                    self.logger.warning(f"Unexpected result type from {platform}: {type(result)}")
        
        self.logger.info(f"Total results found: {len(all_results)}")
        return all_results
    
    async def _search_platform(self, platform: str, crawler, search_params: Dict) -> List[SearchResult]:
        """Search a single platform"""
        try:
            async with crawler:
                results = await crawler.search_properties(**search_params)
                return results
        except Exception as e:
            self.logger.error(f"Error searching {platform}: {str(e)}")
            return []
    
    async def search_single_platform(self, platform: str, request: PriceRequest) -> List[SearchResult]:
        """Search a single platform"""
        if platform not in self.crawlers:
            self.logger.error(f"Platform {platform} not available or disabled")
            return []
        
        crawler = self.crawlers[platform]
        
        # Convert dates to string format
        checkin_str = request.checkin_date.strftime('%Y-%m-%d')
        checkout_str = request.checkout_date.strftime('%Y-%m-%d')
        
        # Prepare search parameters
        search_params = {
            'hotel_name': request.hotel_name,
            'city': request.city,
            'checkin_date': checkin_str,
            'checkout_date': checkout_str,
            'guests': 1,
            'state': request.state,
            'country': request.country,
            'latitude': request.latitude,
            'longitude': request.longitude
        }
        
        try:
            async with crawler:
                results = await crawler.search_properties(**search_params)
                self.logger.info(f"Found {len(results)} results from {platform}")
                return results
        except Exception as e:
            self.logger.error(f"Error searching {platform}: {str(e)}")
            return []
    
    def get_available_platforms(self) -> List[str]:
        """Get list of available and enabled platforms"""
        return list(self.crawlers.keys())
    
    def is_platform_enabled(self, platform: str) -> bool:
        """Check if a platform is enabled and available"""
        return platform in self.crawlers 