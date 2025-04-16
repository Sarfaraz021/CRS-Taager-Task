# D:\CRS-Taager-Task\Code\api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# from typing import List, Dict, Any, Optional
# import os
import sys
# from pathlib import Path

# Import from app.py for workflow
from app import app as workflow_app
from langchain_core.messages import HumanMessage

# FastAPI app initialization
description = """
# Customer Service Optimization API

This API provides access to an AI-powered conversation analysis tool that helps optimize customer service interactions.
It leverages historical conversation data to provide actionable strategies for increasing order confirmation rates.
"""

tags_metadata = [
    {
        "name": "analysis",
        "description": "Endpoints for analyzing customer conversations",
    }
]

# Initialize FastAPI
api = FastAPI(
    title="Customer Service Analyzer API",
    description=description,
    version="1.0.0",
    openapi_tags=tags_metadata,
)

# Add CORS middleware
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request and response models
class ConversationRequest(BaseModel):
    query: str
    
class AnalysisResponse(BaseModel):
    analysis: str

@api.post("/analyze", response_model=AnalysisResponse, tags=["analysis"])
async def analyze_conversation(request: ConversationRequest):
    """
    Analyze a customer conversation snippet and provide optimization strategies.
    
    - **query**: The customer conversation text to analyze
    
    Returns analysis with recommended strategies for handling the conversation.
    """
    if not request.query or len(request.query.strip()) == 0:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Prepare input for the workflow
    workflow_input = {
        "messages": [
            HumanMessage(content=request.query)
        ]
    }
    
    try:
        # Execute the workflow
        final_results = None
        
        # We'll store the analysis result
        analysis_content = None
        
        # Process the workflow stream
        for output in workflow_app.stream(workflow_input):
            # Looking specifically for the analysis node output
            if "analyze" in output:
                analysis_content = output["analyze"]["messages"][-1].content
        
        if analysis_content:
            return AnalysisResponse(analysis=analysis_content)
        else:
            raise HTTPException(status_code=500, detail="Analysis failed to complete")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

# Health check endpoint
@api.get("/health", tags=["system"])
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    
    # Default port
    port = 8000
    
    # Check if port is specified in command line args
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    
    print(f"\n{'='*50}")
    print(f"Starting Customer Service Analyzer API on port {port}")
    print(f"API documentation available at: http://localhost:{port}/docs")
    print(f"{'='*50}\n")
    
    uvicorn.run("api:api", host="0.0.0.0", port=port, reload=True)