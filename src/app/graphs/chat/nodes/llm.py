from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic
from anthropic.types.text_block import TextBlock
from anthropic.types.tool_use_block import ToolUseBlock
from langchain_core.runnables.config import RunnableConfig
from langgraph.types import StreamWriter
from loguru import logger
from pydantic.json_schema import JsonSchemaValue

from app.graphs import Node
from app.utils import PromptStore

from ..state import ChatGraphState


class LLM(Node[ChatGraphState]):
    """Interacts with Anthropic models through Amazon Bedrock.

    Attributes:
        name: Identifier for the node in the graph.
    """

    name = "llm"

    def __init__(
        self,
        anthropic_client: AsyncAnthropic,
        tool_schemas: dict[str, dict[str, str | JsonSchemaValue]],
        prompt_store: PromptStore,
    ) -> None:
        """Initializes the LLM node.

        Args:
            anthropic_client: Client for making LLM calls.
            tool_schemas: JSON schema for the tools available to the LLM.
            prompt_store: Store for managing prompts used in the graph.
        """
        self.anthropic_client = anthropic_client
        self.tool_schemas = list(tool_schemas.values())
        self.prompt_store = prompt_store

    def _validate_config(self, config: RunnableConfig) -> dict[str, Any]:
        """Validates and extracts node configuration.

        Args:
            config: Configuration for the node execution

        Returns:
            Validated node configuration

        Raises:
            KeyError: If required configuration is missing.
        """
        node_config = config.get("configurable", {}).get(self.name)
        if not node_config:
            raise KeyError(
                f"Configuration for node '{self.name}' is missing in 'configurable'."
            )

        required_keys = ["primary_model", "secondary_model"]
        for key in required_keys:
            if key not in node_config:
                raise KeyError(
                    f"'{key}' is required in the configuration for node '{self.name}'."
                )

        return node_config

    def _process_response_content(self, response: Any) -> list[dict[str, Any]]:
        """Processes response content blocks into serializable format.

        Args:
            response: The response message from the API

        Returns:
            List of processed content blocks

        Raises:
            ValueError: If the content block type is unexpected.
        """
        content: list[dict[str, Any]] = []
        for element in response.content:
            if isinstance(element, TextBlock):
                content.append(element.model_dump(exclude={"citations"}))
            elif isinstance(element, ToolUseBlock):
                content.append(element.model_dump())
            else:
                raise ValueError(
                    f"Unexpected content block type: {type(element)}"
                )
        return content

    @asynccontextmanager
    async def _stream_with_model(
        self,
        model_name: str,
        node_config: dict[str, Any],
        state: ChatGraphState,
    ) -> AsyncIterator[Any]:
        """Context manager for streaming with a specific model.

        Args:
            model_name: Name of the model to use
            node_config: Node configuration
            state: Current graph state

        Yields:
            Stream of messages from the model
        """
        async with self.anthropic_client.messages.stream(
            model=model_name,
            max_tokens=node_config.get("max_tokens", 8_192),
            temperature=node_config.get("temperature", 0.0),
            messages=state.messages,  # type: ignore
            tools=self.tool_schemas,  # type: ignore
            system=[
                {
                    "type": "text",
                    "text": f"<current_date> {datetime.now(timezone.utc).date()} </current_date>",
                },
                {
                    "type": "text",
                    "text": self.prompt_store.get_prompt(
                        "system.jinja2"
                    ).render(),
                },
            ],
        ) as stream:
            yield stream

    async def _execute_with_model(
        self,
        model_name: str,
        node_config: dict[str, Any],
        state: ChatGraphState,
        writer: StreamWriter,
    ) -> ChatGraphState:
        """Execute LLM call with a specific model.

        Args:
            model_name: Name of the model to use
            node_config: Node configuration
            state: Current graph state
            writer: Stream writer for streaming custom events

        Returns:
            Updated graph state
        """
        async with self._stream_with_model(
            model_name=model_name, node_config=node_config, state=state
        ) as stream:
            async for text in stream.text_stream:
                writer(text)

        response = await stream.get_final_message()
        content = self._process_response_content(response=response)

        return ChatGraphState(
            messages=[{"role": response.role, "content": content}],
            stop_reason=str(response.stop_reason),
        )

    async def __call__(
        self,
        state: ChatGraphState,
        config: RunnableConfig,
        writer: StreamWriter,
    ) -> ChatGraphState:
        """Invokes the LLM with fallback support.

        Args:
            state: Current state of the graph
            config: Configuration for the node execution
            writer: Stream writer for streaming custom events

        Returns:
            Updated graph state with new message and the llm stop reason.

        Raises:
            KeyError: If required configuration is missing.
            ValueError: If the content block type is unexpected.
            Exception: If both primary and fallback models fail.
        """
        node_config = self._validate_config(config=config)

        try:
            return await self._execute_with_model(
                model_name=node_config["primary_model"],
                node_config=node_config,
                state=state,
                writer=writer,
            )
        except Exception as primary_error:
            logger.warning(
                "Primary model `{model} failed with error: `{error}`.",
                model=node_config["primary_model"],
                error=str(primary_error),
            )

            try:
                return await self._execute_with_model(
                    model_name=node_config["secondary_model"],
                    node_config=node_config,
                    state=state,
                    writer=writer,
                )
            except Exception as fallback_error:
                logger.error(
                    "Both primary and fallback models failed. Primary model error: `{primary_error}`, Fallback model error: `{fallback_error}`.",
                    primary_error=str(primary_error),
                    fallback_error=str(fallback_error),
                )
                raise Exception(
                    f"Both models failed - Primary ({node_config['primary_model']}): {primary_error}, "
                    f"Fallback ({node_config['secondary_model']}): {fallback_error}"
                ) from fallback_error
