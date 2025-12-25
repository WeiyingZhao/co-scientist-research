"""LangGraph workflow nodes for each agent."""

import asyncio
import logging
from typing import Any, Callable

from geospatial_co_scientist.agents.evolution import EvolutionAgent
from geospatial_co_scientist.agents.experiment_design import ExperimentDesignAgent
from geospatial_co_scientist.agents.generation import GenerationAgent
from geospatial_co_scientist.agents.meta_review import MetaReviewAgent
from geospatial_co_scientist.agents.proximity import ProximityAgent
from geospatial_co_scientist.agents.ranking import RankingAgent
from geospatial_co_scientist.agents.reflection import ReflectionAgent
from geospatial_co_scientist.agents.supervisor import SupervisorAgent
from geospatial_co_scientist.models.state import AgentType, CoScientistState

logger = logging.getLogger(__name__)


# Agent instances (lazily initialized)
_agents: dict[AgentType, Any] = {}


def get_agent(agent_type: AgentType) -> Any:
    """Get or create an agent instance."""
    if agent_type not in _agents:
        if agent_type == AgentType.SUPERVISOR:
            _agents[agent_type] = SupervisorAgent()
        elif agent_type == AgentType.GENERATION:
            _agents[agent_type] = GenerationAgent()
        elif agent_type == AgentType.REFLECTION:
            _agents[agent_type] = ReflectionAgent()
        elif agent_type == AgentType.RANKING:
            _agents[agent_type] = RankingAgent()
        elif agent_type == AgentType.PROXIMITY:
            _agents[agent_type] = ProximityAgent()
        elif agent_type == AgentType.EVOLUTION:
            _agents[agent_type] = EvolutionAgent()
        elif agent_type == AgentType.META_REVIEW:
            _agents[agent_type] = MetaReviewAgent()
        elif agent_type == AgentType.EXPERIMENT_DESIGN:
            _agents[agent_type] = ExperimentDesignAgent()
    return _agents.get(agent_type)


async def supervisor_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Supervisor node - coordinates the workflow.

    This node determines what agent should run next and updates the state accordingly.
    """
    logger.info("Executing supervisor node")

    # Convert dict to state object
    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.SUPERVISOR

    # Get supervisor agent and process
    supervisor = get_agent(AgentType.SUPERVISOR)
    updated_state = await supervisor.process(current_state)

    return updated_state.model_dump()


async def generation_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Generation node - creates hypotheses.
    """
    logger.info("Executing generation node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.GENERATION

    agent = get_agent(AgentType.GENERATION)
    updated_state = await agent.process(current_state)

    return updated_state.model_dump()


async def reflection_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Reflection node - reviews hypotheses.
    """
    logger.info("Executing reflection node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.REFLECTION

    agent = get_agent(AgentType.REFLECTION)
    updated_state = await agent.process(current_state)

    return updated_state.model_dump()


async def ranking_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Ranking node - prioritizes hypotheses using Elo rating.
    """
    logger.info("Executing ranking node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.RANKING

    agent = get_agent(AgentType.RANKING)
    updated_state = await agent.process(current_state)

    return updated_state.model_dump()


async def proximity_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Proximity node - analyzes hypothesis similarity and diversity.
    """
    logger.info("Executing proximity node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.PROXIMITY

    agent = get_agent(AgentType.PROXIMITY)
    updated_state = await agent.process(current_state)

    return updated_state.model_dump()


async def evolution_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Evolution node - refines and improves hypotheses.
    """
    logger.info("Executing evolution node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.EVOLUTION

    agent = get_agent(AgentType.EVOLUTION)
    updated_state = await agent.process(current_state)

    return updated_state.model_dump()


async def meta_review_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Meta-review node - synthesizes feedback and compiles outputs.
    """
    logger.info("Executing meta-review node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.META_REVIEW

    agent = get_agent(AgentType.META_REVIEW)
    updated_state = await agent.process(current_state)

    return updated_state.model_dump()


async def experiment_design_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Experiment design node - creates testing plans.
    """
    logger.info("Executing experiment design node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.EXPERIMENT_DESIGN

    agent = get_agent(AgentType.EXPERIMENT_DESIGN)
    updated_state = await agent.process(current_state)

    return updated_state.model_dump()


async def literature_search_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Literature search node - performs initial literature review.

    This is handled by the supervisor's initialize method.
    """
    logger.info("Executing literature search node")

    current_state = CoScientistState(**state)
    current_state.current_agent = AgentType.LITERATURE_SEARCH

    supervisor = get_agent(AgentType.SUPERVISOR)
    updated_state = await supervisor._perform_literature_review(current_state)

    return updated_state.model_dump()


async def human_review_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Human review node - checkpoint for human input.

    In interactive mode, this node pauses for user input.
    In batch mode, it passes through.
    """
    logger.info("Executing human review node")

    current_state = CoScientistState(**state)

    # If human feedback is provided, process it
    if current_state.human_feedback:
        supervisor = get_agent(AgentType.SUPERVISOR)
        updated_state = await supervisor.handle_human_feedback(
            current_state,
            current_state.human_feedback
        )
        updated_state.human_feedback = None  # Clear after processing
        return updated_state.model_dump()

    # Otherwise, check if we should wait for input
    # (This would be handled by the UI layer in practice)

    return state


def should_continue(state: dict[str, Any]) -> str:
    """
    Conditional edge function - determines next node based on state.

    Returns:
        Name of the next node to execute
    """
    current_state = CoScientistState(**state)

    # Check if we should stop
    if not current_state.should_continue:
        return "end"

    # Check if awaiting human input
    if current_state.awaiting_human_input:
        return "human_review"

    # Get next agent from supervisor decision
    next_agent = current_state.next_agent

    if next_agent is None:
        return "end"

    # Map agent type to node name
    agent_to_node = {
        AgentType.SUPERVISOR: "supervisor",
        AgentType.GENERATION: "generation",
        AgentType.REFLECTION: "reflection",
        AgentType.RANKING: "ranking",
        AgentType.PROXIMITY: "proximity",
        AgentType.EVOLUTION: "evolution",
        AgentType.META_REVIEW: "meta_review",
        AgentType.EXPERIMENT_DESIGN: "experiment_design",
        AgentType.LITERATURE_SEARCH: "literature_search",
    }

    return agent_to_node.get(next_agent, "supervisor")


def create_node_functions() -> dict[str, Callable]:
    """Create a dictionary of node name to function mappings."""
    return {
        "supervisor": supervisor_node,
        "generation": generation_node,
        "reflection": reflection_node,
        "ranking": ranking_node,
        "proximity": proximity_node,
        "evolution": evolution_node,
        "meta_review": meta_review_node,
        "experiment_design": experiment_design_node,
        "literature_search": literature_search_node,
        "human_review": human_review_node,
    }


async def run_agents_parallel(
    state: dict[str, Any],
    agent_types: list[AgentType]
) -> dict[str, Any]:
    """Run multiple agents in parallel and merge their state updates.

    This function enables concurrent execution of independent agents,
    improving performance when agents don't have dependencies on each other.

    Args:
        state: Current workflow state
        agent_types: List of agent types to run in parallel

    Returns:
        Merged state from all agents

    Note:
        State merging strategy:
        - Lists (hypotheses, reviews, etc.) are concatenated
        - Dicts (statistics, etc.) are merged
        - Scalar values take the last write
    """
    logger.info(f"Running agents in parallel: {[a.value for a in agent_types]}")

    async def run_single_agent(agent_type: AgentType) -> dict[str, Any]:
        """Run a single agent and return its state updates."""
        current_state = CoScientistState(**state)
        current_state.current_agent = agent_type

        agent = get_agent(agent_type)
        if agent:
            updated_state = await agent.process(current_state)
            return updated_state.model_dump()
        return state

    # Run all agents concurrently
    tasks = [run_single_agent(agent_type) for agent_type in agent_types]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions and log them
    valid_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Agent {agent_types[i].value} failed: {result}")
        else:
            valid_results.append(result)

    if not valid_results:
        return state

    # Merge results
    return _merge_parallel_states(state, valid_results)


def _merge_parallel_states(
    original_state: dict[str, Any],
    agent_states: list[dict[str, Any]]
) -> dict[str, Any]:
    """Merge states from parallel agent execution.

    Args:
        original_state: The state before parallel execution
        agent_states: List of states from each agent

    Returns:
        Merged state combining all agent updates
    """
    # Start with a copy of the original state
    merged = dict(original_state)

    # Fields that should be merged as lists (appended)
    list_fields = [
        "hypothesis_rankings",
        "hypothesis_clusters",
        "messages",
        "errors",
        "warnings",
    ]

    # Fields that should be merged as dicts
    dict_fields = ["statistics"]

    for agent_state in agent_states:
        for key, value in agent_state.items():
            if key in list_fields:
                # Append new items that don't exist in original
                original_items = original_state.get(key, [])
                new_items = [item for item in value if item not in original_items]
                merged[key] = merged.get(key, []) + new_items
            elif key in dict_fields:
                # Merge dictionaries
                merged[key] = {**merged.get(key, {}), **value}
            else:
                # For other fields, take the agent's value if changed
                if value != original_state.get(key):
                    merged[key] = value

    return merged


async def parallel_ranking_proximity_node(state: dict[str, Any]) -> dict[str, Any]:
    """Run ranking and proximity analysis in parallel.

    This is an optimized node that combines ranking and proximity
    analysis into a single parallel execution step.
    """
    logger.info("Executing parallel ranking+proximity node")
    return await run_agents_parallel(
        state,
        [AgentType.RANKING, AgentType.PROXIMITY]
    )
