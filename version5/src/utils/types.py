from typing import Dict, List, Tuple, TypedDict, Annotated
from pydantic import BaseModel

from .helpers import dict_merge

class TaskPlan(TypedDict):
    plan: Dict[str, Dict[str, any]]  # subtask_name -> {subtask_steps: List[str], semantic_query: str}

class SubtaskSteps(BaseModel):
    subtask_name: str
    subtask_steps: list[str]
    semantic_query: str  # Query optimized for semantic search

class TaskExecutionPlan(BaseModel):
    task_execution_plan: list[SubtaskSteps]
    
class VerificationMetric(BaseModel):
    metric: str
    rating: bool 
    explanation: str
    
class VerificationFeedback(BaseModel):
    metrics: list[VerificationMetric]

class TaskState(TypedDict):
    """
    - task_plan: holds the dict of subtask => list of instructions
    - partial_results: dictionary of subtask => string output
    - input_prompt: overall prompt
    - merged_result: final merged essay
    - merged_result_with_agent: final merged essay from the agent
    - instructional_content: content from instructional PDF files
    - has_rag: boolean indicating if RAG is available
    - verification_report: feedback based on initial prompt => criterion: [text_feedback, bool_feedback]
    - retry_count: number of times the workflow has been retried due to verification failures
    """
    task_plan: TaskPlan
    partial_results: Annotated[Dict[str, str], dict_merge]
    input_prompt: str
    merged_result: str
    merged_result_with_agent: str
    instructional_content: str
    has_rag: bool 
    verification_report: dict
    retry_count: int
    