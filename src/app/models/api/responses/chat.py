from pydantic import BaseModel


class ChatbotResponse(BaseModel):
    content: str
