from __future__ import annotations
from typing import Literal, List, Optional, Dict, Any
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

class CQIAState(TypedDict, total=False):
    # Inputs
    mode: Literal["analyze", "chat"]
    path: Optional[str]
    include: Optional[List[str]]
    exclude: Optional[List[str]]
    max_bytes: Optional[int]
    question: Optional[str]
    k: Optional[int]
    name_match_boost: Optional[float]

    # Shared / memory
    messages: List[BaseMessage]

    # Outputs / artifacts
    analysis_report_path: Optional[str]
    analysis_json_path: Optional[str]
    retrieval_docs: Optional[List[Dict[str, Any]]]
    answer: Optional[str]

    # Control / guardrails
    next_action: Optional[Literal["run_analyze", "run_chat", "end"]]
    steps: Optional[List[str]]
