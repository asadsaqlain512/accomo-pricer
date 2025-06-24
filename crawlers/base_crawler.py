import asyncio
import aiohttp
import random
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
import logging
from fake_useragent import UserAgent

from config import Config
from models import SearchResult

class BaseCrawler(ABC):
    """Base class for all platform crawlers"""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.config = Config.get_platform_config(platform_name)
        self.session = None
        self.user_agent = UserAgent()
        self.logger = logging.getLogger(f"crawler.{platform_name}")
        
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=self._get_headers()
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with random user agent"""
        headers = {
            'User-Agent': random.choice(Config.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        return headers
    
    def _get_proxy(self) -> Optional[str]:
        """Get a random proxy if enabled"""
        if Config.USE_PROXIES and Config.PROXY_LIST:
            return random.choice(Config.PROXY_LIST)
        return None
    
    async def make_request(self, url: str, method: str = "GET", **kwargs) -> Optional[aiohttp.ClientResponse]:
        """Make HTTP request with retry logic"""
        max_retries = self.config.get("max_retries", 3)
        delay = self.config.get("delay_between_requests", 2)
        
        for attempt in range(max_retries):
            try:
                # Add delay between requests
                if attempt > 0:
                    await asyncio.sleep(delay)
                
                # Update headers for each request
                headers = self._get_headers()
                kwargs['headers'] = {**headers, **kwargs.get('headers', {})}
                
                # Add proxy if enabled
                proxy = self._get_proxy()
                if proxy:
                    kwargs['proxy'] = proxy
                
                self.logger.info(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        return response
                    elif response.status == 429:  # Rate limited
                        wait_time = (attempt + 1) * delay * 2
                        self.logger.warning(f"Rate limited, waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                    else:
                        self.logger.warning(f"Request failed with status {response.status}")
                        
            except Exception as e:
                self.logger.error(f"Request attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
        
        return None
    
    async def get_page_content(self, url: str, **kwargs) -> Optional[str]:
        """Get page content as text"""
        response = await self.make_request(url, **kwargs)
        if response:
            return await response.text()
        return None
    
    async def get_page_soup(self, url: str, **kwargs) -> Optional[BeautifulSoup]:
        """Get BeautifulSoup object from URL"""
        content = await self.get_page_content(url, **kwargs)
        if content:
            return BeautifulSoup(content, 'lxml')
        return None
    
    @abstractmethod
    async def search_properties(self, hotel_name: str, city: str, checkin_date: str, 
                              checkout_date: str, **kwargs) -> List[SearchResult]:
        """Search for properties on this platform"""
        pass
    
    def _extract_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        if not price_text:
            return None
        
        # Remove common currency symbols and non-numeric characters
        import re
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        if price_match:
            try:
                return float(price_match.group())
            except ValueError:
                pass
        return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        return " ".join(text.strip().split())
    
    def _extract_rating(self, rating_text: str) -> Optional[float]:
        """Extract rating from text"""
        if not rating_text:
            return None
        
        import re
        rating_match = re.search(r'(\d+\.?\d*)', rating_text)
        if rating_match:
            try:
                rating = float(rating_match.group(1))
                return min(max(rating, 0), 10)  # Ensure rating is between 0-10
            except ValueError:
                pass
        return None
    
    def _extract_review_count(self, review_text: str) -> Optional[int]:
        """Extract review count from text"""
        if not review_text:
            return None
        
        import re
        count_match = re.search(r'(\d+)', review_text.replace(',', ''))
        if count_match:
            try:
                return int(count_match.group(1))
            except ValueError:
                pass
        return None 