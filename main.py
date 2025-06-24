import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import Config
from models import PriceRequest, SearchResult, JobStatus, JobResult, PriceMessage, PriceData
from crawler_manager import CrawlerManager
from database import get_db_service, DatabaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
crawler_manager = None
db_service: Optional[DatabaseService] = None
active_connections: List[WebSocket] = []
active_jobs: Dict[str, Dict] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global crawler_manager, db_service
    
    # Startup
    logger.info("Starting Accommodation Price Crawler...")
    crawler_manager = CrawlerManager()
    db_service = get_db_service()
    logger.info("Crawler manager and database service initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Accommodation Price Crawler...")
    # Close all active WebSocket connections
    for connection in active_connections:
        try:
            await connection.close()
        except:
            pass
    
    # Close database connections
    if db_service:
        db_service.close_connections()

# Create FastAPI app
app = FastAPI(
    title="Accommodation Price Crawler",
    description="Real-time accommodation price crawling system with MongoDB storage and Redis caching",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Accommodation Price Crawler API",
        "version": "1.0.0",
        "status": "running",
        "features": ["MongoDB storage", "Redis caching", "Real-time WebSocket updates"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_connections": len(active_connections),
        "active_jobs": len(active_jobs),
        "database": "connected" if db_service else "disconnected"
    }

@app.get("/platforms")
async def get_platforms():
    """Get list of available platforms"""
    if not crawler_manager:
        raise HTTPException(status_code=503, detail="Crawler manager not initialized")
    
    platforms = crawler_manager.get_available_platforms()
    return {
        "platforms": platforms,
        "total": len(platforms)
    }

@app.post("/search")
async def search_properties(request: PriceRequest, background_tasks: BackgroundTasks):
    """Search for properties across all enabled platforms with caching"""
    if not crawler_manager:
        raise HTTPException(status_code=503, detail="Crawler manager not initialized")
    
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")
    
    # Check cache first
    cached_result = await db_service.get_cached_prices(
        hotel_name=request.hotel_name,
        city=request.city,
        country=request.country,
        checkin_date=request.checkin_date,
        checkout_date=request.checkout_date,
        state=request.state
    )
    
    if cached_result:
        logger.info(f"Returning cached results for {request.hotel_name} in {request.city}")
        return {
            "job_id": "cached",
            "message": "Results retrieved from cache",
            "status": "completed",
            "cached": True,
            "cached_at": cached_result.crawled_at.isoformat(),
            "total_results": cached_result.total_results
        }
    
    # Generate job ID
    job_id = generate_job_id()
    
    # Initialize job status
    active_jobs[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "total_platforms": len(crawler_manager.get_available_platforms()),
        "completed_platforms": 0,
        "results": [],
        "created_at": datetime.now(),
        "request": request
    }
    
    # Start background search
    background_tasks.add_task(run_search_job, job_id, request)
    
    return {
        "job_id": job_id,
        "message": "Search job started",
        "status": "pending",
        "cached": False
    }

@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific job"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = active_jobs[job_id]
    
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        total_platforms=job["total_platforms"],
        completed_platforms=job["completed_platforms"],
        created_at=job["created_at"]
    )

@app.get("/job/{job_id}/results")
async def get_job_results(job_id: str):
    """Get results of a completed job"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = active_jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    return JobResult(
        job_id=job_id,
        search_criteria=job["request"],
        results=job["results"],
        total_results=len(job["results"]),
        completed_at=job.get("completed_at", datetime.now()),
        execution_time=job.get("execution_time", 0.0)
    )

@app.get("/prices/{hotel_name}")
async def get_stored_prices(hotel_name: str, city: str, country: str, 
                          checkin_date: str, checkout_date: str, state: Optional[str] = None):
    """Get stored prices for a specific hotel and criteria"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not initialized")
    
    try:
        from datetime import datetime
        checkin = datetime.strptime(checkin_date, "%Y-%m-%d").date()
        checkout = datetime.strptime(checkout_date, "%Y-%m-%d").date()
        
        # Try cache first
        cached_result = await db_service.get_cached_prices(
            hotel_name=hotel_name,
            city=city,
            country=country,
            checkin_date=checkin,
            checkout_date=checkout,
            state=state
        )
        
        if cached_result:
            return {
                "source": "cache",
                "data": cached_result.dict(),
                "cached_at": cached_result.crawled_at.isoformat()
            }
        
        # Try MongoDB
        mongo_result = await db_service.get_prices_from_mongodb(
            hotel_name=hotel_name,
            city=city,
            country=country,
            checkin_date=checkin,
            checkout_date=checkout,
            state=state
        )
        
        if mongo_result:
            return {
                "source": "mongodb",
                "data": mongo_result.dict(),
                "cached_at": mongo_result.crawled_at.isoformat()
            }
        
        raise HTTPException(status_code=404, detail="No prices found for the specified criteria")
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Error retrieving stored prices: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time price updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_text(json.dumps({
            "type": "connection",
            "job_id": job_id,
            "message": "Connected to price crawler"
        }))
        
        # Monitor job progress
        while True:
            if job_id in active_jobs:
                job = active_jobs[job_id]
                
                # Send job status updates
                status_message = {
                    "type": "status",
                    "job_id": job_id,
                    "status": job["status"],
                    "progress": job["progress"],
                    "completed_platforms": job["completed_platforms"],
                    "total_platforms": job["total_platforms"]
                }
                await websocket.send_text(json.dumps(status_message))
                
                # If job is completed, send final results and close
                if job["status"] == "completed":
                    await websocket.send_text(json.dumps({
                        "type": "completed",
                        "job_id": job_id,
                        "total_results": len(job["results"])
                    }))
                    break
                elif job["status"] == "failed":
                    await websocket.send_text(json.dumps({
                        "type": "failed",
                        "job_id": job_id,
                        "error": job.get("error", "Unknown error")
                    }))
                    break
            
            await asyncio.sleep(1)  # Check every second
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {str(e)}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)

async def run_search_job(job_id: str, request: PriceRequest):
    """Run search job in background with database storage"""
    start_time = datetime.now()
    
    try:
        # Update job status to running
        active_jobs[job_id]["status"] = "running"
        
        # Get all results from all platforms
        all_results = await crawler_manager.search_all_platforms(request)
        
        # Save results to database and cache
        if db_service:
            save_success = await db_service.save_search_results(
                hotel_name=request.hotel_name,
                city=request.city,
                country=request.country,
                checkin_date=request.checkin_date,
                checkout_date=request.checkout_date,
                state=request.state,
                latitude=request.latitude,
                longitude=request.longitude,
                job_id=job_id,
                results=all_results
            )
            
            if not save_success:
                logger.warning(f"Failed to save results for job {job_id}")
        
        # Update job with results
        active_jobs[job_id]["results"] = all_results
        active_jobs[job_id]["status"] = "completed"
        active_jobs[job_id]["progress"] = 100.0
        active_jobs[job_id]["completed_platforms"] = len(crawler_manager.get_available_platforms())
        active_jobs[job_id]["completed_at"] = datetime.now()
        active_jobs[job_id]["execution_time"] = (datetime.now() - start_time).total_seconds()
        
        # Send results to WebSocket connections
        await send_results_to_websockets(job_id, all_results)
        
        logger.info(f"Job {job_id} completed with {len(all_results)} results")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        active_jobs[job_id]["status"] = "failed"
        active_jobs[job_id]["error"] = str(e)
        active_jobs[job_id]["execution_time"] = (datetime.now() - start_time).total_seconds()

async def send_results_to_websockets(job_id: str, results: List[SearchResult]):
    """Send results to all connected WebSocket clients"""
    if job_id not in active_jobs:
        return
    
    job = active_jobs[job_id]
    request = job["request"]
    
    # Send each result as a separate message
    for result in results:
        price_message = PriceMessage(
            group_id=job_id,
            property_title=result.property_name,
            city=request.city,
            state=request.state,
            country=request.country,
            latitude=request.latitude,
            longitude=request.longitude,
            platform=result.platform,
            price_data=PriceData(
                currency=result.currency,
                amount=result.price,
                availability=result.availability,
                timestamp=result.fetched_at
            )
        )
        
        # Send to all active connections
        message_data = price_message.dict()
        message_data["type"] = "price_update"
        
        for connection in active_connections:
            try:
                await connection.send_text(json.dumps(message_data))
            except Exception as e:
                logger.error(f"Failed to send message to WebSocket: {str(e)}")

def generate_job_id() -> str:
    """Generate a unique job ID"""
    import uuid
    return str(uuid.uuid4())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=Config.DEBUG
    ) 