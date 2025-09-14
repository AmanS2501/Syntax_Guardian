# cqia/qa/chain.py
from __future__ import annotations
from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from cqia.qa.prompt import SYSTEM_QA, USER_QA, format_context

# Add a small helper to cap request size by characters (fast + deterministic)
def _trim(s: str, max_chars: int) -> str:
    if not s:
        return s
    if len(s) <= max_chars:
        return s
    # keep head and tail to preserve most-relevant boundaries
    half = max_chars // 2
    return f"{s[:half]}\n...\n{s[-half:]}"

def build_chatgroq_llm(model_name: str = "llama-3.3-70b-versatile", temperature: float = 0.0):
    return ChatGroq(model_name=model_name, temperature=temperature)  # type: ignore

def build_qa_chain(llm: ChatGroq):
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_QA), ("user", USER_QA)])
    return prompt | llm | StrOutputParser()

def answer_with_citations(
    llm: ChatGroq,
    question: str,
    docs: List,
    detector_rationale: Optional[str] = None,
    findings_context: str = "",
) -> str:
    chain = build_qa_chain(llm)
    # Build raw context
    context = format_context(docs)
    # Guardrails to satisfy Groq 413/TPM limits on on_demand tier:
    # - cap retrieved context aggressively (e.g., ~10k chars total)
    # - cap findings further (e.g., ~6k chars)
    # - keep rationale tiny
    safe_context   = _trim(context, 10_000)
    safe_findings  = _trim(findings_context or "No findings context provided.", 6_000)
    safe_rationale = _trim(detector_rationale or "None provided", 512)

    return chain.invoke(
        {
            "question": question,
            "context": safe_context,
            "rationale": safe_rationale,
            "findings": safe_findings,
        }
    )
