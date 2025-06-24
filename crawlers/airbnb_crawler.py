import asyncio
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urlencode
from bs4 import BeautifulSoup

from .base_crawler import BaseCrawler
from models import SearchResult

class AirbnbCrawler(BaseCrawler):
    """Airbnb crawler implementation"""
    
    def __init__(self):
        super().__init__("airbnb")
    
    async def search_properties(self, hotel_name: str, city: str, checkin_date: str, 
                              checkout_date: str, **kwargs) -> List[SearchResult]:
        """Search for properties on Airbnb"""
        results = []
        
        try:
            # Build search URL
            search_query = f"{hotel_name} {city}"
            encoded_query = quote_plus(search_query)
            
            # Airbnb search URL structure
            search_url = f"https://www.airbnb.com/s/{encoded_query}"
            
            # Add date parameters
            params = {
                'checkin': checkin_date,
                'checkout': checkout_date,
                'adults': kwargs.get('guests', 1),
                'children': 0,
                'infants': 0,
                'pets': 0
            }
            
            search_url += '?' + urlencode(params)
            
            self.logger.info(f"Searching Airbnb for: {search_query}")
            
            # Get search results page
            soup = await self.get_page_soup(search_url)
            if not soup:
                self.logger.warning("Failed to get Airbnb search page")
                return results
            
            # Extract property listings
            listings = soup.find_all('div', {'data-testid': 'card-container'})
            if not listings:
                # Try alternative selectors
                listings = soup.find_all('div', class_=re.compile(r'listing'))
            
            self.logger.info(f"Found {len(listings)} listings on Airbnb")
            
            for listing in listings[:Config.MAX_PRICE_RESULTS_PER_PLATFORM]:
                try:
                    result = await self._extract_listing_data(listing, search_url)
                    if result:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"Error extracting listing data: {str(e)}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error searching Airbnb: {str(e)}")
        
        return results
    
    async def _extract_listing_data(self, listing_element, base_url: str) -> Optional[SearchResult]:
        """Extract data from a single listing element"""
        try:
            # Extract property name
            name_elem = listing_element.find('div', {'data-testid': 'listing-card-name'})
            if not name_elem:
                name_elem = listing_element.find('h3') or listing_element.find('h2')
            
            property_name = self._clean_text(name_elem.get_text()) if name_elem else "Unknown Property"
            
            # Extract price
            price_elem = listing_element.find('span', {'data-testid': 'listing-card-price'})
            if not price_elem:
                price_elem = listing_element.find(class_=re.compile(r'price'))
            
            price_text = price_elem.get_text() if price_elem else ""
            price = self._extract_price(price_text)
            
            if not price:
                return None
            
            # Extract rating
            rating_elem = listing_element.find('span', {'data-testid': 'rating'})
            if not rating_elem:
                rating_elem = listing_element.find(class_=re.compile(r'rating'))
            
            rating_text = rating_elem.get_text() if rating_elem else ""
            rating = self._extract_rating(rating_text)
            
            # Extract review count
            review_elem = listing_element.find('span', {'data-testid': 'reviews'})
            if not review_elem:
                review_elem = listing_element.find(class_=re.compile(r'review'))
            
            review_text = review_elem.get_text() if review_elem else ""
            review_count = self._extract_review_count(review_text)
            
            # Extract URL
            link_elem = listing_element.find('a')
            url = None
            if link_elem and link_elem.get('href'):
                url = f"https://www.airbnb.com{link_elem['href']}"
            
            # Extract image
            img_elem = listing_element.find('img')
            image_url = img_elem.get('src') if img_elem else None
            
            # Extract amenities (basic)
            amenities = []
            amenity_elems = listing_element.find_all(class_=re.compile(r'amenity'))
            for amenity in amenity_elems:
                amenity_text = self._clean_text(amenity.get_text())
                if amenity_text:
                    amenities.append(amenity_text)
            
            return SearchResult(
                platform="airbnb",
                property_name=property_name,
                price=price,
                currency="USD",  # Airbnb typically shows USD
                availability=True,
                url=url,
                rating=rating,
                review_count=review_count,
                amenities=amenities if amenities else None,
                image_url=image_url
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting listing data: {str(e)}")
            return None 