from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn

# --- App Imports ---
from app.database.database import connect_to_mongo, close_mongo_connection
from app.database.crud import (
    create_hypothesis_analysis,
    get_all_hypotheses_summary,
    get_hypothesis_by_id
)
from app.pipeline.orchestrator import orchestrator, TradeSageOrchestrator

# --- Pydantic Models ---
# These models define the expected request and response data structures
# This is a good practice for API design.

class HypothesisRequest(BaseModel):
    """The input from the user."""
    hypothesis: str

class HypothesisSummary(BaseModel):
    """A lightweight summary for the dashboard."""
    _id: str
    processed_hypothesis: str
    confidence_score: float
    synthesis: Optional[str] = None
    created_at: Any # Will be a datetime object

class FullHypothesis(BaseModel):
    """The full, detailed analysis document."""
    _id: str
    status: str
    original_hypothesis: str
    processed_hypothesis: str
    context: Dict[str, Any]
    research_data: Dict[str, Any]
    contradictions: List[Dict[str, Any]]
    confirmations: List[Dict[str, Any]]
    synthesis: str
    alerts: List[Dict[str, Any]]
    confidence_score: float
    method: str
    created_at: Any

# --- FastAPI App ---

# We create the app instance
app = FastAPI(
    title="TradeSage API (Gemini + MongoDB)",
    description="A 6-step agent pipeline for financial hypothesis testing."
)

# --- Application Lifecycle Events ---

@app.on_event("startup")
async def startup_event():
    """Connects to MongoDB when the app starts."""
    connect_to_mongo()
    
    # Check if orchestrator initialized correctly
    if orchestrator is None:
        print("--- FATAL: ORCHESTRATOR FAILED TO INITIALIZE ---")
        # In a real app, you might want to force a shutdown
    else:
        print("Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    """Disconnects from MongoDB when the app shuts down."""
    close_mongo_connection()
    print("Application shutdown complete.")

# --- API Endpoints ---

@app.get("/health", tags=["Status"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "TradeSage API is running."}

@app.post("/process", response_model=FullHypothesis, tags=["Analysis"])
async def process_hypothesis(request: HypothesisRequest):
    """
    Submits a new hypothesis, runs the full 6-step analysis pipeline,
    and saves the result to the database.
    """
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator is not initialized.")

    try:
        # 1. Run the analysis
        # This is the main call to our 6-step pipeline
        analysis_data = await orchestrator.process_hypothesis(request.dict())
        
        if analysis_data.get("status") == "error":
            raise HTTPException(status_code=500, detail=analysis_data.get("error"))

        # 2. Save the full result to MongoDB
        # We don't await this, but in a production app you might
        new_id = await create_hypothesis_analysis(analysis_data)
        
        # 3. Add the new DB ID to the response and return it
        analysis_data["_id"] = new_id
        
        return analysis_data
        
    except Exception as e:
        print(f"--- Error in /process endpoint: {e} ---")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.get("/dashboard", response_model=List[HypothesisSummary], tags=["Analysis"])
async def get_dashboard_summary():
    """
    Gets the lightweight summary of all recent analyses
    for the main dashboard.
    """
    try:
        summaries = await get_all_hypotheses_summary()
        return summaries
    except Exception as e:
        print(f"--- Error in /dashboard endpoint: {e} ---")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/hypothesis/{hypothesis_id}", response_model=FullHypothesis, tags=["Analysis"])
async def get_full_hypothesis(hypothesis_id: str):
    """
    Gets a single, complete analysis by its unique ID.
    """
    try:
        analysis = await get_hypothesis_by_id(hypothesis_id)
        if analysis is None:
            raise HTTPException(status_code=404, detail="Hypothesis not found.")
        return analysis
    except Exception as e:
        print(f"--- Error in /hypothesis/{hypothesis_id} endpoint: {e} ---")
        raise HTTPException(status_code=500, detail=str(e))

# --- Main entrypoint to run the app ---
if __name__ == "__main__":
    """
    This allows you to run the app directly for testing:
    `python app/main.py`
    """
    print("Starting TradeSage API server...")
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True # Enables auto-reload for development
    )
