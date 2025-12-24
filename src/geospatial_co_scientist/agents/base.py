"""Base agent class for all Co-Scientist agents."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from geospatial_co_scientist.config import LLMProvider, get_settings
from geospatial_co_scientist.models.state import AgentType, CoScientistState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents in the Co-Scientist system."""

    agent_type: AgentType = AgentType.SUPERVISOR
    default_model: str = "gpt-4-turbo-preview"

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs
    ):
        self.settings = get_settings()
        self.model_name = model_name or self.default_model
        self.temperature = temperature or self.settings.temperature
        self._llm: Optional[BaseChatModel] = None
        self.kwargs = kwargs

    @property
    def llm(self) -> BaseChatModel:
        """Get or create the LLM instance."""
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm

    def _create_llm(self) -> BaseChatModel:
        """Create the appropriate LLM based on configuration."""
        provider = self.settings.llm_provider

        if provider == LLMProvider.OPENAI:
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=self.settings.openai_api_key,
                max_tokens=self.settings.max_tokens
            )
        elif provider == LLMProvider.ANTHROPIC:
            return ChatAnthropic(
                model=self.model_name,
                temperature=self.temperature,
                api_key=self.settings.anthropic_api_key,
                max_tokens=self.settings.max_tokens
            )
        elif provider == LLMProvider.AZURE_OPENAI:
            from langchain_openai import AzureChatOpenAI
            return AzureChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=self.settings.azure_openai_api_key,
                azure_endpoint=self.settings.azure_openai_endpoint
            )
        else:
            # Default to OpenAI
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=self.settings.openai_api_key
            )

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The system prompt for this agent."""
        pass

    def get_prompt_template(self) -> ChatPromptTemplate:
        """Get the chat prompt template for this agent."""
        return ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{input}")
        ])

    async def invoke(
        self,
        input_text: str,
        state: Optional[CoScientistState] = None
    ) -> str:
        """
        Invoke the agent with input text.

        Args:
            input_text: The input to process
            state: Optional current state

        Returns:
            The agent's response
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=input_text)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Agent {self.agent_type} failed: {e}")
            raise

    def invoke_sync(
        self,
        input_text: str,
        state: Optional[CoScientistState] = None
    ) -> str:
        """Synchronous version of invoke."""
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=input_text)
        ]

        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Agent {self.agent_type} failed: {e}")
            raise

    @abstractmethod
    async def process(self, state: CoScientistState) -> CoScientistState:
        """
        Process the current state and return updated state.

        This is the main method called by the LangGraph workflow.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        pass

    def log_action(self, action: str, details: Optional[dict] = None):
        """Log an agent action."""
        logger.info(f"[{self.agent_type.value}] {action}")
        if details:
            logger.debug(f"[{self.agent_type.value}] Details: {details}")

    def add_message_to_state(
        self,
        state: CoScientistState,
        content: str,
        **metadata
    ) -> None:
        """Add a message from this agent to the state."""
        state.add_message(self.agent_type, content, **metadata)

    def format_context(self, state: CoScientistState) -> str:
        """Format relevant context from state for the agent."""
        context_parts = []

        if state.research_goal:
            context_parts.append(
                f"Research Goal: {state.research_goal.get('question', 'Not specified')}"
            )

        if state.literature_summary:
            summary = state.literature_summary.get("summary", "")
            if summary:
                context_parts.append(f"Literature Summary:\n{summary[:1000]}...")

        if state.hypotheses:
            context_parts.append(f"Current hypotheses count: {len(state.hypotheses)}")

        return "\n\n".join(context_parts)


class ToolUsingAgent(BaseAgent):
    """Base class for agents that use tools."""

    def __init__(self, tools: Optional[list] = None, **kwargs):
        super().__init__(**kwargs)
        self.tools = tools or []

    def _create_llm(self) -> BaseChatModel:
        """Create LLM with tool binding."""
        llm = super()._create_llm()
        if self.tools:
            return llm.bind_tools(self.tools)
        return llm

    async def invoke_with_tools(
        self,
        input_text: str,
        state: Optional[CoScientistState] = None
    ) -> tuple[str, list[dict]]:
        """
        Invoke the agent with tools and return response with tool calls.

        Returns:
            Tuple of (response_text, tool_calls)
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=input_text)
        ]

        response = await self.llm.ainvoke(messages)

        tool_calls = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_calls = response.tool_calls

        return response.content, tool_calls
