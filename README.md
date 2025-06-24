# Accommodation Price Crawler

A real-time accommodation price crawling system built with FastAPI and Python. This application fetches prices from multiple accommodation platforms, stores them in MongoDB, caches results in Redis, and streams results via WebSocket.

## Features

- **Multi-Platform Support**: Crawls Airbnb, Booking.com, Expedia, Hotels.com, TripAdvisor, and VRBO
- **Real-Time Streaming**: WebSocket-based real-time price updates
- **MongoDB Storage**: Persistent storage of all crawled prices with efficient indexing
- **Redis Caching**: Configurable caching with TTL for fast repeated queries
- **Configurable Platforms**: Enable/disable platforms via configuration
- **REST API**: Standard REST endpoints for job management and data retrieval
- **Async Processing**: Concurrent crawling across all platforms
- **Proxy Support**: Optional proxy rotation for production use

## Quick Start

### 1. Install Dependencies

```bash
cd accomopricer
pip install -r requirements.txt
```

### 2. Setup Databases

#### MongoDB
```bash
# Install MongoDB (Ubuntu/Debian)
sudo apt-get install mongodb

# Start MongoDB service
sudo systemctl start mongodb
sudo systemctl enable mongodb
```

#### Redis
```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Start Redis service
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 3. Configure Environment

Copy the example environment file and configure your settings:
```bash
cp env.example .env
# Edit .env with your database settings
```

### 4. Run the Application

```bash
# Simple way to run
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access the API

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Available Platforms**: http://localhost:8000/platforms

## API Usage

### 1. Start a Search Job (with Caching)

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_name": "Marriott Hotel",
    "checkin_date": "2024-02-01",
    "checkout_date": "2024-02-03",
    "city": "New York",
    "state": "NY",
    "country": "USA",
    "latitude": 40.7128,
    "longitude": -74.0060
  }'
```

Response (if cached):
```json
{
  "job_id": "cached",
  "message": "Results retrieved from cache",
  "status": "completed",
  "cached": true,
  "cached_at": "2024-01-01T12:00:00Z",
  "total_results": 15
}
```

Response (if not cached):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Search job started",
  "status": "pending",
  "cached": false
}
```

### 2. Get Stored Prices

```bash
curl "http://localhost:8000/prices/Marriott%20Hotel?city=New%20York&country=USA&checkin_date=2024-02-01&checkout_date=2024-02-03&state=NY"
```

Response:
```json
{
  "source": "cache",
  "data": {
    "hotel_name": "Marriott Hotel",
    "city": "New York",
    "country": "USA",
    "checkin_date": "2024-02-01",
    "checkout_date": "2024-02-03",
    "state": "NY",
    "platform_prices": {
      "airbnb": [...],
      "booking": [...],
      "expedia": [...]
    },
    "total_results": 15,
    "crawled_at": "2024-01-01T12:00:00Z",
    "job_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "cached_at": "2024-01-01T12:00:00Z"
}
```

### 3. Check Job Status

```bash
curl "http://localhost:8000/job/550e8400-e29b-41d4-a716-446655440000"
```

### 4. Get Job Results

```bash
curl "http://localhost:8000/job/550e8400-e29b-41d4-a716-446655440000/results"
```

### 5. WebSocket Connection

Connect to WebSocket for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/550e8400-e29b-41d4-a716-446655440000');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
    
    if (data.type === 'price_update') {
        console.log(`Price from ${data.platform}: $${data.price_data.amount}`);
    }
};
```

## Configuration

Edit `config.py` or set environment variables to customize the application:

### MongoDB Settings

```python
# Environment variables
MONGODB_URI = "mongodb://localhost:27017/"
MONGODB_DATABASE = "accomopricer"
MONGODB_COLLECTION = "crawled_prices"
```

### Redis Cache Settings

```python
# Environment variables
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None
CACHE_TTL = 3600  # 1 hour default
```

### Enable/Disable Platforms

```python
PLATFORMS = {
    "airbnb": {
        "enabled": True,  # Set to False to disable
        "base_url": "https://www.airbnb.com",
        "delay_between_requests": 2,
        "max_retries": 3
    },
    "booking": {
        "enabled": True,
        # ... other settings
    },
    # ... other platforms
}
```

### Proxy Configuration

```python
USE_PROXIES = False  # Set to True to enable proxy rotation
PROXY_LIST = [
    "http://proxy1:port",
    "http://proxy2:port",
]
```

### Request Settings

```python
REQUEST_TIMEOUT = 30  # Request timeout in seconds
MAX_CONCURRENT_REQUESTS = 5  # Max concurrent requests per platform
MAX_PRICE_RESULTS_PER_PLATFORM = 10  # Max results per platform
```

## Project Structure

```
accomopricer/
├── main.py                 # FastAPI application with caching
├── config.py              # Configuration settings
├── models.py              # Pydantic data models
├── database.py            # MongoDB and Redis service
├── crawler_manager.py     # Manages all crawlers
├── requirements.txt       # Python dependencies
├── env.example           # Environment variables template
├── README.md             # This file
└── crawlers/             # Platform-specific crawlers
    ├── __init__.py
    ├── base_crawler.py   # Base crawler class
    ├── airbnb_crawler.py
    ├── booking_crawler.py
    ├── expedia_crawler.py
    ├── hotels_crawler.py
    ├── tripadvisor_crawler.py
    └── vrbo_crawler.py
```

## Data Storage

### MongoDB Collection: `crawled_prices`

Each document contains:
- **Search Criteria**: hotel_name, city, country, checkin_date, checkout_date, state
- **Location Data**: latitude, longitude
- **Platform Prices**: Grouped results from each platform
- **Metadata**: total_results, crawled_at, job_id

### Redis Cache

- **Cache Keys**: `prices:{hotel_name}:{city}:{country}:{checkin_date}:{checkout_date}:{state}`
- **TTL**: Configurable (default: 1 hour)
- **Data**: Serialized CrawledPriceRecord objects

## WebSocket Message Format

### Price Update Message

```json
{
  "type": "price_update",
  "group_id": "job-uuid",
  "property_title": "Hotel Name",
  "city": "New York",
  "state": "NY",
  "country": "USA",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "platform": "airbnb",
  "price_data": {
    "currency": "USD",
    "amount": 150.00,
    "availability": true,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### Status Update Message

```json
{
  "type": "status",
  "job_id": "job-uuid",
  "status": "running",
  "progress": 50.0,
  "completed_platforms": 3,
  "total_platforms": 6
}
```

## Error Handling

The application includes comprehensive error handling:

- **Network Errors**: Automatic retry with exponential backoff
- **Rate Limiting**: Intelligent delays between requests
- **Invalid Data**: Graceful handling of malformed responses
- **Database Errors**: Fallback mechanisms for MongoDB/Redis failures
- **Platform Failures**: Individual platform failures don't stop the entire job

## Development

### Adding a New Platform

1. Create a new crawler file in `crawlers/` directory
2. Inherit from `BaseCrawler`
3. Implement the `search_properties` method
4. Add the crawler to `CrawlerManager._initialize_crawlers()`
5. Update the platform configuration in `config.py`

Example:
```python
class NewPlatformCrawler(BaseCrawler):
    def __init__(self):
        super().__init__("newplatform")
    
    async def search_properties(self, hotel_name, city, checkin_date, checkout_date, **kwargs):
        # Implementation here
        pass
```

### Testing

```bash
# Run with debug mode
python main.py

# Test with curl
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"hotel_name": "Test Hotel", "checkin_date": "2024-02-01", "checkout_date": "2024-02-03", "city": "Test City", "country": "Test Country"}'
```

## Production Deployment

For production deployment:

1. **Enable Proxies**: Set `USE_PROXIES = True` and configure proxy list
2. **Adjust Delays**: Increase `delay_between_requests` to avoid rate limiting
3. **Configure Databases**: Set up MongoDB and Redis with proper authentication
4. **Use Process Manager**: Use PM2, Supervisor, or systemd
5. **Load Balancing**: Use nginx or similar for load balancing
6. **Monitoring**: Add logging and monitoring
7. **Backup**: Set up MongoDB backups for data persistence

## Troubleshooting

### Common Issues

1. **No Results**: Check if platforms are enabled in config
2. **Rate Limiting**: Increase delays between requests
3. **Connection Errors**: Check network connectivity and proxy settings
4. **Database Errors**: Verify MongoDB and Redis connections
5. **Cache Issues**: Check Redis connectivity and TTL settings
6. **WebSocket Issues**: Ensure WebSocket connections are properly closed

### Logs

The application logs to console with detailed information about:
- Crawler initialization
- Request attempts and failures
- Job progress and completion
- WebSocket connections
- Database operations
- Cache hits/misses

## License

This project is for educational and development purposes. Please respect the terms of service of the platforms being crawled.

## Support

For issues and questions:
1. Check the logs for error messages
2. Verify configuration settings
3. Test with a simple search request
4. Check platform availability and rate limits
5. Verify database connections 