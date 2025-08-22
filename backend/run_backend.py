#!/usr/bin/env python3
"""
Simple runner script for Lucky Gas backend
Ensures proper Python path setup
"""
import sys
import os

# Add backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Now we can import and run the app
if __name__ == "__main__":
    import uvicorn
    
    # Import the app after path is set
    from app.main import app
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )