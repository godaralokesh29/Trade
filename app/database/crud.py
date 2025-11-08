from .database import get_hypotheses_collection
from typing import Dict, Any, List, Optional
from bson import ObjectId
from datetime import datetime

# Note: We don't need models.py because MongoDB is schemaless.
# Our "schema" is the JSON object returned by the orchestrator.


async def create_hypothesis_analysis(analysis_data: Dict[str, Any]) -> str:
    """
    Saves the *entire* analysis object from the orchestrator as one document.
    """
    collection = get_hypotheses_collection()
    if collection is None:
        raise Exception("Database not connected.")
        
    # Add a timestamp to the root of the document
    analysis_data["created_at"] = datetime.utcnow()
    
    # analysis_data is the full JSON object from the Gemini-powered orchestrator
    result = await collection.insert_one(analysis_data)
    
    # Return the string ID of the new document
    return str(result.inserted_id)

async def get_all_hypotheses_summary() -> List[Dict[str, Any]]:
    """
    Gets a lightweight summary for all hypotheses for the dashboard.
    This replaces the complex DashboardCRUD from the original.
    """
    collection = get_hypotheses_collection()
    if collection is None:
        raise Exception("Database not connected.")
        
    summaries = []
    
    # Find all documents, but only return specific fields (projection)
    # This keeps the dashboard payload small and fast.
    # We sort by -1 to get the newest ones first.
    cursor = collection.find(
        {}, 
        {
            "processed_hypothesis": 1, 
            "confidence_score": 1, 
            "synthesis": 1,
            "context.primary_symbol": 1, # Get nested symbol
            "created_at": 1
        }
    ).sort("created_at", -1).limit(50) # Get last 50
    
    async for doc in cursor:
        doc["_id"] = str(doc["_id"]) # Convert Mongo's ObjectId to a string
        summaries.append(doc)
        
    return summaries

async def get_hypothesis_by_id(hypothesis_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a single, complete analysis document by its Mongo ID.
    """
    collection = get_hypotheses_collection()
    if collection is None:
        raise Exception("Database not connected.")
        
    try:
        # Convert the string ID back to a BSON ObjectId for querying
        oid = ObjectId(hypothesis_id)
    except Exception:
        print(f"Invalid ID format: {hypothesis_id}")
        return None
        
    doc = await collection.find_one({"_id": oid})
    
    if doc:
        # Convert _id to string for JSON responses
        doc["_id"] = str(doc["_id"]) 
    
    return doc