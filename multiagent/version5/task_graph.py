from typing import Dict, TypedDict, Annotated, List, Any
import json
from dotenv import load_dotenv
import os
import getpass

from langgraph.graph import Graph, StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.pregel import InvalidUpdateError

# Merge helpers
def dict_merge(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """If multiple parallel updates to a dict come in, merge them."""
    return {**old, **new}

load_dotenv()
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")

class TaskPlan(TypedDict):
    plan: Dict[str, List[str]]

class TaskState(TypedDict):
    """
    - task_plan: holds the dict of subtask => list of instructions
    - partial_results: dictionary of subtask => string output
    - input_prompt: overall prompt
    - merged_result: final merged essay
    """
    task_plan: TaskPlan
    partial_results: Annotated[Dict[str, str], dict_merge]  # parallel merges
    input_prompt: str
    merged_result: str

planner_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
executor_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
merger_llm   = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def task_planner(state: TaskState) -> TaskState:
    """
    Asks GPT to produce a plan in JSON with a top-level "plan" key whose
    value is a dict of subtask => list of instructions. Example:

    {
      "plan": {
        "introduction": [...],
        "background": [...],
        "benefit_1": [...],
        "conclusion": [...]
      }
    }
    If it fails or is empty, a default plan is used.
    """
    system_text = """You are a Task Planning AI.
You must break down the user's task into multiple subtasks that can be done in parallel.
Each subtask has a name (like "introduction", "background", "benefit_1", etc.) and a list of instructions.

**Your output must be valid JSON** with a single top-level key "plan".
For example:
{
  "plan": {
    "introduction": ["Define AI...", "Explain context..."],
    "background": ["Research the current state...", "Collect stats..."],
    "benefit_1": ["Describe first benefit...", "Give example..."],
    "conclusion": ["Summarize points...", "Give final thoughts..."]
  }
}

Do not include markdown fences or extraneous text. Only return the JSON object.
"""
    user_text = f"Task to plan:\n{state['input_prompt']}"
    messages = [
        AIMessage(role="system", content=system_text),
        HumanMessage(content=user_text)
    ]

    try:
        print("Planner: calling LLM for plan...")
        llm_response = planner_llm(messages)
        raw_text = llm_response.content.strip()
        print("Planner raw response:\n", raw_text)
        plan_data = json.loads(raw_text)

        # Validate plan
        if "plan" not in plan_data or not plan_data["plan"]:
            print("Empty or invalid plan. Using fallback.")
            plan_data = _fallback_plan()
    except Exception as e:
        print("Planner error:", e)
        plan_data = _fallback_plan()

    print("Final Plan:\n", plan_data)
    return {
        **state,
        "task_plan": plan_data,
        "partial_results": {},
        "merged_result": ""
    }

def _fallback_plan() -> TaskPlan:
    return {
      "plan": {
        "introduction": ["Define AI", "Introduce AI in healthcare"],
        "benefit_1": ["Discuss first major benefit", "Give example(s)"],
        "benefit_2": ["Discuss second major benefit", "Give example(s)"],
        "conclusion": ["Summarize and conclude"]
      }
    }

def router(state: TaskState) -> Dict:
    """
    Looks at the plan's keys and returns a list of executor node names
    to run in parallel. For example, if plan has subtask keys:
      introduction, background, benefit_1, benefit_2, conclusion
    we return:
      ["exec_introduction", "exec_background", "exec_benefit_1", ...]
    """
    subtask_keys = list(state["task_plan"]["plan"].keys())
    # If no subtasks, jump to merger
    if not subtask_keys:
        return {"next": ["merger"]}

    # Return parallel executors
    next_nodes = [f"exec_{k}" for k in subtask_keys]
    return {"next": next_nodes}

def make_executor(subtask_name: str):
    """
    Creates a node function that uses the subtask instructions plus the overall prompt.
    Writes its result to partial_results[subtask_name].
    """
    def executor_fn(state: TaskState) -> TaskState:
        instructions = state["task_plan"]["plan"][subtask_name]
        full_prompt = f"""Subtask: {subtask_name}
Overall Task: {state['input_prompt']}
Instructions for this subtask:
{instructions}
"""
        print(f"\n=== Executor {subtask_name} running ===")
        print("Prompt:\n", full_prompt)

        system_text = "You are a specialized subtask executor. Follow the instructions meticulously."
        msgs = [
            AIMessage(role="system", content=system_text),
            HumanMessage(content=full_prompt)
        ]
        try:
            response = executor_llm(msgs)
            output_text = response.content.strip()
        except Exception as e:
            print(f"Executor {subtask_name} error: {e}")
            output_text = f"Error occurred in {subtask_name}."

        # Write result
        return {
            "partial_results": {subtask_name: output_text}
        }
    return executor_fn

def merger(state: TaskState) -> TaskState:
    """
    Merges partial_results into one coherent output, preserving the order
    of subtasks from the plan's keys.
    """
    plan_keys = list(state["task_plan"]["plan"].keys())
    # Combine in plan order
    final_text = []
    for k in plan_keys:
        if k in state["partial_results"]:
            chunk = state["partial_results"][k]
            final_text.append(f"--- {k.upper()} ---\n{chunk}\n")
        else:
            final_text.append(f"--- {k.upper()} ---\n(No result)\n")

    merged = "\n".join(final_text)
    print("\n=== MERGER ===\nMerged output:\n", merged)
    return {
        **state,
        "merged_result": merged
    }

def create_parallel_workflow() -> Graph:
    # Our typed state is TaskState
    workflow = StateGraph(TaskState)

    # Add nodes
    workflow.add_node("planner", task_planner)
    workflow.add_node("router", router)
    workflow.add_node("merger", merger)

    possible_subtasks = ["introduction", "background", "benefit_1", "benefit_2", "benefit_3", "conclusion"]
    for st in possible_subtasks:
        node_name = f"exec_{st}"
        workflow.add_node(node_name, make_executor(st))
        # after the router, we can go to this executor
        workflow.add_edge("router", node_name)
        # each executor eventually leads to "merger"
        workflow.add_edge(node_name, "merger")

    # Edges: planner -> router, router -> ... -> merger -> END
    workflow.add_edge("planner", "router")
    workflow.add_edge("merger", END)

    workflow.set_entry_point("planner")
    return workflow.compile()

def process_task(prompt: str) -> TaskState:
    graph = create_parallel_workflow()
    init_state: TaskState = {
        "input_prompt": prompt,
        "task_plan": {"plan": {}},
        "partial_results": {},
        "merged_result": ""
    }

    final_state = graph.invoke(init_state)
    return final_state

if __name__ == "__main__":
    # This is the user prompt
    prompt_text = "Write an essay about the benefits of artificial intelligence in healthcare."
    final = process_task(prompt_text)

    print("\n=== FINAL STATE ===")
    print(json.dumps(final, indent=2))

    print("\n=== PARTIAL RESULTS ===")
    for sub, text in final["partial_results"].items():
        print(f"Subtask {sub} =>", text)

    print("\n=== MERGED RESULT ===")
    print(final["merged_result"])
