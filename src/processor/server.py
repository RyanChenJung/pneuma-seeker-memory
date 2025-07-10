from fastapi import FastAPI
from pydantic import BaseModel
from processor.interaction_conductor.chat_interface import ChatInterface
from processor.interaction_conductor.llm_conductor import LLMConductor
from ir_system import IRSystem
from materializer_engine import MaterializerEngine

app = FastAPI(title="Interaction Conductor API")

# Initialize system components
ir_system = IRSystem()
materializer = MaterializerEngine()
llm_conductor = LLMConductor(ir_system, materializer)
chat_interface = ChatInterface(llm_conductor)

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

@app.post("/materialize/")
def materialize():
    """
    Materializes the current state if it is converged.
    """
    if llm_conductor.check_state_convergence():
        result = llm_conductor.materialize_state()
        return {"result": result}
    return {"error": "State has not converged yet."}

@app.post("/reset/")
def reset_state():
    """
    Resets the chat session state.
    """
    llm_conductor.state.reset()
    return {"message": "State has been reset."}
