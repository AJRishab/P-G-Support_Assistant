import uvicorn
import os

if __name__ == "__main__":
    # Start the server on port 8000
    print("Starting P&G Chat Assistant FastAPI Backend...")
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
