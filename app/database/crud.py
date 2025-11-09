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
            "contradictions": 1,
            "confirmations": 1,
            "status": 1,
            "context.primary_symbol": 1, # Get nested symbol
            "created_at": 1
        }
    ).sort("created_at", -1).limit(50) # Get last 50
    
    # REMOVED 'async for'
    for doc in cursor:
        doc["_id"] = str(doc["_id"]) # Convert Mongo's ObjectId to a string
        
        # Transform data for frontend compatibility
        # Convert confidence_score (0-1) to confidence percentage (0-100)
        if "confidence_score" in doc and doc["confidence_score"] is not None:
            doc["confidence"] = round(doc["confidence_score"] * 100)
        else:
            doc["confidence"] = 50  # Default to 50%
        
        # Count contradictions and confirmations
        contradictions_list = doc.get("contradictions", [])
        confirmations_list = doc.get("confirmations", [])
        
        doc["contradictions"] = len(contradictions_list) if isinstance(contradictions_list, list) else 0
        doc["confirmations"] = len(confirmations_list) if isinstance(confirmations_list, list) else 0
        
        # Add detail arrays for frontend
        doc["contradictions_detail"] = contradictions_list if isinstance(contradictions_list, list) else []
        doc["confirmations_detail"] = confirmations_list if isinstance(confirmations_list, list) else []
        
        # Add title and id for frontend
        doc["id"] = doc["_id"]
        doc["title"] = doc.get("processed_hypothesis", "Untitled Hypothesis")
        
        # Format lastUpdated
        if "created_at" in doc and doc["created_at"]:
            if isinstance(doc["created_at"], datetime):
                doc["lastUpdated"] = doc["created_at"].strftime("%Y-%m-%d %H:%M")
            else:
                doc["lastUpdated"] = "Recently"
        else:
            doc["lastUpdated"] = "Recently"
        
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
