from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from app.core.config import MONGO_CONNECTION_STRING, MONGO_DB_NAME

# This class will hold our database connection (as a singleton)
class MongoConnection:
    client: MongoClient = None
    db: Database = None
    
    # Collections
    hypotheses: Collection = None

db_connection = MongoConnection()

def connect_to_mongo():
    """
    Connects to the MongoDB database and initializes collections.
    This function should be called once at application startup.
    """
    print("Connecting to MongoDB...")
    try:
        db_connection.client = MongoClient(MONGO_CONNECTION_STRING)
        db_connection.db = db_connection.client[MONGO_DB_NAME]
        
        # Get collections
        db_connection.hypotheses = db_connection.db["hypotheses"]
        
        # Verify connection
        db_connection.client.admin.command('ping')
        print(f"Successfully connected to MongoDB, database: '{MONGO_DB_NAME}'.")
        
    except Exception as e:
        print(f"--- FAILED TO CONNECT TO MONGODB ---")
        print(f"Error: {e}")
        print("Please check your MONGO_CONNECTION_STRING in the .env file.")
        # We'll let the app exit or fail gracefully at startup
        raise

def close_mongo_connection():
    """Closes the MongoDB connection. Call this at application shutdown."""
    if db_connection.client:
        db_connection.client.close()
        print("MongoDB connection closed.")

def get_db() -> Database:
    """Helper function to get the database instance."""
    return db_connection.db

def get_hypotheses_collection() -> Collection:
    """Helper function to get the main 'hypotheses' collection."""
    return db_connection.hypotheses