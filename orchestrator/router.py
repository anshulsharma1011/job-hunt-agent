from orchestrator.state import CycleState


def route_after_profile(state: CycleState) -> str:
    return "profile_exists" if state["profile"] is not None else "no_profile"
