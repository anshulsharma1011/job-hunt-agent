# T10 — Orchestrator: Nodes + Graph

**Status:** `pending`
**Depends on:** T5, T6, T8, T9

## Goal
Five LangGraph node functions wired into the compiled graph with MongoDBSaver checkpointer.

## Files to Create

```
orchestrator/nodes.py
orchestrator/graph.py
```

## `orchestrator/nodes.py`

Each function takes `CycleState` and returns only the keys it modifies.

```python
def load_profile_node(state: CycleState, deps: Deps) -> dict:
    """
    Reads active ProfileDoc from MongoDB via ProfileRepository.
    Returns: {"profile": dict | None, "search_criteria": dict | None}
    """

def run_profile_agent_node(state: CycleState, deps: Deps) -> dict:
    """
    Calls ProfileAgent.run(). Saves result via ProfileRepository.
    Returns: {"profile": dict, "search_criteria": dict}
    """

def run_discovery_match_node(state: CycleState, deps: Deps) -> dict:
    """
    Calls DiscoveryMatchAgent.run().
    Calls apply_budget_gate() after scoring completes.
    Returns: {"raw_opportunities", "scored_opportunities", "shortlisted",
              "rejected", "token_spend", "sources_queried"}
    """

def store_results_node(state: CycleState, deps: Deps) -> dict:
    """
    Calls opportunity_repo.upsert_many(shortlisted + rejected).
    Calls cycle_repo.update() with counts and token spend.
    Returns: {}
    """

def run_reporter_node(state: CycleState, deps: Deps) -> dict:
    """
    Calls ReporterAgent.run().
    Returns: {"report_path": str}
    """
```

`Deps` is a dataclass holding all injected dependencies (repos, agents, config) — passed via LangGraph's config mechanism, not global state.

## `orchestrator/graph.py`

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.mongodb import MongoDBSaver

def build_graph(deps: Deps) -> CompiledGraph:
    builder = StateGraph(CycleState)

    builder.add_node("load_profile", partial(load_profile_node, deps=deps))
    builder.add_node("run_profile_agent", partial(run_profile_agent_node, deps=deps))
    builder.add_node("run_discovery_match", partial(run_discovery_match_node, deps=deps))
    builder.add_node("store_results", partial(store_results_node, deps=deps))
    builder.add_node("run_reporter", partial(run_reporter_node, deps=deps))

    builder.set_entry_point("load_profile")

    builder.add_conditional_edges("load_profile", route_after_profile, {
        "profile_exists": "run_discovery_match",
        "no_profile": "run_profile_agent",
    })
    builder.add_edge("run_profile_agent", "run_discovery_match")
    builder.add_edge("run_discovery_match", "store_results")
    builder.add_edge("store_results", "run_reporter")
    builder.add_edge("run_reporter", END)

    checkpointer = MongoDBSaver(deps.mongo_client)
    return builder.compile(checkpointer=checkpointer)
```

## Initial State Helper

```python
def make_initial_state(cycle_id: str) -> CycleState:
    return CycleState(
        cycle_id=cycle_id,
        profile=None,
        search_criteria=None,
        raw_opportunities=[],
        scored_opportunities=[],
        shortlisted=[],
        rejected=[],
        report_path=None,
        errors=[],
        token_spend=0.0,
        sources_queried=[],
    )
```

## Steps

1. Define `Deps` dataclass with all injectable dependencies
2. Write all 5 node functions in `orchestrator/nodes.py`
3. Write `build_graph()` in `orchestrator/graph.py`
4. Write `make_initial_state()` helper
5. Run `mypy orchestrator/nodes.py orchestrator/graph.py` — must pass
6. No unit tests at this layer — covered by T18 (e2e smoke)
7. Commit
