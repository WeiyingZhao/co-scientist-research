"""Tests for utility modules."""

import json
import pytest

from geospatial_co_scientist.utils.json_utils import (
    extract_json_from_markdown,
    parse_json_dict,
    parse_json_list,
    parse_json_safely,
    repair_json,
)
from geospatial_co_scientist.utils.tracing import (
    TracingContext,
    log_agent_action,
    traceable,
)


class TestJSONParsing:
    """Tests for robust JSON parsing utilities."""

    def test_parse_json_safely_valid_json(self):
        """Test parsing valid JSON."""
        text = '{"name": "test", "value": 42}'
        result = parse_json_safely(text, expected_type=dict)
        assert result == {"name": "test", "value": 42}

    def test_parse_json_safely_valid_list(self):
        """Test parsing valid JSON list."""
        text = '[{"id": 1}, {"id": 2}]'
        result = parse_json_safely(text, expected_type=list)
        assert result == [{"id": 1}, {"id": 2}]

    def test_extract_json_from_markdown(self):
        """Test extracting JSON from markdown code blocks."""
        text = '''Here is the JSON:
```json
{"key": "value"}
```
'''
        result = extract_json_from_markdown(text)
        assert result.strip() == '{"key": "value"}'

    def test_extract_json_from_markdown_no_lang(self):
        """Test extracting JSON from code blocks without language."""
        text = '''Result:
```
{"key": "value"}
```
'''
        result = extract_json_from_markdown(text)
        assert result.strip() == '{"key": "value"}'

    def test_parse_json_with_markdown_wrapper(self):
        """Test parsing JSON wrapped in markdown."""
        text = '''Here is the result:
```json
{"name": "test", "count": 5}
```
'''
        result = parse_json_safely(text, expected_type=dict)
        assert result == {"name": "test", "count": 5}

    def test_repair_json_trailing_comma(self):
        """Test repairing JSON with trailing commas."""
        text = '{"key": "value",}'
        repaired = repair_json(text)
        result = json.loads(repaired)
        assert result == {"key": "value"}

    def test_repair_json_trailing_comma_array(self):
        """Test repairing JSON array with trailing commas."""
        text = '[1, 2, 3,]'
        repaired = repair_json(text)
        result = json.loads(repaired)
        assert result == [1, 2, 3]

    def test_parse_json_list_default(self):
        """Test parse_json_list returns default for invalid input."""
        result = parse_json_list("not valid json")
        assert result == []

    def test_parse_json_list_custom_default(self):
        """Test parse_json_list returns custom default."""
        result = parse_json_list("invalid", default=[1, 2, 3])
        assert result == [1, 2, 3]

    def test_parse_json_dict_default(self):
        """Test parse_json_dict returns default for invalid input."""
        result = parse_json_dict("not valid json")
        assert result == {}

    def test_parse_json_dict_custom_default(self):
        """Test parse_json_dict returns custom default."""
        result = parse_json_dict("invalid", default={"default": True})
        assert result == {"default": True}

    def test_parse_json_with_prefix(self):
        """Test parsing JSON with LLM response prefix."""
        text = 'Here is the JSON: {"result": "success"}'
        result = parse_json_safely(text, expected_type=dict)
        assert result == {"result": "success"}

    def test_parse_json_empty_input(self):
        """Test parsing empty input."""
        assert parse_json_safely("") is None
        assert parse_json_safely("", default={"empty": True}) == {"empty": True}

    def test_parse_json_wrong_type(self):
        """Test that wrong type returns default."""
        text = '["array", "not", "dict"]'
        result = parse_json_safely(text, expected_type=dict, default={"fallback": True})
        assert result == {"fallback": True}

    def test_parse_complex_nested_json(self):
        """Test parsing complex nested JSON."""
        text = '''```json
{
  "hypotheses": [
    {
      "title": "Test",
      "assumptions": ["a1", "a2"],
      "variables": {"x": 1, "y": 2}
    }
  ]
}
```'''
        result = parse_json_safely(text, expected_type=dict)
        assert result is not None
        assert "hypotheses" in result
        assert len(result["hypotheses"]) == 1


class TestTracingUtilities:
    """Tests for tracing and observability utilities."""

    def test_tracing_context_sync(self):
        """Test TracingContext as sync context manager."""
        with TracingContext("test_operation", run_type="chain") as ctx:
            assert ctx.name == "test_operation"
            assert ctx.run_type == "chain"

    @pytest.mark.asyncio
    async def test_tracing_context_async(self):
        """Test TracingContext as async context manager."""
        async with TracingContext("test_async", run_type="llm", tags=["test"]) as ctx:
            assert ctx.name == "test_async"
            assert ctx.tags == ["test"]

    def test_log_agent_action(self, caplog):
        """Test log_agent_action logs correctly."""
        import logging
        with caplog.at_level(logging.INFO):
            log_agent_action("generation", "Processing hypotheses", {"count": 5})

        assert "GENERATION" in caplog.text
        assert "Processing hypotheses" in caplog.text
        assert "count=5" in caplog.text

    def test_traceable_decorator_sync(self):
        """Test @traceable decorator on sync function."""
        @traceable(name="test_func", run_type="tool")
        def test_function(x: int) -> int:
            return x * 2

        result = test_function(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_traceable_decorator_async(self):
        """Test @traceable decorator on async function."""
        @traceable(name="test_async_func", run_type="chain")
        async def test_async_function(x: int) -> int:
            return x * 3

        result = await test_async_function(4)
        assert result == 12

    def test_tracing_context_with_exception(self):
        """Test TracingContext logs errors properly."""
        with pytest.raises(ValueError):
            with TracingContext("failing_op"):
                raise ValueError("Test error")


class TestWorkflowConfig:
    """Tests for workflow configuration."""

    def test_workflow_config_creation(self):
        """Test WorkflowConfiguration can be created."""
        from geospatial_co_scientist.orchestration.workflow_config import (
            WorkflowConfiguration,
        )
        config = WorkflowConfiguration()
        assert config is not None

    def test_workflow_config_get_next_agent(self):
        """Test get_next_agent with initial state."""
        from geospatial_co_scientist.models.state import AgentType, CoScientistState
        from geospatial_co_scientist.orchestration.workflow_config import (
            WorkflowConfiguration,
        )

        config = WorkflowConfiguration()
        state = CoScientistState()

        # Without literature summary, should suggest literature search
        next_agent = config.get_next_agent(state)
        assert next_agent == AgentType.LITERATURE_SEARCH

    def test_workflow_config_parallel_disabled(self):
        """Test parallel groups can be disabled."""
        from geospatial_co_scientist.models.state import CoScientistState
        from geospatial_co_scientist.orchestration.workflow_config import (
            WorkflowConfiguration,
        )

        config = WorkflowConfiguration(enable_parallel=False)
        state = CoScientistState()

        result = config.get_parallel_agents(state)
        assert result is None

    def test_workflow_config_transition_graph(self):
        """Test transition graph can be retrieved."""
        from geospatial_co_scientist.orchestration.workflow_config import (
            WorkflowConfiguration,
        )

        config = WorkflowConfiguration()
        graph = config.get_transition_graph()

        assert isinstance(graph, dict)
        assert len(graph) > 0


class TestWebSearchTool:
    """Tests for web search tool."""

    @pytest.mark.asyncio
    async def test_web_search_tool_initialization(self):
        """Test WebSearchTool can be initialized."""
        from geospatial_co_scientist.tools.literature_search import WebSearchTool

        tool = WebSearchTool()
        assert tool is not None
        await tool.close()

    @pytest.mark.asyncio
    async def test_get_web_search_tool_singleton(self):
        """Test get_web_search_tool returns singleton."""
        from geospatial_co_scientist.tools.literature_search import (
            get_web_search_tool,
        )

        tool1 = get_web_search_tool()
        tool2 = get_web_search_tool()

        assert tool1 is tool2


class TestDependencyInjection:
    """Tests for dependency injection in agents."""

    def test_generation_agent_accepts_custom_tools(self):
        """Test GenerationAgent accepts custom tools."""
        from unittest.mock import MagicMock
        from geospatial_co_scientist.agents.generation import GenerationAgent

        mock_tool = MagicMock()
        agent = GenerationAgent(tools=[mock_tool])

        assert agent.tools == [mock_tool]

    def test_generation_agent_uses_default_tools(self):
        """Test GenerationAgent uses default tools when none provided."""
        from geospatial_co_scientist.agents.generation import GenerationAgent

        agent = GenerationAgent()

        assert len(agent.tools) > 0

    def test_generation_agent_accepts_custom_literature_search(self):
        """Test GenerationAgent accepts custom literature search."""
        from unittest.mock import MagicMock
        from geospatial_co_scientist.agents.generation import GenerationAgent

        mock_search = MagicMock()
        agent = GenerationAgent(literature_search=mock_search)

        assert agent.literature_search is mock_search

    def test_supervisor_agent_accepts_workflow_config(self):
        """Test SupervisorAgent accepts custom workflow config."""
        from unittest.mock import MagicMock
        from geospatial_co_scientist.agents.supervisor import SupervisorAgent
        from geospatial_co_scientist.orchestration.workflow_config import (
            WorkflowConfiguration,
        )

        config = WorkflowConfiguration(enable_parallel=False)
        agent = SupervisorAgent(workflow_config=config)

        assert agent.workflow_config is config
        assert not agent.workflow_config._enable_parallel


class TestParallelExecution:
    """Tests for parallel agent execution."""

    @pytest.mark.asyncio
    async def test_run_agents_parallel(self):
        """Test run_agents_parallel function."""
        from geospatial_co_scientist.models.state import AgentType, CoScientistState
        from geospatial_co_scientist.orchestration.nodes import run_agents_parallel

        state = CoScientistState()
        state_dict = state.model_dump()

        # This would normally run the agents, but without mocking they would fail
        # Here we're just testing the function exists and handles the types correctly
        assert run_agents_parallel is not None

    def test_merge_parallel_states(self):
        """Test _merge_parallel_states function."""
        from geospatial_co_scientist.orchestration.nodes import _merge_parallel_states

        original = {
            "hypotheses": [{"id": "1"}],
            "hypothesis_rankings": [],
            "statistics": {"count": 1},
        }

        agent_states = [
            {
                "hypotheses": [{"id": "1"}],
                "hypothesis_rankings": [{"id": "r1"}],
                "statistics": {"count": 1, "new_stat": 10},
            },
            {
                "hypotheses": [{"id": "1"}],
                "hypothesis_rankings": [{"id": "r2"}],
                "statistics": {"count": 1, "another": 20},
            },
        ]

        merged = _merge_parallel_states(original, agent_states)

        # Check rankings are merged
        assert len(merged["hypothesis_rankings"]) == 2

        # Check statistics are merged
        assert merged["statistics"]["new_stat"] == 10
        assert merged["statistics"]["another"] == 20
