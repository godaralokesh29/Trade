import json
import re
from typing import Dict, Any, List

def extract_response(response: str) -> str:
    """Extract clean response text."""
    if not response:
        return ""
    
    # Clean up common artifacts
    cleaned = response.strip()
    
    # Remove common prefixes
    prefixes_to_remove = [
        "Here's the processed hypothesis:",
        "Here is the processed hypothesis:",
        "Processed hypothesis:",
        "The processed hypothesis is:",
        "Analysis:",
        "Response:",
        "Output:",
    ]
    
    for prefix in prefixes_to_remove:
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix):].strip()
            break
    
    # Remove quotes if the entire response is quoted
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1].strip()
    
    return cleaned

def parse_json_response(response: str) -> Dict[str, Any]:
    """Parse JSON response from agent, with fallbacks."""
    if not response:
        return get_fallback_context()
    
    try:
        # Method 1: Direct JSON parsing if response starts with {
        cleaned_response = response.strip()
        
        # Remove markdown backticks
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
            
        cleaned_response = cleaned_response.strip()
            
        if cleaned_response.startswith('{'):
            return json.loads(cleaned_response)
        
        # Method 2: Extract JSON block
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            return json.loads(json_str)
        
        # Method 3: Look for code block
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if code_block_match:
            json_str = code_block_match.group(1)
            return json.loads(json_str)
            
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON parsing failed: {str(e)}")
    except Exception as e:
        print(f"⚠️  Unexpected parsing error: {str(e)}")
    
    # Try to extract partial information from text
    return extract_context_from_text(response)

def extract_context_from_text(response: str) -> Dict[str, Any]:
    """Fallback: Extract context information from free text response."""
    context = get_fallback_context()
    
    # Look for asset mentions
    asset_patterns = [
        r'(?:Apple|AAPL)',
        r'(?:Tesla|TSLA)', 
        r'(?:Bitcoin|BTC)',
        r'(?:Microsoft|MSFT)',
        r'(?:Google|GOOGL)',
        r'(?:Amazon|AMZN)',
        r'(?:Oil|Crude|WTI|Brent)',
    ]
    
    for pattern in asset_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            # This is a simplified version of the reference logic
            asset_name = pattern.split('|')[0].strip(r'?:(')
            symbol = pattern.split('|')[1].strip(r')')
            context["asset_info"] = {
                "primary_symbol": symbol,
                "asset_name": f"{asset_name} Inc." if 'Inc.' not in asset_name else asset_name,
                "asset_type": "stock",
                "sector": "Technology",
            }
            break # Found one
    
    return context

def get_fallback_context() -> Dict[str, Any]:
    """Get fallback context if parsing fails."""
    return {
        "asset_info": {
            "primary_symbol": "SPY",
            "asset_name": "Financial Asset",
            "asset_type": "equity",
            "sector": "Technology",
        },
        "hypothesis_details": {
            "direction": "neutral",
            "timeframe": "3-6 months",
        },
        "research_guidance": {
            "search_terms": ["market analysis", "financial data"],
            "key_metrics": ["price", "volume"],
        },
        "risk_analysis": {
            "primary_risks": ["market volatility"],
        }
    }

def parse_contradictions_response(response_text: str) -> List[Dict]:
    """Parse contradictions from agent response."""
    contradictions = []
    
    # Clean the response text
    response_text = response_text.strip()
    
    # First, try to parse as complete JSON array
    try:
        # Try parsing the entire response as JSON
        parsed = json.loads(response_text)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and 'quote' in item:
                    contradictions.append({
                        "quote": str(item.get("quote", ""))[:400],
                        "reason": str(item.get("reason", "Market analysis identifies this challenge"))[:400],
                        "source": str(item.get("source", "Market Analysis"))[:40],
                        "strength": str(item.get("strength", "Medium"))
                    })
            if contradictions:
                return contradictions[:5]
    except:
        pass
    
    # Second, try to find JSON array in the text
    try:
        # Look for JSON array pattern (more flexible)
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', response_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and 'quote' in item:
                        contradictions.append({
                            "quote": str(item.get("quote", ""))[:400],
                            "reason": str(item.get("reason", "Market analysis identifies this challenge"))[:400],
                            "source": str(item.get("source", "Market Analysis"))[:40],
                            "strength": str(item.get("strength", "Medium"))
                        })
                if contradictions:
                    return contradictions[:5]
    except:
        pass
    
    # Third, try to find individual JSON objects
    try:
        # Find all JSON objects in the response
        json_objects = re.findall(r'\{[^{}]*"quote"[^{}]*\}', response_text, re.DOTALL)
        for obj_str in json_objects:
            try:
                parsed = json.loads(obj_str)
                if isinstance(parsed, dict) and 'quote' in parsed:
                    contradictions.append({
                        "quote": str(parsed.get("quote", ""))[:400],
                        "reason": str(parsed.get("reason", "Market analysis identifies this challenge"))[:400],
                        "source": str(parsed.get("source", "Market Analysis"))[:40],
                        "strength": str(parsed.get("strength", "Medium"))
                    })
            except:
                continue
        if contradictions:
            return contradictions[:5]
    except:
        pass
    
    # Fallback: Parse text for risk indicators
    lines = response_text.split('\n')
    risk_indicators = ['risk', 'challenge', 'concern', 'pressure', 'decline', 
                       'competition', 'regulation', 'slowdown', 'headwind', 'threat',
                       'weakness', 'vulnerability', 'uncertainty', 'volatility']
    
    for line in lines:
        line = line.strip().strip('*-• "')
        if len(line) < 20: continue
        
        if any(indicator in line.lower() for indicator in risk_indicators):
            contradictions.append({
                "quote": line[:400],
                "reason": "Market analysis identifies this as a potential challenge.",
                "source": "Text Analysis",
                "strength": "Medium"
            })
            if len(contradictions) >= 5:
                break
    
    return contradictions[:5] if contradictions else []

def parse_synthesis_response(response_text: str, contradictions: List[Dict]) -> Dict[str, Any]:
    """Parse synthesis response and extract confirmations."""
    
    confirmations = []
    
    # Clean the response text
    response_text = response_text.strip()
    
    # First, try to parse as complete JSON object
    try:
        parsed = json.loads(response_text)
        if isinstance(parsed, dict):
            # Check if confirmations are in the root
            if 'confirmations' in parsed and isinstance(parsed['confirmations'], list):
                for item in parsed['confirmations']:
                    if isinstance(item, dict) and 'quote' in item:
                        confirmations.append({
                            "quote": str(item.get("quote", ""))[:400],
                            "reason": str(item.get("reason", ""))[:400],
                            "source": str(item.get("source", "Market Analysis"))[:40],
                            "strength": str(item.get("strength", "Medium"))
                        })
            # Check if confirmations array is directly in the response
            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and 'quote' in item:
                        confirmations.append({
                            "quote": str(item.get("quote", ""))[:400],
                            "reason": str(item.get("reason", ""))[:400],
                            "source": str(item.get("source", "Market Analysis"))[:40],
                            "strength": str(item.get("strength", "Medium"))
                        })
    except:
        pass
    
    # Second, try to find JSON object with confirmations array
    if not confirmations:
        try:
            # Look for the confirmations array in JSON
            json_match = re.search(r'"confirmations"\s*:\s*\[\s*\{.*?\}\s*\]', response_text, re.DOTALL)
            if json_match:
                # Extract just the array part
                array_match = re.search(r'\[\s*\{.*?\}\s*\]', json_match.group(), re.DOTALL)
                if array_match:
                    parsed = json.loads(array_match.group())
                    if isinstance(parsed, list):
                        for item in parsed:
                            if isinstance(item, dict) and 'quote' in item:
                                confirmations.append({
                                    "quote": str(item.get("quote", ""))[:400],
                                    "reason": str(item.get("reason", ""))[:400],
                                    "source": str(item.get("source", "Market Analysis"))[:40],
                                    "strength": str(item.get("strength", "Medium"))
                                })
        except:
            pass
    
    # Third, try to find individual confirmation objects
    if not confirmations:
        try:
            # Find all JSON objects that might be confirmations
            json_objects = re.findall(r'\{[^{}]*"quote"[^{}]*\}', response_text, re.DOTALL)
            for obj_str in json_objects:
                try:
                    parsed = json.loads(obj_str)
                    if isinstance(parsed, dict) and 'quote' in parsed:
                        # Check if it looks like a confirmation (not a contradiction)
                        quote_lower = str(parsed.get("quote", "")).lower()
                        if any(word in quote_lower for word in ['support', 'positive', 'growth', 'strong', 'favorable', 'bullish', 'momentum', 'advantage']):
                            confirmations.append({
                                "quote": str(parsed.get("quote", ""))[:400],
                                "reason": str(parsed.get("reason", ""))[:400],
                                "source": str(parsed.get("source", "Market Analysis"))[:40],
                                "strength": str(parsed.get("strength", "Medium"))
                            })
                except:
                    continue
        except:
            pass

    # Generate default confirmations if still empty (but only as last resort)
    if not confirmations:
        confirmations = [
            {
                "quote": "Market analysis indicates potential for this hypothesis based on current conditions.",
                "reason": "Fundamental and technical factors suggest favorable conditions.",
                "source": "Market Analysis",
                "strength": "Medium"
            },
            {
                "quote": "Technical indicators and market sentiment support the thesis.",
                "reason": "Multiple signals align with the hypothesis direction.",
                "source": "Technical Analysis",
                "strength": "Medium"
            }
        ]

    # Calculate confidence score (from reference)
    conf_count = len(confirmations)
    contra_count = len(contradictions)
    
    if conf_count == 0 and contra_count == 0:
        confidence = 0.5
    else:
        ratio = conf_count / (conf_count + contra_count + 0.01) # avoid zero division
        confidence = 0.3 + (ratio * 0.4)  # Range: 0.3 to 0.7
        
    confidence = max(0.15, min(0.85, confidence)) # Bound
    
    # Extract clean synthesis text
    synthesis_text = response_text.strip()
    # Remove any JSON artifacts
    synthesis_text = re.sub(r'\{[^}]+\}', '', synthesis_text)
    synthesis_text = re.sub(r'\[[^\]]+\]', '', synthesis_text)
    synthesis_text = ' '.join(synthesis_text.split()) # Normalize whitespace
    
    if len(synthesis_text) < 100:
        synthesis_text = "Analysis complete. Confidence score reflects market data, supporting factors, and identified risks."

    return {
        "analysis": synthesis_text,
        "confirmations": confirmations[:5],
        "confidence_score": confidence
    }

def parse_alerts_response(response_text: str) -> Dict[str, Any]:
    """Parse alerts response."""
    alerts = []
    
    # Try to extract JSON array of alerts (from reference)
    try:
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', response_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and 'message' in item:
                        alerts.append({
                            "type": item.get("type", "recommendation"),
                            "message": item.get("message", "")[:500],
                            "priority": item.get("priority", "medium")
                        })
                if alerts:
                    return {
                        "alerts": alerts[:5],
                        "recommendations": "See alerts for recommendations."
                    }
    except:
        pass

    # Fallback: Parse text for actionable alerts (from reference)
    lines = response_text.split('\n')
    action_words = ['Enter', 'Set', 'Monitor', 'Wait', 'Consider', 'Watch', 'Avoid']
    
    for line in lines:
        line = line.strip('•-*"\' ')
        if len(line) < 20: continue
            
        if any(word in line for word in action_words):
            alerts.append({
                "type": "recommendation",
                "message": line[:500],
                "priority": "medium"
            })

    # Generate default alerts if none found (from reference)
    if not alerts:
        alerts = [
            {
                "type": "recommendation",
                "message": "Monitor price action and volume for entry signals",
                "priority": "medium"
            },
            {
                "type": "risk_management",
                "message": "Set appropriate stop-loss levels based on volatility",
                "priority": "medium"
            }
        ]
    
    return {
        "alerts": alerts[:5],
        "recommendations": " ".join([a["message"] for a in alerts[:3]])
    }

