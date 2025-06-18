from typing import Annotated

from pydantic import BaseModel, Field

from app.tools.base import BaseTool


class Placeholder(BaseModel):
    placeholder: Annotated[
        str,
        Field(
            description="this is a placeholder",
        ),
    ]


class PlaceholderTool(BaseTool[Placeholder, str]):
    name: str = "get_placeholder"
    description: str = "This is a placeholder tool meant to be replaced"
    input_schema: type[Placeholder] = Placeholder

    async def __call__(self, input_data: Placeholder) -> str:
        return input_data.placeholder
