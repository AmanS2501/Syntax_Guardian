from __future__ import annotations
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from cqia.qa.prompt import SYSTEM_QA, USER_QA, format_context
from dotenv import load_dotenv
load_dotenv()

def build_chatgroq_llm(model_name: str = "openai/gpt-oss-120b", temperature: float = 0.0):
    # Requires GROQ_API_KEY in env
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
    context = format_context(docs)
    return chain.invoke(
        {
            "question": question,
            "context": context,
            "rationale": detector_rationale or "None provided",
            "findings": findings_context or "No findings context provided.",
        }
    )
