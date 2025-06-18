from functools import lru_cache

from .handler import ToolHandler
from .placeholder import PlaceholderTool


@lru_cache(maxsize=1)
def get_tool_handler() -> ToolHandler:
    handler = ToolHandler()
    handler.register_tool(PlaceholderTool())
    return handler
