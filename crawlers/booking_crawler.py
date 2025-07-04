import asyncio
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urlencode
from bs4 import BeautifulSoup

from .base_crawler import BaseCrawler
from models import SearchResult

class BookingCrawler(BaseCrawler):
    """Booking.com crawler implementation"""
    
    def __init__(self):
        super().__init__("booking")
    
    async def search_properties(self, hotel_name: str, city: str, checkin_date: str, 
                              checkout_date: str, **kwargs) -> List[SearchResult]:
        """Search for properties on Booking.com"""
        results = []
        
        try:
            # Build search URL
            search_query = f"{hotel_name} {city}"
            encoded_query = quote_plus(search_query)
            
            # Booking.com search URL structure
            search_url = "https://www.booking.com/search.html"
            
            # Add search parameters
            params = {
                'ss': search_query,
                'checkin': checkin_date,
                'checkout': checkout_date,
                'group_adults': kwargs.get('guests', 1),
                'group_children': 0,
                'no_rooms': 1,
                'selected_currency': 'USD'
            }
            
            search_url += '?' + urlencode(params)
            
            self.logger.info(f"Searching Booking.com for: {search_query}")
            
            # Get search results page
            soup = await self.get_page_soup(search_url)
            if not soup:
                self.logger.warning("Failed to get Booking.com search page")
                return results
            
            # Extract property listings
            listings = soup.find_all('div', {'data-testid': 'property-card'})
            if not listings:
                # Try alternative selectors
                listings = soup.find_all('div', class_=re.compile(r'property-card'))
            
            self.logger.info(f"Found {len(listings)} listings on Booking.com")
            
            for listing in listings[:Config.MAX_PRICE_RESULTS_PER_PLATFORM]:
                try:
                    result = await self._extract_listing_data(listing, search_url)
                    if result:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"Error extracting listing data: {str(e)}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error searching Booking.com: {str(e)}")
        
        return results
    
    async def _extract_listing_data(self, listing_element, base_url: str) -> Optional[SearchResult]:
        """Extract data from a single listing element"""
        try:
            # Extract property name
            name_elem = listing_element.find('div', {'data-testid': 'title'})
            if not name_elem:
                name_elem = listing_element.find('h3') or listing_element.find('h2')
            
            property_name = self._clean_text(name_elem.get_text()) if name_elem else "Unknown Property"
            
            # Extract price
            price_elem = listing_element.find('span', {'data-testid': 'price-and-discounted-price'})
            if not price_elem:
                price_elem = listing_element.find(class_=re.compile(r'price'))
            
            price_text = price_elem.get_text() if price_elem else ""
            price = self._extract_price(price_text)
            
            if not price:
                return None
            
            # Extract rating
            rating_elem = listing_element.find('div', {'data-testid': 'review-score'})
            if not rating_elem:
                rating_elem = listing_element.find(class_=re.compile(r'score'))
            
            rating_text = rating_elem.get_text() if rating_elem else ""
            rating = self._extract_rating(rating_text)
            
            # Extract review count
            review_elem = listing_element.find('div', {'data-testid': 'review-score'})
            if not review_elem:
                review_elem = listing_element.find(class_=re.compile(r'review'))
            
            review_text = review_elem.get_text() if review_elem else ""
            review_count = self._extract_review_count(review_text)
            
            # Extract URL
            link_elem = listing_element.find('a')
            url = None
            if link_elem and link_elem.get('href'):
                url = f"https://www.booking.com{link_elem['href']}"
            
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
                platform="booking",
                property_name=property_name,
                price=price,
                currency="USD",  # Booking.com typically shows USD
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