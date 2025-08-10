from pydantic import BaseModel


class RenameChatRequest(BaseModel):
    user_id: str
    chat_id: str
    new_title: str


class DeleteChatRequest(BaseModel):
    user_id: str
    chat_id: str
