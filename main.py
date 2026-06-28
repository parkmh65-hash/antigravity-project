from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import agent
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="LangGraph Agent API",
    description="A FastAPI server running a LangGraph agent powered by Gemini.",
    version="1.0.0"
)

# Request and Response schemas
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

@app.get("/")
def read_root():
    return {"status": "running", "info": "LangGraph Agent API is ready!"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # Check if the API key is present in environment
    if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "your_gemini_api_key_here":
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not configured. Please set your Gemini API key in the .env file."
        )
    
    try:
        # Structure the input for LangGraph
        # Inputs contain the user's message as a tuple (role, message)
        inputs = {"messages": [("user", request.message)]}
        
        # Invoke the compiled LangGraph agent asynchronously
        result = await agent.ainvoke(inputs)
        
        # Extract the assistant's last message content
        last_message = result["messages"][-1]
        
        return ChatResponse(reply=last_message.content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing agent workflow: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
