import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from app.core.config import GOOGLE_API_KEY
from typing import Dict, Any, List
import asyncio
import traceback

# Import the live market data service
from app.services.market_research_service import fetch_market_research

# Import our parser utilities
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

class TradeSageOrchestrator:
    """
    Re-implements the 6-agent pipeline using the Google GenAI SDK and live data lookup.
    """

    def __init__(self):
        # Configuration for requesting JSON or Text output
        self.json_generation_config = GenerationConfig(
            response_mime_type="application/json"
        )
        self.text_generation_config = GenerationConfig(
            response_mime_type="text/plain"
        )
        
        # FIX: Using gemini-1.5-flash which is the correct model name for this SDK
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash"
        )
        print("-> TradeSageOrchestrator (Gemini SDK Edition) initialized.")
        
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
            print(f"--- Gemini API call failed: {e}")
            return f"Error: {e}"

    def _format_agent_input(self, agent_name: str, input_data: Dict[str, Any]) -> str:
        """
        Formats the prompt for each agent, incorporating research data where applicable.
        """
        base_hypothesis = input_data.get('hypothesis', '')
        
        if agent_name == "hypothesis":
            return f"""
            Process this trading hypothesis: "{base_hypothesis}"
            
            Rewrite it into a clear, concise, and testable thesis statement.
            Return *only* the rewritten thesis statement as plain text.
            """
            
        elif agent_name == "context":
            return f"""
            Analyze the context for this trading hypothesis: "{base_hypothesis}"

            You *must* return *only* a valid JSON object with the following structure:
            {{
              "asset_info": {{
                "primary_symbol": "<TICKER>",
                "asset_name": "<Asset Name>",
                "asset_type": "<e.g., stock, crypto>",
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

        elif agent_name == "contradiction":
            research_summary = input_data.get('research_data', {}).get('summary', '')
            
            # This agent should return a JSON array
            return f"""
            Identify contradictions and risk factors for this hypothesis:
            Hypothesis: "{base_hypothesis}"
            
            **Market Context:** {research_summary}

            Find 3-5 specific risks, challenges, or contradictory evidence.
            
            You *must* return *only* a valid JSON array of objects:
            [
                {{ "quote": "<The risk>", "reason": "<Why it's a risk>", "source": "<Source>", "strength": "<Medium/High/Low>" }},
                {{ "quote": "<Another risk>", "reason": "<...>", "source": "<...>", "strength": "<...>" }}
            ]
            """
            
        elif agent_name == "synthesis":
            research_summary = input_data.get('research_data', {}).get('summary', '')
            contradictions = input_data.get('contradictions', [])
            
            return f"""
            Synthesize a comprehensive investment analysis for this hypothesis:
            Hypothesis: "{base_hypothesis}"
            
            **Market Context:** {research_summary}
            Risk Factors: {len(contradictions)} identified

            Provide a balanced analysis. Identify 2-3 supporting confirmations.
            
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
            Generate actionable alerts and recommendations for this investment hypothesis:
            Synthesis: {synthesis}

            Provide 2-3 specific, actionable alerts.
            
            You *must* return *only* a valid JSON array of objects:
            [
                {{ "type": "<recommendation/risk_management>", "message": "<The alert message>", "priority": "<high/medium/low>" }},
                {{ "type": "<...>", "message": "<...>", "priority": "<...>" }}
            ]
            """
        
        return str(input_data)

    async def process_hypothesis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a trading hypothesis through the 6-step Gemini-powered pipeline.
        """
        
        hypothesis_text = input_data.get("hypothesis", "").strip()
        if not hypothesis_text:
            return {"status": "error", "error": "No hypothesis provided"}
        
        print(f"-> Starting Gemini workflow for: {hypothesis_text[:100]}...")
        
        try:
            # --- Step 1: Process Hypothesis (Text -> Text) ---
            print("--- [1/6] Processing hypothesis...")
            step1_prompt = self._format_agent_input("hypothesis", {"hypothesis": hypothesis_text})
            step1_response = await self._call_gemini_agent_async(step1_prompt) 
            processed_hypothesis = extract_response(step1_response)
            print(f"--- Processed: {processed_hypothesis[:80]}...")
            
            # --- Step 2: Analyze Context (Text -> JSON) ---
            print("--- [2/6] Analyzing context...")
            step2_prompt = self._format_agent_input("context", {"hypothesis": processed_hypothesis})
            step2_response = await self._call_gemini_agent_async(step2_prompt, use_json_mode=True)
            context = parse_json_response(step2_response)
            symbol = context.get('asset_info', {}).get('primary_symbol', 'N/A')
            print(f"--- Asset identified: {context.get('asset_info', {}).get('asset_name', 'N/A')} ({symbol})")
            
            # --- Step 3: Conduct Research (LIVE API CALL) ---
            # This replaces the simulated research with a real Alpha Vantage call
            print("--- [3/6] Fetching live market research...")
            
            market_data_dict = await fetch_market_research(symbol)
            
            research_summary = f"""
            Market Data from Alpha Vantage for {symbol}:
            - Current Price: ${market_data_dict.get('price', 'N/A')}
            - Trading Volume: {market_data_dict.get('volume', 'N/A')}
            - 50-Day Moving Average: {market_data_dict.get('fifty_day_moving_average', 'N/A')}
            - Company Summary: {market_data_dict.get('overview', 'No company summary available.')[:300]}...
            """
            
            research_data = {
                "summary": research_summary,
                "tool_results": market_data_dict,
            }
            print(f"--- Research data fetched for {symbol}.")

            # --- Step 4: Identify Contradictions (Text -> JSON List) ---
            print("--- [4/6] Identifying contradictions...")
            step4_prompt = self._format_agent_input("contradiction", {
                "hypothesis": processed_hypothesis,
                "context": context,
                "research_data": research_data
            })
            step4_response = await self._call_gemini_agent_async(step4_prompt, use_json_mode=True)
            contradictions = parse_contradictions_response(step4_response)
            print(f"--- Found {len(contradictions)} contradictions.")
            
            # --- Step 5: Synthesize Analysis (Text -> JSON) ---
            print("--- [5/6] Synthesizing analysis...")
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
            print(f"--- Synthesis complete - Confidence: {confidence_score:.2f}")

            # --- Step 6: Generate Alerts (Text -> JSON List) ---
            print("--- [6/6] Generating alerts...")
            step6_prompt = self._format_agent_input("alert", {
                "hypothesis": processed_hypothesis,
                "synthesis": synthesis_data
            })
            step6_response = await self._call_gemini_agent_async(step6_prompt, use_json_mode=True)
            alerts_data = parse_alerts_response(step6_response)
            alerts = alerts_data.get("alerts", [])
            print(f"--- Generated {len(alerts)} alerts.")
            
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
                "method": "gemini_sdk_pipeline_live_data"
            }
            
            print(f"-> Gemini workflow completed successfully.")
            return result
            
        except Exception as e:
            print(f"--- Orchestration error: {e}")
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "method": "gemini_sdk_pipeline_live_data",
            }

# --- Global Orchestrator Instance ---
try:
    orchestrator = TradeSageOrchestrator()
except Exception:
    print(f"--- FAILED TO INITIALIZE ORCHESTRATOR ---")
    orchestrator = None