"""Memoria RAG vetorial 100% local e deterministica (TF-IDF + cosseno em stdlib) (Fase 11)."""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from factory.playforge.models import FactoryError
from factory.playforge.registry import ProjectManager, _atomic_write_json, validate_project_id
from factory.playforge.security_utils import scan_prompt_injection

RAG_INDEX_SCHEMA_VERSION = 1
_TOKEN_RE = re.compile(r"[a-z0-9_]+")


class RagMemoryError(FactoryError):
    """Erro fail-closed ao indexar ou consultar a memoria RAG local."""


def _tokenize(text: str) -> list[str]:
    return [tok for tok in _TOKEN_RE.findall(text.lower()) if len(tok) >= 2]


def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    common = set(vec_a) & set(vec_b)
    if not common:
        return 0.0
    dot = sum(vec_a[t] * vec_b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class LocalRagMemory:
    """Indice RAG local auditavel sobre artefatos dos jogos sem chamadas externas ou custo."""

    def __init__(self, manager: ProjectManager) -> None:
        self.manager = manager

    def _index_path(self) -> Path:
        return self.manager.repo_root / "data" / "rag" / "knowledge_index.json"

    def _load_index(self) -> dict[str, Any]:
        path = self._index_path()
        if not path.is_file():
            return {
                "rag_schema_version": RAG_INDEX_SCHEMA_VERSION,
                "backend": "local-tfidf-cosine-stdlib",
                "updated_at": self.manager.now_timestamp(),
                "documents": {},
            }
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RagMemoryError(f"knowledge_index.json corrompido: {exc}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("documents"), dict):
            raise RagMemoryError("Estrutura invalida em knowledge_index.json.")
        return data

    def _save_index(self, index_data: dict[str, Any]) -> None:
        index_data["updated_at"] = self.manager.now_timestamp()
        _atomic_write_json(self._index_path(), index_data)

    def _collect_project_sources(self, project_id: str) -> list[tuple[str, str]]:
        validate_project_id(project_id)
        project = self.manager.get_project(project_id)
        ws = (
            self.manager.repo_root
            if project.get("protected")
            else self.manager.resolve_game_path(project_id, ".")
        )
        candidates = (
            ("metadata", f"Project {project['name']} ({project_id}), genre={project.get('genre')}, engine={project.get('engine')}, stage={project.get('stage')}, version={project.get('version')}."),
        )
        docs: list[tuple[str, str]] = list(candidates)
        rel_files = (
            "specs/game_specification.json",
            "specs/engine_selection_report.json",
            "assets/asset_registry.json",
            "qa/qa_report.json",
            "specs/verification_report.json",
            "config/gameplay_systems.json",
        )
        for rel in rel_files:
            fpath = ws / rel
            if fpath.is_file():
                try:
                    raw = fpath.read_text(encoding="utf-8", errors="ignore")[:8000]
                except OSError:
                    continue
                if scan_prompt_injection(raw):
                    raise RagMemoryError(
                        f"Conteudo suspeito de prompt injection bloqueado ao indexar '{project_id}/{rel}'."
                    )
                docs.append((rel, raw))
        builds_dir = ws / "builds"
        if builds_dir.is_dir():
            for mf in sorted(builds_dir.rglob("build_manifest.json")):
                rel = mf.relative_to(ws).as_posix()
                docs.append((rel, mf.read_text(encoding="utf-8", errors="ignore")[:4000]))
        return docs

    def index_project(self, project_id: str) -> dict[str, Any]:
        """Indexa metadados, specs, selecao de engine, assets, QA e builds de um projeto (somente leitura)."""
        sources = self._collect_project_sources(project_id)
        index_data = self._load_index()
        docs: dict[str, Any] = index_data["documents"]

        # Remove entradas antigas deste project_id para manter indice consistente
        stale = [doc_id for doc_id, rec in docs.items() if rec.get("project_id") == project_id]
        for key in stale:
            del docs[key]

        indexed_ids: list[str] = []
        for source_rel, raw_text in sources:
            doc_id = f"{project_id}::{source_rel}"
            tokens = _tokenize(raw_text)
            counts = dict(Counter(tokens))
            docs[doc_id] = {
                "doc_id": doc_id,
                "project_id": project_id,
                "source": source_rel,
                "sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                "token_counts": counts,
                "excerpt": " ".join(raw_text.split())[:240],
                "indexed_at": self.manager.now_timestamp(),
            }
            indexed_ids.append(doc_id)

        self._save_index(index_data)
        self.manager.log_event(
            "INFO",
            "RAG_PROJECT_INDEXED",
            project_id=project_id,
            doc_count=len(indexed_ids),
        )
        return {
            "status": "INDEXED",
            "project_id": project_id,
            "doc_count": len(indexed_ids),
            "doc_ids": indexed_ids,
            "paid_services_enabled": False,
        }

    def search(
        self,
        query: str,
        *,
        project_id: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Executa busca TF-IDF + cosseno 100% local sobre o conhecimento indexado."""
        if not isinstance(query, str) or not query.strip():
            raise RagMemoryError("Consulta RAG nao pode ser vazia.")
        if top_k < 1 or top_k > 50:
            raise RagMemoryError("Parametro 'top_k' deve estar entre 1 e 50.")

        index_data = self._load_index()
        all_docs = list(index_data["documents"].values())
        if project_id:
            validate_project_id(project_id)
            candidates = [d for d in all_docs if d.get("project_id") == project_id]
        else:
            candidates = all_docs

        if not candidates:
            return {"query": query, "total_indexed": len(all_docs), "results": []}

        # IDF sobre documentos candidatos
        n_docs = len(candidates)
        df: Counter[str] = Counter()
        for doc in candidates:
            for tok in doc.get("token_counts", {}):
                df[tok] += 1

        def tfidf_vec(counts: dict[str, int]) -> dict[str, float]:
            total = max(sum(counts.values()), 1)
            return {
                tok: (cnt / total) * (math.log((n_docs + 1) / (df.get(tok, 0) + 1)) + 1.0)
                for tok, cnt in counts.items()
            }

        q_counts = dict(Counter(_tokenize(query)))
        q_vec = tfidf_vec(q_counts)

        scored: list[dict[str, Any]] = []
        for doc in candidates:
            score = _cosine_similarity(q_vec, tfidf_vec(doc.get("token_counts", {})))
            if score > 0.0:
                scored.append(
                    {
                        "doc_id": doc["doc_id"],
                        "project_id": doc["project_id"],
                        "source": doc["source"],
                        "score": round(score, 4),
                        "excerpt": doc["excerpt"],
                    }
                )
        scored.sort(key=lambda item: (-item["score"], item["doc_id"]))
        return {
            "query": query,
            "total_indexed": len(all_docs),
            "results": scored[:top_k],
            "paid_services_enabled": False,
        }
