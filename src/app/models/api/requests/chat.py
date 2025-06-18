from pydantic import BaseModel


class ChatModelSettings(BaseModel):
    primary_model: str = "claude-sonnet-4-0"
    secondary_model: str = "claude-3-7-sonnet-latest"
    max_tokens: int = 8192
    temperature: float = 0.5


class ChatbotRequest(BaseModel):
    content: str
    chat_model_settings: ChatModelSettings = ChatModelSettings()
