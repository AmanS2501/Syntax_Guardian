
from __future__ import annotations
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
import re

class FileAwareRetriever(BaseRetriever):
    # Pydantic v2 config: allow arbitrary types and no extra errors
    model_config = dict(arbitrary_types_allowed=True)

    # Declare fields so Pydantic knows them
    vector_store: Any
    k: int = 5
    name_match_boost: float = 0.3

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        base = self.vector_store.similarity_search_with_score(query, k=self.k * 2)
        tokens = self._identifiers(query)
        rescored = []
        for doc, score in base:
            adj = float(score)
            name = (doc.metadata or {}).get("name", "").lower()
            fname = (doc.metadata or {}).get("file_name", "").lower()
            for t in tokens:
                if t in name:
                    adj += float(self.name_match_boost)
                if t in fname:
                    adj += float(self.name_match_boost) * 0.5
            rescored.append((doc, adj))
        rescored.sort(key=lambda x: x[1], reverse=True)
        return [d for d, _ in rescored[: self.k]]

    def _identifiers(self, q: str) -> List[str]:
        return [t for t in re.findall(r"\\b[a-zA-Z_][a-zA-Z0-9_]*\\b", (q or "").lower()) if len(t) >= 3]
