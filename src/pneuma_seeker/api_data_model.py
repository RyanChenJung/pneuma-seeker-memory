from pydantic import BaseModel


class RenameChatRequest(BaseModel):
    user_id: str
    chat_id: str
    new_title: str


class UserManipulationRequest(BaseModel):
    # Applies to both user creation and deletion.
    user_id: str


class CreateDeleteChatRequest(BaseModel):
    user_id: str
    chat_id: str
