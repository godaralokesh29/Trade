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
    
    # First, try to parse as JSON array
    try:
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', response_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and 'quote' in item:
                        contradictions.append({
                            "quote": item.get("quote", "")[:400],
                            "reason": item.get("reason", "Market analysis identifies this challenge")[:400],
                            "source": item.get("source", "Market Analysis")[:40],
                            "strength": item.get("strength", "Medium")
                        })
                return contradictions[:5]  # Limit to 5
    except:
        pass
    
    # Fallback: Parse text (from reference)
    lines = response_text.split('\n')
    risk_indicators = ['risk', 'challenge', 'concern', 'pressure', 'decline', 
                       'competition', 'regulation', 'slowdown', 'headwind']
    
    for line in lines:
        line = line.strip().strip('*-• ')
        if len(line) < 30: continue
        
        if any(indicator in line.lower() for indicator in risk_indicators):
            contradictions.append({
                "quote": line[:400],
                "reason": "Market analysis identifies this as a potential challenge.",
                "source": "Text Analysis",
                "strength": "Medium"
            })
    
    return contradictions[:5]

def parse_synthesis_response(response_text: str, contradictions: List[Dict]) -> Dict[str, Any]:
    """Parse synthesis response and extract confirmations."""
    
    confirmations = []
    
    # Try to extract structured confirmations from response (from reference)
    try:
        json_matches = re.findall(r'\{[^}]+\}', response_text)
        for match in json_matches:
            try:
                parsed = json.loads(match)
                if 'quote' in parsed:
                    confirmations.append({
                        "quote": parsed.get("quote", "")[:400],
                        "reason": parsed.get("reason", "")[:400],
                        "source": parsed.get("source", "Market Analysis")[:40],
                        "strength": parsed.get("strength", "Medium")
                    })
            except:
                continue
    except:
        pass

    # Generate default confirmations if needed (from reference)
    if not confirmations:
        confirmations = [
            {
                "quote": "Strong market fundamentals and improving financial metrics support growth.",
                "reason": "Fundamental analysis indicates favorable conditions.",
                "source": "Fundamental Analysis",
                "strength": "Medium"
            },
            {
                "quote": "Technical indicators showing positive momentum.",
                "reason": "Technical setup suggests upward price movement.",
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
```eof

**File 2: `app/pipeline/orchestrator.py`**

Now, the main file. This will use the Google GenAI SDK and our new parsers. This replaces `app/adk/orchestrator.py` completely.

```python:6-Step Agent Pipeline:app/pipeline/orchestrator.py
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from app.core.config import GOOGLE_API_KEY
from typing import Dict, Any, List
import asyncio

# Import our new, clean parsers
from app.utils.response_parser import (
    extract_response,
    parse_json_response,
    parse_contradictions_response,
    parse_synthesis_response,
    parse_alerts_response
)

# Configure the Gemini SDK
try:
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"--- FAILED TO CONFIGURE GOOGLE GENAI ---")
    print(f"Error: {e}")
    print("Please check your GOOGLE_API_KEY in the .env file.")

class TradeSageOrchestrator:
    """
    Re-implements the 6-agent pipeline using the Google GenAI SDK.
    The logic is preserved from the original app/adk/orchestrator.py.
    """

    def __init__(self):
        # Configure the model to force JSON output where possible
        # This is a good practice for agentic workflows.
        self.json_generation_config = GenerationConfig(
            response_mime_type="application/json"
        )
        self.text_generation_config = GenerationConfig(
            response_mime_type="text/plain"
        )
        
        # Use a model that supports JSON mode (e.g., gemini-1.5-pro-latest)
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-pro-latest"
        )
        print("✅ TradeSageOrchestrator (Gemini SDK Edition) initialized.")
        
    async def _call_gemini_agent_async(self, prompt: str, use_json_mode: bool = False) -> str:
        """
        A wrapper to call the Gemini API asynchronously.
        """
        try:
            config = self.json_generation_config if use_json_mode else self.text_generation_config
            
            response = await self.model.generate_content_async(
                contents=prompt,
                generation_config=config
            )
            return response.text
        except Exception as e:
            print(f"❌ Gemini API call failed: {e}")
            # Return a simple error string that parsers can handle
            return f"Error: {e}"

    def _format_agent_input(self, agent_name: str, input_data: Dict[str, Any]) -> str:
        """
        Formats the prompt for each agent.
        This logic is ported directly from the reference orchestrator.
        
        ** We also add instructions for JSON output **
        """
        base_hypothesis = input_data.get('hypothesis', '')
        
        if agent_name == "hypothesis":
            return f"""
            Process this trading hypothesis: "{base_hypothesis}"
            
            Rewrite it into a clear, concise, and testable thesis statement.
            Return *only* the rewritten thesis statement as plain text.
            """
            
        elif agent_name == "context":
            # This agent *must* return JSON
            return f"""
            Analyze the context for this trading hypothesis: "{base_hypothesis}"

            You *must* return *only* a valid JSON object with the following structure:
            {{
              "asset_info": {{
                "primary_symbol": "<SYMBOL>",
                "asset_name": "<Asset Name>",
                "asset_type": "<e.g., stock, crypto, commodity>",
                "sector": "<e.g., Technology>"
              }},
              "hypothesis_details": {{
                "direction": "<long, short, or neutral>",
                "timeframe": "<e.g., 3-6 months>",
                "price_target": "<target_price or 'N/A'>"
              }},
              "research_guidance": {{
                "search_terms": ["<term1>", "<term2>"],
                "key_metrics": ["<metric1>", "<metric2>"]
              }},
              "risk_analysis": {{
                "primary_risks": ["<risk1>", "<risk2>"]
              }}
            }}
            """
            
        elif agent_name == "research":
            # This agent will use RAG, so its prompt will be different
            # For now, we simulate its output
            # (We will build this out in the RAG step)
            
            # This is a placeholder until we build the RAG service
            context = input_data.get('context', {})
            asset_info = context.get('asset_info', {})
            return f"""
            You are a research agent.
            The hypothesis is: "{base_hypothesis}"
            The asset is: {asset_info.get('asset_name', 'Unknown')}
            
            Simulate a brief summary of market data and news.
            Return *only* a plain text summary.
            """

        elif agent_name == "contradiction":
            context = input_data.get('context', {})
            research_summary = input_data.get('research_data', {}).get('summary', '')[:500]
            
            # This agent should return a JSON array
            return f"""
            Identify contradictions and risk factors for this hypothesis:
            Hypothesis: "{base_hypothesis}"
            Asset Context: {context.get('asset_info', {}).get('asset_name', 'Unknown asset')}
            Research Summary: {research_summary}

            Find 3-5 specific risks, challenges, or contradictory evidence.
            
            You *must* return *only* a valid JSON array of objects:
            [
                {{ "quote": "<The risk>", "reason": "<Why it's a risk>", "source": "<Source>", "strength": "<Medium/High/Low>" }},
                {{ "quote": "<Another risk>", "reason": "<...>", "source": "<...>", "strength": "<...>" }}
            ]
            
            If you cannot find any, return an empty array [].
            """
            
        elif agent_name == "synthesis":
            context = input_data.get('context', {})
            research_summary = input_data.get('research_data', {}).get('summary', '')[:500]
            contradictions = input_data.get('contradictions', [])
            
            return f"""
            Synthesize a comprehensive investment analysis for this hypothesis:
            Hypothesis: "{base_hypothesis}"
            Asset: {context.get('asset_info', {}).get('asset_name', 'Unknown')}
            Research: {research_summary}
            Risk Factors: {len(contradictions)} identified

            Provide a balanced analysis.
            Identify 2-3 supporting confirmations.
            
            You *must* return *only* a valid JSON object:
            {{
                "analysis": "<Your brief synthesis text>",
                "confirmations": [
                    {{ "quote": "<Supporting point>", "reason": "<Why it supports>", "source": "<Source>", "strength": "<Medium/High>" }},
                    {{ "quote": "<Another point>", "reason": "<...>", "source": "<...>", "strength": "<...>" }}
                ]
            }}
            """
            
        elif agent_name == "alert":
            synthesis = input_data.get('synthesis', {}).get('analysis', '')[:300]
            
            return f"""
            Generate actionable alerts for this investment hypothesis:
            Synthesis: {synthesis}

            Provide 2-3 specific, actionable alerts.
            
            You *must* return *only* a valid JSON array of objects:
            [
                {{ "type": "<recommendation/risk_management>", "message": "<The alert message>", "priority": "<high/medium/low>" }},
                {{ "type": "<...>", "message": "<...>", "priority": "<...>" }}
            ]
            """
        
        return str(input_data) # Fallback

    async def process_hypothesis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a trading hypothesis through the 6-step Gemini-powered pipeline.
        This is the main function of the application.
        """
        
        hypothesis_text = input_data.get("hypothesis", "").strip()
        if not hypothesis_text:
            return {"status": "error", "error": "No hypothesis provided"}
        
        print(f"🚀 Starting Gemini workflow for: {hypothesis_text[:100]}...")
        
        try:
            # --- Step 1: Process Hypothesis (Text -> Text) ---
            print("🧠 [1/6] Processing hypothesis...")
            step1_prompt = self._format_agent_input("hypothesis", {"hypothesis": hypothesis_text})
            step1_response = await self._call_gemini_agent_async(step1_prompt)
            processed_hypothesis = extract_response(step1_response)
            print(f"   ✅ Processed: {processed_hypothesis[:80]}...")
            
            # --- Step 2: Analyze Context (Text -> JSON) ---
            print("🔍 [2/6] Analyzing context...")
            step2_prompt = self._format_agent_input("context", {"hypothesis": processed_hypothesis})
            step2_response = await self._call_gemini_agent_async(step2_prompt, use_json_mode=True)
            context = parse_json_response(step2_response)
            print(f"   ✅ Asset identified: {context.get('asset_info', {}).get('asset_name', 'N/A')}")
            
            # --- Step 3: Conduct Research (Text -> Text) ---
            # This is a placeholder. We will replace this in the RAG step.
            print("📊 [3/6] Conducting research (simulated)...")
            step3_prompt = self._format_agent_input("research", {"hypothesis": processed_hypothesis, "context": context})
            step3_response = await self._call_gemini_agent_async(step3_prompt)
            research_summary = extract_response(step3_response)
            
            # For now, we just create a simple research data object
            research_data = {
                "summary": "Market data shows high volatility. Recent news is mixed." if not research_summary else research_summary,
                "tool_results": {}, # This will be for RAG
            }
            print(f"   ✅ Research summary generated.")

            # --- Step 4: Identify Contradictions (Text -> JSON List) ---
            print("⚠️  [4/6] Identifying contradictions...")
            step4_prompt = self._format_agent_input("contradiction", {
                "hypothesis": processed_hypothesis,
                "context": context,
                "research_data": research_data
            })
            step4_response = await self._call_gemini_agent_async(step4_prompt, use_json_mode=True)
            contradictions = parse_contradictions_response(step4_response)
            print(f"   ✅ Found {len(contradictions)} contradictions.")
            
            # --- Step 5: Synthesize Analysis (Text -> JSON) ---
            print("🔬 [5/6] Synthesizing analysis...")
            step5_prompt = self._format_agent_input("synthesis", {
                "hypothesis": processed_hypothesis,
                "context": context,
                "research_data": research_data,
                "contradictions": contradictions
            })
            step5_response = await self._call_gemini_agent_async(step5_prompt, use_json_mode=True)
            synthesis_data = parse_synthesis_response(step5_response, contradictions)
            confidence_score = synthesis_data.get("confidence_score", 0.5)
            confirmations = synthesis_data.get("confirmations", [])
            print(f"   ✅ Synthesis complete - Confidence: {confidence_score:.2f}")

            # --- Step 6: Generate Alerts (Text -> JSON List) ---
            print("🚨 [6/6] Generating alerts...")
            step6_prompt = self._format_agent_input("alert", {
                "hypothesis": processed_hypothesis,
                "synthesis": synthesis_data
            })
            step6_response = await self._call_gemini_agent_async(step6_prompt, use_json_mode=True)
            alerts_data = parse_alerts_response(step6_response)
            alerts = alerts_data.get("alerts", [])
            print(f"   ✅ Generated {len(alerts)} alerts.")
            
            # --- Compile Final Result ---
            result = {
                "status": "success",
                "original_hypothesis": hypothesis_text,
                "processed_hypothesis": processed_hypothesis,
                "context": context,
                "research_data": research_data,
                "contradictions": contradictions,
                "confirmations": confirmations,
                "synthesis": synthesis_data.get("analysis", ""),
                "alerts": alerts,
                "confidence_score": confidence_score,
                "method": "gemini_sdk_pipeline"
            }
            
            print(f"✅ Gemini workflow completed successfully.")
            return result
            
        except Exception as e:
            print(f"❌ Orchestration error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "method": "gemini_sdk_pipeline",
            }

# --- Global Orchestrator Instance ---
# We create a single instance to be used by the FastAPI app
try:
    orchestrator = TradeSageOrchestrator()
except Exception as e:
    print(f"--- FAILED TO INITIALIZE ORCHESTRATOR ---")
    print(f"Error: {e}")
    orchestrator = None
