import os
import requests
from typing import Dict, Any
import asyncio
from app.core.config import ALPHA_VANTAGE_API_KEY

BASE_URL = "https://www.alphavantage.co/query"

async def fetch_market_research(symbol: str) -> Dict[str, Any]:
    """
    Fetches key market data (price and overview) for a given stock symbol
    using the Alpha Vantage API. Uses asyncio.run_in_executor to handle
    the blocking 'requests' calls safely in the async environment.
    """
    if not ALPHA_VANTAGE_API_KEY:
        print("ERROR: ALPHA_VANTAGE_API_KEY not set.")
        return get_fallback_data(symbol)

    # Use the event loop to run the synchronous network calls in a thread pool
    loop = asyncio.get_event_loop()
    
    # We call two APIs for comprehensive data: Global Quote (price) and Company Overview (summary)
    price_future = loop.run_in_executor(None, get_global_quote, symbol)
    overview_future = loop.run_in_executor(None, get_company_overview, symbol)
    
    # Wait for both network calls to complete
    price_data, overview_data = await asyncio.gather(price_future, overview_future)
    
    # Combine the results
    combined_data = {
        "symbol": symbol,
        # Global Quote fields
        "price": price_data.get('05. price', 'N/A'),
        "volume": price_data.get('06. volume', 'N/A'),
        "week_high": price_data.get('03. high', 'N/A'),
        "week_low": price_data.get('04. low', 'N/A'),
        # Company Overview fields
        "overview": overview_data.get('Description', 'No detailed overview available.'),
        "fifty_day_moving_average": overview_data.get('50DayMovingAverage', 'N/A'),
        "source": "Alpha Vantage"
    }
    
    # Simple check for failure
    if combined_data['price'] == 'N/A' and combined_data['overview'].startswith("No detailed"):
        print(f"WARNING: Alpha Vantage failed to return data for {symbol}. Returning fallback.")
        return get_fallback_data(symbol)
        
    return combined_data

def get_global_quote(symbol: str) -> Dict[str, str]:
    """Synchronous call for current price and volume."""
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY
    }
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("Global Quote", {})
    except Exception as e:
        print(f"Error fetching Global Quote for {symbol}: {e}")
        return {}

def get_company_overview(symbol: str) -> Dict[str, str]:
    """Synchronous call for company summary and technical metrics."""
    params = {
        "function": "OVERVIEW",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY
    }
    try:
        # NOTE: Sleep briefly to comply with Alpha Vantage API rate limits (5 calls/min on free tier)
        import time
        time.sleep(1) 
        
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching Company Overview for {symbol}: {e}")
        return {}

def get_fallback_data(symbol: str) -> Dict[str, Any]:
    """Returns placeholder data if the API call fails."""
    return {
        "symbol": symbol,
        "price": "N/A",
        "volume": "N/A",
        "overview": "Financial data could not be retrieved due to API limits or a bad symbol.",
        "fifty_day_moving_average": "N/A",
        "week_high": "N/A",
        "week_low": "N/A",
        "source": "SIMULATED FALLBACK"
    }