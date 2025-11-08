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
        self.json_generation_config = GenerationConfig(
            response_mime_type="application/json"
        )
        self.text_generation_config = GenerationConfig(
            response_mime_type="text/plain"
        )
        
        # --- FIX 1: Change Model Name ---
        # We will use gemini-1.5-flash-latest, which is fast and supports JSON mode.
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash"
        )
        print("✅ TradeSageOrchestrator (Gemini SDK Edition) initialized.")
        
    # --- FIX 2: Restore this function to accept 'use_json_mode' ---
    async def _call_gemini_agent_async(self, prompt: str, use_json_mode: bool = False) -> str:
        """
        A wrapper to call the Gemini API asynchronously.
        This version correctly handles JSON mode.
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
            # --- NO 'use_json_mode' here ---
            step1_response = await self._call_gemini_agent_async(step1_prompt) 
            processed_hypothesis = extract_response(step1_response)
            print(f"   ✅ Processed: {processed_hypothesis[:80]}...")
            
            # --- Step 2: Analyze Context (Text -> JSON) ---
            print("🔍 [2/6] Analyzing context...")
            step2_prompt = self._format_agent_input("context", {"hypothesis": processed_hypothesis})
            # --- YES 'use_json_mode' here ---
            step2_response = await self._call_gemini_agent_async(step2_prompt, use_json_mode=True)
            context = parse_json_response(step2_response)
            print(f"   ✅ Asset identified: {context.get('asset_info', {}).get('asset_name', 'N/A')}")
            
            # --- Step 3: Conduct Research (Text -> Text) ---
            print("📊 [3/6] Conducting research (simulated)...")
            step3_prompt = self._format_agent_input("research", {"hypothesis": processed_hypothesis, "context": context})
            # --- NO 'use_json_mode' here ---
            step3_response = await self._call_gemini_agent_async(step3_prompt)
            research_summary = extract_response(step3_response)
            
            research_data = {
                "summary": "Market data shows high volatility. Recent news is mixed." if not research_summary else research_summary,
                "tool_results": {}, 
            }
            print(f"   ✅ Research summary generated.")

            # --- Step 4: Identify Contradictions (Text -> JSON List) ---
            print("⚠️  [4/6] Identifying contradictions...")
            step4_prompt = self._format_agent_input("contradiction", {
                "hypothesis": processed_hypothesis,
                "context": context,
                "research_data": research_data
            })
            # --- YES 'use_json_mode' here ---
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
            # --- YES 'use_json_mode' here ---
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
            # --- YES 'use_json_mode' here ---
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
            print(f"❌ Orchestration error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "method": "gemini_sdk_pipeline",
            }

# --- Global Orchestrator Instance ---
try:
    orchestrator = TradeSageOrchestrator()
except Exception as e:
    print(f"--- FAILED TO INITIALIZE ORCHESTRATOR ---")
    print(f"Error: {e}")
    orchestrator = None