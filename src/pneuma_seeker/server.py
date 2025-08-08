from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Pneuma-Seeker")

# Initialize system components
pneuma_seeker = 

# Input model for API requests
class UserInput(BaseModel):
    message: str

@app.post("/chat/")
def chat(user_input: UserInput):
    """
    Handle chat input from the user and return the system's response.
    """
    response = chat_interface.receive_user_input(user_input.message)
    return {"response": response}

@app.get("/state/")
def get_state():
    """
    Returns the current SQLs and target schemas.
    """
    state = llm_conductor.state.get_state()
    return {"state": state}

@app.post("/reset/")
def reset_state():
    """
    Resets the chat session state.
    """
    llm_conductor.state.reset()
    return {"message": "State has been reset."}
