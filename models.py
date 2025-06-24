from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import date, datetime
import uuid

class PriceRequest(BaseModel):
    """Model for price search request"""
    hotel_name: str = Field(..., description="Name of the hotel/property")
    checkin_date: date = Field(..., description="Check-in date (YYYY-MM-DD)")
    checkout_date: date = Field(..., description="Check-out date (YYYY-MM-DD)")
    city: str = Field(..., description="City name")
    state: Optional[str] = Field(None, description="State/province (optional)")
    country: str = Field(..., description="Country name")
    latitude: Optional[float] = Field(None, description="Latitude coordinate (optional)")
    longitude: Optional[float] = Field(None, description="Longitude coordinate (optional)")
    
    @validator('checkout_date')
    def checkout_after_checkin(cls, v, values):
        if 'checkin_date' in values and v <= values['checkin_date']:
            raise ValueError('Checkout date must be after checkin date')
        return v
    
    @validator('latitude')
    def validate_latitude(cls, v):
        if v is not None and (v < -90 or v > 90):
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @validator('longitude')
    def validate_longitude(cls, v):
        if v is not None and (v < -180 or v > 180):
            raise ValueError('Longitude must be between -180 and 180')
        return v

class PriceData(BaseModel):
    """Model for price data from a platform"""
    currency: str = Field(default="USD", description="Currency code")
    amount: float = Field(..., description="Price amount")
    availability: bool = Field(default=True, description="Availability status")
    timestamp: datetime = Field(default_factory=datetime.now, description="When price was fetched")
    platform_specific_data: Optional[Dict[str, Any]] = Field(None, description="Platform-specific data")

class PriceMessage(BaseModel):
    """Model for WebSocket price message"""
    group_id: str = Field(..., description="Unique job identifier")
    property_title: str = Field(..., description="Hotel/property name")
    city: str = Field(..., description="City name")
    state: Optional[str] = Field(None, description="State/province")
    country: str = Field(..., description="Country name")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    platform: str = Field(..., description="Source platform name")
    price_data: PriceData = Field(..., description="Price information")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class JobStatus(BaseModel):
    """Model for job status response"""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status (pending, running, completed, failed)")
    progress: float = Field(..., description="Progress percentage (0-100)")
    total_platforms: int = Field(..., description="Total number of platforms to check")
    completed_platforms: int = Field(..., description="Number of completed platforms")
    created_at: datetime = Field(default_factory=datetime.now, description="Job creation time")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")

class SearchResult(BaseModel):
    """Model for search result from a platform"""
    platform: str = Field(..., description="Platform name")
    property_name: str = Field(..., description="Property name found")
    price: float = Field(..., description="Price amount")
    currency: str = Field(default="USD", description="Currency")
    availability: bool = Field(default=True, description="Availability")
    url: Optional[str] = Field(None, description="Direct URL to property")
    rating: Optional[float] = Field(None, description="Property rating")
    review_count: Optional[int] = Field(None, description="Number of reviews")
    amenities: Optional[List[str]] = Field(None, description="Available amenities")
    image_url: Optional[str] = Field(None, description="Property image URL")
    fetched_at: datetime = Field(default_factory=datetime.now, description="When data was fetched")

class JobResult(BaseModel):
    """Model for complete job result"""
    job_id: str = Field(..., description="Job identifier")
    search_criteria: PriceRequest = Field(..., description="Original search criteria")
    results: List[SearchResult] = Field(..., description="All search results")
    total_results: int = Field(..., description="Total number of results")
    completed_at: datetime = Field(default_factory=datetime.now, description="Job completion time")
    execution_time: float = Field(..., description="Total execution time in seconds")

class CrawledPriceRecord(BaseModel):
    """Model for storing crawled prices in MongoDB"""
    hotel_name: str = Field(..., description="Hotel name")
    city: str = Field(..., description="City name")
    country: str = Field(..., description="Country name")
    checkin_date: date = Field(..., description="Check-in date")
    checkout_date: date = Field(..., description="Check-out date")
    state: Optional[str] = Field(None, description="State/province")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    platform_prices: Dict[str, List[SearchResult]] = Field(..., description="Prices from each platform")
    total_results: int = Field(..., description="Total number of results")
    crawled_at: datetime = Field(default_factory=datetime.now, description="When data was crawled")
    job_id: str = Field(..., description="Job identifier")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }

class CacheKey(BaseModel):
    """Model for generating cache keys"""
    hotel_name: str
    city: str
    country: str
    checkin_date: date
    checkout_date: date
    state: Optional[str] = None
    
    def to_key(self) -> str:
        """Generate a unique cache key"""
        state_part = f":{self.state}" if self.state else ""
        return f"prices:{self.hotel_name}:{self.city}:{self.country}:{self.checkin_date}:{self.checkout_date}{state_part}"

def generate_job_id() -> str:
    """Generate a unique job ID"""
    return str(uuid.uuid4()) 