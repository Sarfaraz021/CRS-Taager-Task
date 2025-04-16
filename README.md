# CRS-Taager-Task 

An AI-powered conversational recommender system.

## Project Overview

This project provides:
- Conversation analysis using LangChain, Langgraph and OpenAI
- Vector storage with Pinecone
- FastAPI endpoint with Swagger documentation
- Data processing and indexing capabilities

## Prerequisites

- Python 3.11+
- OpenAI API key
- Pinecone API key

## Installation

1. Navigate to Code directory:
```bash
open folder
cd Code
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
   - Create `Code/var.env` with your API keys:
```env
OPENAI_API_KEY = your_openai_key_here
PINECONE_API_KEY = your_pinecone_key_here
PINECONE_INDEX_NAME = "crstaager"
```

## Usage


1. Index the conversation data if you want to load an additional files in vector databse for RAG Pipeline:
```bash
cd Code
python indexing.py
```

2. Or just Start the API server:
```bash
python api.py
```

3. Access the Swagger UI:
   - Open `http://localhost:8000/docs` in your browser
   - Test the API endpoints through the interactive interface

## API Endpoints

### POST /analyze
Analyzes customer service conversations and provides optimization strategies.

Request body:
```json
{
    "query": "string"  // The conversation text to analyze
}
```

Response:
```json
{
    "analysis": "string"  // Detailed analysis with recommendations
}
```

## Project Structure

```
CRS-Taager-Task/
├── Code/
│   ├── api.py          # FastAPI implementation
│   ├── app.py          # Core analysis workflow
│   ├── indexing.py     # Data indexing utilities
│   ├── prompt.py       # Analysis prompt templates
│   └── var.env         # Environment variables
├── Data/               # Conversation data files
├── requirements.txt    # Python dependencies
└── N8N Arabic Data Loading + Transcription + Translation Workflow # This folder contains n8n workflow that i used to load the audio data from google drive -> Trnscribed them -> translated them in english and saved them in an other google drive.
├──README.md           # Readme file  
```