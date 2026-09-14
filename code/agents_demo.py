import json
from typing import TypedDict, Dict, Any, List
from langgraph.graph import StateGraph, END
from src.model_client import ModelClient
from pydantic import BaseModel, Field, field_validator, ValidationError
class PlannerOutput(BaseModel):
    tags: List[str] = Field(min_length=3, max_length=3)
    summary: str
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, tags):
        for tag in tags:
            if not 3 <= len(tag) <= 30:
                raise ValueError("Each tag must be 3 to 30 characters")
        return tags
    @field_validator("summary")
    @classmethod
    def validate_summary(cls, summary):
        if len(summary.split()) > 25:
            raise ValueError("Summary must be at most 25 words")
        return summary
class AgentState(TypedDict):
    title: str
    content: str
    planner_proposal: Dict[str, Any]
    reviewer_feedback: Dict[str, Any]
    turn_count: int
    max_turns: int
    planner_attempts: int
    validation_failures: int
def planner_node(state: AgentState) -> Dict[str, Any]:
    print("---NODE: Planner---")
    planner_attempts = state["planner_attempts"] + 1
    client = ModelClient(
        model_name="qwen3:8b",
        temperature=0.0,
        format="json"
    )
    feedback = state.get("reviewer_feedback", {})
    planner_prompt = f"""
    You are the Planner agent.
    Title: {state["title"]}
    Content: {state["content"]}
    Previous feedback: {json.dumps(feedback)}
    Please give exactly three relevant tags and a one sentence summary up to twenty five words.
    If previous feedback contains an issue, correct that issue.
    Return only valid JSON in exactly this format:
    {{
        "tags": ["tag1", "tag2", "tag3"],
        "summary": "summary here"
    }}
    """
    response = client.complete(planner_prompt)
    raw_proposal = json.loads(response.content)

    try:
        validated = PlannerOutput.model_validate(raw_proposal)
        proposal = validated.model_dump()
        print(json.dumps(proposal, indent=2))
        return {
            "planner_proposal": proposal,
            "reviewer_feedback": {},
            "planner_attempts": planner_attempts
        }
    except ValidationError as error:
        print("---VALIDATION ERROR---")
        print(error)
        return {
            "planner_proposal": {},
            "reviewer_feedback": {
                "has_issue": True,
                "feedback": str(error)
            },
            "planner_attempts": planner_attempts,
            "validation_failures": state["validation_failures"] + 1
        }
def reviewer_node(state: AgentState) -> Dict[str, Any]:
    print("---NODE: Reviewer---")
    client = ModelClient(
        model_name="qwen3:8b",
        temperature=0.0,
        format="json"
    )
    reviewer_prompt = f"""
    You are the Reviewer agent.
    Title: {state["title"]}
    Content: {state["content"]}
    Planner output: {json.dumps(state["planner_proposal"])}
    Check whether there are exactly three relevant tags and whether the summary is correct and no more than twenty five words.
    Return only valid JSON in exactly this format:
    {{
        "has_issue": false,
        "feedback": "No issues found"
    }}
    If there is a problem, set "has_issue" to true and explain the problem in "feedback".
    """
    response = client.complete(reviewer_prompt)
    feedback = json.loads(response.content)
    print(json.dumps(feedback, indent=2))
    return {"reviewer_feedback": feedback}
def supervisor_node(state: AgentState) -> Dict[str, Any]:
    print("---NODE: Supervisor---")
    return {"turn_count": state["turn_count"] + 1}
def router_logic(state: AgentState):
    if state["turn_count"] >= state["max_turns"]:
        return END
    if not state.get("planner_proposal"):
        return "planner"
    if not state.get("reviewer_feedback"):
        return "reviewer"
    if state["reviewer_feedback"].get("has_issue"):
        return "planner"
    return END
def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("planner", planner_node)
    graph.add_node("reviewer", reviewer_node)
    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        router_logic,
        {
            "planner": "planner",
            "reviewer": "reviewer",
            END: END
        }
    )
    graph.add_edge("planner", "supervisor")
    graph.add_edge("reviewer", "supervisor")
    return graph.compile()
def run_graph(title, content, max_turns=10):
    app = build_graph()
    initial_state = {
        "title": title,
        "content": content,
        "planner_proposal": {},
        "reviewer_feedback": {},
        "turn_count": 0,
        "max_turns": max_turns,
        "planner_attempts": 0,
        "validation_failures": 0
    }
    final_state = None
    for step in app.stream(initial_state):
        print(step)
        final_state = step
    return final_state
if __name__ == "__main__":
    title = input("Please enter a title... ")
    content = input("Please enter the content... ")
    run_graph(title, content)