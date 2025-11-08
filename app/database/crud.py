from .database import get_hypotheses_collection
from typing import Dict, Any, List, Optional
from bson import ObjectId
from datetime import datetime

# Note: We don't need models.py because MongoDB is schemaless.
# Our "schema" is the JSON object returned by the orchestrator.

# REMOVED 'async'
def create_hypothesis_analysis(analysis_data: Dict[str, Any]) -> str:
    """
    Saves the *entire* analysis object from the orchestrator as one document.
    """
    collection = get_hypotheses_collection()
    if collection is None:
        raise Exception("Database not connected.")
        
    # Add a timestamp to the root of the document
    analysis_data["created_at"] = datetime.utcnow()
    
    # REMOVED 'await'
    result = collection.insert_one(analysis_data)
    
    # Return the string ID of the new document
    return str(result.inserted_id)

# REMOVED 'async'
def get_all_hypotheses_summary() -> List[Dict[str, Any]]:
    """
    Gets a lightweight summary for all hypotheses for the dashboard.
    This replaces the complex DashboardCRUD from the original.
    """
    collection = get_hypotheses_collection()
    if collection is None:
        raise Exception("Database not connected.")
        
    summaries = []
    
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
    
    # REMOVED 'async for'
    for doc in cursor:
        doc["_id"] = str(doc["_id"]) # Convert Mongo's ObjectId to a string
        summaries.append(doc)
        
    return summaries

# REMOVED 'async'
def get_hypothesis_by_id(hypothesis_id: str) -> Optional[Dict[str, Any]]:
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
        
    # REMOVED 'await'
    doc = collection.find_one({"_id": oid})
    
    if doc:
        # Convert _id to string for JSON responses
        doc["_id"] = str(doc["_id"]) 
    
    return doc
