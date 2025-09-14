"""
ChromaDB vector store manager for code embeddings and retrieval.
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.docstore.document import Document
import chromadb
from chromadb.config import Settings

class CodeVectorStore:
    def __init__(
        self,
        collection_name: str = "cqia_code_chunks",
        persist_directory: str = ".cqia_vectordb",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )

        self.vector_store = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(self.persist_directory),
        )

    def add_documents(self, documents: List[Document], batch_size: int = 100) -> List[str]:
        all_ids = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_ids = [f"doc_{i + j}" for j in range(len(batch))]
            self.vector_store.add_documents(documents=batch, ids=batch_ids)
            all_ids.extend(batch_ids)
        # No explicit persist() needed with Chroma 0.4+
        return all_ids


    def delete_by_file_path(self, file_path: str) -> int:
        try:
            col = self.client.get_collection(self.collection_name)
            res = col.get(where={"file_path": file_path})
            ids = (res or {}).get("ids") or []
            if ids:
                col.delete(ids=ids)
                self.vector_store = Chroma(
                    client=self.client,
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings,
                    persist_directory=str(self.persist_directory),
                )
            return len(ids)
        except Exception:
            return 0

    def update_documents(self, documents: List[Document], file_path: str) -> List[str]:
        self.delete_by_file_path(file_path)
        return self.add_documents(documents)

    def as_retriever(self, k: int = 5, score_threshold: float = 0.5, filter: Optional[Dict[str, Any]] = None):
        search_kwargs: Dict[str, Any] = {"k": k, "score_threshold": score_threshold}
        if filter:
            search_kwargs["filter"] = filter
        return self.vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs=search_kwargs,
        )

    def similarity_search_with_score(
        self, query: str, k: int = 5, filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        return self.vector_store.similarity_search_with_score(query=query, k=k, filter=filter)

    def get_collection_stats(self) -> Dict[str, Any]:
        try:
            col = self.client.get_collection(self.collection_name)
            count = col.count()
            out: Dict[str, Any] = {"total_documents": int(count)}
            if count > 0:
                sample = col.get(limit=min(100, count))
                langs, types, files = set(), set(), set()
                for md in (sample.get("metadatas") or []):
                    if not md:
                        continue
                    langs.add(md.get("language", "unknown"))
                    types.add(md.get("chunk_type", "unknown"))
                    files.add(md.get("file_name", "unknown"))
                out.update({
                    "languages": sorted(langs),
                    "chunk_types": sorted(types),
                    "unique_files": len(files),
                    "sample_files": list(files)[:10],
                })
            return out
        except Exception as e:
            return {"error": str(e)}

    def reset_collection(self) -> bool:
        try:
            self.client.delete_collection(self.collection_name)
            self.vector_store = Chroma(
                client=self.client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_directory),
            )
            return True
        except Exception:
            return False

class CodeEmbeddingManager:
    def __init__(self, persist_directory: str = ".cqia_vectordb", embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.vector_store = CodeVectorStore(persist_directory=persist_directory, embedding_model=embedding_model)

    def index_repository(self, file_metas: List, chunker_func: callable) -> Dict[str, Any]:
        results = {"total_files": 0, "successful_files": 0, "failed_files": 0, "total_chunks": 0, "errors": []}
        for fm in file_metas:
            try:
                text = Path(fm.path).read_text(encoding="utf-8", errors="ignore")
                docs = chunker_func(str(fm.path), text, fm.language)
                if docs:
                    ids = self.vector_store.update_documents(docs, str(fm.path))
                    results["total_chunks"] += len(ids)
                    results["successful_files"] += 1
                results["total_files"] += 1
            except Exception as e:
                results["failed_files"] += 1
                results["errors"].append(f"{fm.path}: {e}")
        return results

    def get_stats(self) -> Dict[str, Any]:
        return self.vector_store.get_collection_stats()

    def search(self, query: str, k: int = 5, filter: Optional[Dict[str, Any]] = None):
        return self.vector_store.similarity_search_with_score(query=query, k=k, filter=filter)
