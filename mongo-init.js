// MongoDB initialization script
// This script runs when the MongoDB container starts for the first time

// Switch to the accomopricer database
db = db.getSiblingDB('accomopricer');

// Create the crawled_prices collection
db.createCollection('crawled_prices');

// Create indexes for efficient querying
db.crawled_prices.createIndex({
    "hotel_name": 1,
    "city": 1,
    "country": 1,
    "checkin_date": 1,
    "checkout_date": 1
}, { name: "search_criteria_index" });

// Create index for crawled_at for time-based queries
db.crawled_prices.createIndex({
    "crawled_at": -1
}, { name: "crawled_at_index" });

// Create index for job_id
db.crawled_prices.createIndex({
    "job_id": 1
}, { name: "job_id_index" });

// Create text index for hotel name searches
db.crawled_prices.createIndex({
    "hotel_name": "text",
    "city": "text"
}, { name: "text_search_index" });

print("MongoDB initialization completed successfully!");
print("Database: accomopricer");
print("Collection: crawled_prices");
print("Indexes created: search_criteria_index, crawled_at_index, job_id_index, text_search_index"); 