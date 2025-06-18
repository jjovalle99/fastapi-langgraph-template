from abc import ABC, abstractmethod

from pydantic import BaseModel


class BaseTool[InputType: BaseModel, OutputType](ABC, BaseModel):
    name: str
    description: str
    input_schema: type[InputType]

    @abstractmethod
    async def __call__(self, input_data: InputType) -> OutputType:
        pass
