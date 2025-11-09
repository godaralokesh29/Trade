# TradeSenti AI: Hybrid ML/LLM Financial Analysis Engine

[](https://www.python.org/downloads/)
[](https://fastapi.tiangolo.com/)
[](https://ai.google.dev/)
[](https://www.tensorflow.org/)
[](https://www.mongodb.com/)

TradeSage AI is a sophisticated hybrid decision engine that transforms raw trading ideas and live market data into precise, interpretable forecasts. It uses a custom-trained **LSTM neural network** for quantitative forecasting and a **6-step Generative AI (Gemini) pipeline** for qualitative reasoning and risk assessment.

## 1\. Core Features

  * **Hybrid AI Pipeline:** Combines a statistical LSTM model for price prediction with a Gemini 1.5 Flash LLM for interpretation and risk analysis.
  * **Live Data Integration:** Fetches real-time OHLCV data from Alpha Vantage to power the ML model's predictions.
  * **Sentiment Analysis:** Incorporates user-provided sentiment (or FinBERT-derived scores) as a key feature in the ML model.
  * **Structured Analysis:** Decomposes the analysis into six specialized agentic steps, from context extraction to contradiction finding and final synthesis.
  * **Modern Backend:** Built on an asynchronous **FastAPI** server with a **MongoDB** database for flexible, schemaless storage of complex AI-generated analysis.

## 2\. Architecture Overview

The innovation of TradeSage lies in its hybrid 6-level architecture. A quantitative ML model handles the prediction, and a qualitative LLM pipeline handles the interpretation.

The workflow is as follows:

1.  **[LLM] Step 1: Hypothesis Agent**

      * **Input:** Raw user text (e.g., "I think AAPL is going up, they had great news").
      * **Action:** Gemini refines this into a clear, testable thesis.
      * **Output:** "Hypothesis: AAPL will show bullish momentum."

2.  **[LLM] Step 2: Context Agent**

      * **Input:** The refined thesis.
      * **Action:** Gemini extracts the key inputs required for the ML model: the **ticker symbol** (AAPL) and the **sentiment context**.
      * **Output:** `{"ticker": "AAPL", "sentiment": "Bullish"}`

3.  **[ML] Step 3: Prediction Agent (The ML Core)**

      * **Input:** The ticker and sentiment from Step 2.
      * **Action:** The system calls the `ml_prediction_service` which:
        1.  Fetches live OHLCV data from Alpha Vantage.
        2.  Calculates technical indicators.
        3.  Pre-processes the data using the saved `scaler.joblib`.
        4.  Executes the trained `lstm_best.keras` model.
      * **Output:** `{"prediction": 278.4, "percent_change": +3.7, "confidence": "High"}`

4.  **[LLM] Step 4: Contradiction Agent**

      * **Input:** The original hypothesis + the ML model's prediction.
      * **Action:** Gemini acts as a "stress test" layer, finding risks or technical indicators that **contradict** the model's bullish forecast.
      * **Output:** A list of risks (e.g., "Risk: RSI (72) indicates the asset is overbought...").

5.  **[LLM] Step 5: Synthesis Agent**

      * **Input:** The prediction (Step 3) and the risks (Step 4).
      * **Action:** Gemini balances the quantitative forecast against the qualitative risks to write a final, human-readable rationale and assign a holistic **Confidence Score**.
      * **Output:** The final analysis summary and score.

6.  **[LLM] Step 6: Alert Agent**

      * **Input:** The synthesized analysis.
      * **Action:** Gemini generates actionable alerts based on the model's signal.
      * **Output:** `{"signal": "High confidence buy zone. Monitor for entry."}`

## 3\. Technology Stack

  * **Backend:** Python 3.10+, **FastAPI**, Uvicorn
  * **AI (Reasoning):** **Google Gemini 1.5 Flash** (via `google-generativeai` SDK)
  * **AI (Prediction):** **TensorFlow (Keras)**, Scikit-learn, Joblib
  * **Database:** **MongoDB** (via `pymongo`)
  * **Live Market Data:** **Alpha Vantage** (via `requests`)
  * **Frontend (Demo):** Single-file **React** app (in `index.html`)

## 4\. Repository Structure

```
.
├── app/
│   ├── core/
│   │   └── config.py           # Loads environment variables
│   ├── database/
│   │   ├── database.py         # MongoDB connection logic
│   │   └── crud.py             # MongoDB C/R operations
│   ├── pipeline/
│   │   └── orchestrator.py     # The 6-step hybrid pipeline logic (Gemini + ML)
│   ├── services/
│   │   ├── market_research_service.py # Fetches live data from Alpha Vantage
│   │   └── ml_prediction_service.py   # (Your new service to run the LSTM model)
│   ├── utils/
│   │   └── response_parser.py    # Utilities to parse LLM JSON/text outputs
│   └── main.py                 # FastAPI application, API endpoints
│
├── models/
│   ├── AAPL_lstm_best.keras    # (Your trained TensorFlow model)
│   └── AAPL_scaler_with_sent.joblib # (Your trained Scikit-learn scaler)
│
├── .env                        # (Your local secrets - see .env.example)
├── .env.example                # Environment variable template
├── .gitignore
├── index.html                  # Demo UI (Single-file React app)
└── requirements.txt            # Python dependencies
```

## 5\. Local Development & Quick Start

### Prerequisites

  * Python 3.10+
  * A MongoDB Atlas account (or local MongoDB instance)
  * A Google AI Studio API Key (for Gemini)
  * An Alpha Vantage API Key
  * Your trained ML model files (`.keras`, `.joblib`)

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd tradesage-ai
```

### Step 2: Set Up Environment

1.  **Create `.env` File:**
    Copy the example template and fill in your secret keys.

    ```bash
    cp .env.example .env
    ```

    **File: `.env`**

    ```env
    # Google Gemini API Key
    GOOGLE_API_KEY=YOUR_GEMINI_API_KEY_HERE

    # MongoDB Connection
    MONGO_CONNECTION_STRING=mongodb+srv://<user>:<password>@<cluster-url>/...

    # Name for your database
    MONGO_DB_NAME=tradesage_hackathon_db

    # Alpha Vantage API Key
    ALPHA_VANTAGE_API_KEY=YOUR_ALPHA_VANTAGE_API_KEY_HERE
    ```

2.  **Create Python Virtual Environment:**

    ```bash
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Place ML Models:**
    Place your trained `AAPL_lstm_best.keras` and `AAPL_scaler_with_sent.joblib` files into the `/models` directory at the project root.

### Step 3: Run the Application

1.  **Run the Backend Server:**
    The server will run on `http://127.0.0.1:8000` and automatically reload on changes.

    ```bash
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    ```

2.  **Open the Frontend:**
    Open the `index.html` file in your web browser. You can typically just double-click the file.

3.  **Test:**

      * The application UI will load.
      * Enter a hypothesis (e.g., "AAPL looks bullish") and submit.
      * View the full 6-step analysis and see the history populate on the dashboard.

## 6\. API Endpoints

The API documentation is automatically generated by FastAPI and available at `http://127.0.0.1:8000/docs`.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/process` | Submits a new hypothesis, runs the full 6-step hybrid pipeline, and saves the result to MongoDB. |
| `GET` | `/dashboard` | Retrieves a lightweight summary of all past analyses for the main dashboard. |
| `GET` | `/hypothesis/{id}` | Retrieves a single, complete analysis document by its MongoDB `_id`. |
| `GET` | `/health` | A simple health check endpoint to verify the server is running. |

### Example `/process` Request Body:

```json
{
  "hypothesis": "Apple (AAPL) stock will increase to $220 by the end of Q3 2026 due to strong services growth and new product releases."
}
```