# P&G Customer Support Chat Assistant (Multi-Agent System)

This is a working implementation of the P&G Customer Support Chat Assistant, designed as a **Multi-Agent system** with a **Python (FastAPI) backend** and a **React/Vite frontend**.

## Features

1. **Safety Scan First (Step 1)**: Scanning customer messages for physical risks, injuries, skin rashes, ingestion, or chemical exposure, independent of emotional tone.
2. **Product Catalog Query & Factual Grounding (Step 2 & 3)**: Match and verify user questions against a structured official database of products (Tide, Pampers, Olay, Gillette).
3. **Sentiment Tone Classification (Step 4)**: Assessing user emotional tone (calm, annoyed, furious) separately to avoid bias.
4. **Decide Handoff & Log Ticket (Step 5 & 6)**: Triggering human agent escalation if a safety concern is raised OR if the customer is annoyed/furious. Tickets are saved in SQLite and visible on the support dashboard.
5. **Stream Response (Step 7 & 9)**: The reply is generated dynamically, apologizing if the customer is frustrated, giving safety advice without medical diagnosis, and streamed character-by-character along with the active agent progress logs.
6. **Session Persistence (Step 8)**: Uses client-side LocalStorage session tokens. Closed and reopened tabs load history from SQLite, surviving backend restarts.

## Folder Structure

```
pg-support-assistant/
├── server/
│   ├── src/
│   │   ├── config/
│   │   │   └── products.json      # Trustworthy official product details
│   │   ├── agents/
│   │   │   ├── orchestrator_agent.py # Coordinates agents & response streams
│   │   │   ├── safety_agent.py       # binary safety scanner
│   │   │   ├── product_agent.py      # product catalog search & grounding
│   │   │   └── sentiment_agent.py    # tone classifier
│   │   ├── services/
│   │   │   ├── db_service.py         # SQLite connection manager
│   │   │   └── llm_service.py        # Gemini API / rule-based fallback mock
│   │   └── main.py                   # FastAPI server endpoints
│   ├── tests/
│   │   ├── test_engine.py            # isolated agent tests
│   │   ├── test_storage.py           # DB restart survival tests
│   │   ├── test_integration.py       # full pipeline integration tests
│   │   └── run_tests.py              # custom test runner execution script
│   ├── requirements.txt              # python package list
│   └── run.py                        # backend app entrypoint
├── client/
│   ├── src/
│   │   ├── components/
│   │   ├── App.jsx                   # primary chat and dashboard UI
│   │   ├── index.css                 # custom CSS, styling design system
│   │   └── main.jsx
│   ├── index.html
│   └── vite.config.js                # Vite configuration with server proxy
└── README.md
```

## How to Run

### Prerequisite
Make sure you have Python 3.8+ and Node.js 16+ installed.

### 1. Start the Backend Server

Set your Gemini API key (optional - the system uses a fully capable mock mode if not present):
```bash
# Windows (CMD)
set GEMINI_API_KEY=your_key_here

# Windows (PowerShell)
$env:GEMINI_API_KEY="your_key_here"
```

Install requirements and run:
```bash
cd server
pip install -r requirements.txt
python run.py
```
The server will start on `http://localhost:8000`.

### 2. Start the Frontend Client

In a separate terminal:
```bash
cd client
npm install
npm run dev
```
The frontend will start on `http://localhost:3000`.

### 3. Running Tests
To run the automated test suite verifying Phases 1, 2, and 3:
```bash
cd server
python tests/run_tests.py
```
