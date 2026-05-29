"""
LLM interface module for local Ollama integration.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List


class OllamaLLMInterface:
    """Interface to a local Ollama model."""

    def __init__(
        self,
        model: str = "qwen2.5:3b-instruct-q4_K_M",
        fallback_model: str | None = "qwen3.5:cloud",
        base_url: str = "http://127.0.0.1:11434",
        timeout: int = 300,
        num_ctx: int = 32768,
    ):
        self.model_name = model
        self.fallback_model_name = fallback_model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.num_ctx = num_ctx
        self.last_request_time = None
        self.min_request_interval = 0.1

        self._verify_server()
        print(f"[OK] Initialized Ollama LLM ({self.model_name})")
        if self.fallback_model_name and self.fallback_model_name != self.model_name:
            print(f"[OK] Ollama fallback model: {self.fallback_model_name}")
        print(f"[OK] Ollama endpoint: {self.base_url}")

    def _verify_server(self) -> None:
        try:
            self._post("/api/show", {"model": self.model_name}, timeout=30)
        except Exception as exc:
            raise RuntimeError(
                f"Ollama is reachable, but model '{self.model_name}' is not ready. "
                f"Run: ollama pull {self.model_name}"
            ) from exc

        if self.fallback_model_name and self.fallback_model_name != self.model_name:
            try:
                self._post("/api/show", {"model": self.fallback_model_name}, timeout=30)
            except Exception:
                print(f"[WARN] Ollama fallback model '{self.fallback_model_name}' is not available")

    def _post(self, path: str, payload: Dict[str, Any], timeout: int | None = None) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama returned HTTP {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Could not reach Ollama at {self.base_url}: {exc}") from exc

    def _apply_rate_limit(self) -> None:
        if self.last_request_time is None:
            return

        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

    def generate_text(self, prompt: str, temperature: float = 0.1, max_tokens: int = 2048) -> str:
        """Generate text from the local Ollama model."""
        self._apply_rate_limit()

        active_prompt = self._prompt_for_model(self.model_name, prompt)
        payload = {
            "model": self.model_name,
            "prompt": active_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": self._num_predict_for_model(self.model_name, max_tokens),
                "num_ctx": self.num_ctx,
            },
        }

        try:
            response = self._post("/api/generate", payload)
            self.last_request_time = time.time()
            return str(response.get("response", "")).strip()
        except Exception as exc:
            if self._should_retry_with_fallback(str(exc)):
                print(
                    f"[WARN] Ollama model '{self.model_name}' could not generate; "
                    f"retrying with '{self.fallback_model_name}'"
                )
                payload["model"] = self.fallback_model_name
                payload["prompt"] = self._prompt_for_model(self.fallback_model_name, prompt)
                payload["options"]["num_ctx"] = min(self.num_ctx, 4096)
                payload["options"]["num_predict"] = self._num_predict_for_model(self.fallback_model_name, max_tokens)
                try:
                    response = self._post("/api/generate", payload)
                    self.last_request_time = time.time()
                    return str(response.get("response", "")).strip()
                except Exception as fallback_exc:
                    return f"Error generating text with Ollama fallback: {fallback_exc}"
            return f"Error generating text with Ollama: {exc}"

    def _should_retry_with_fallback(self, error_message: str) -> bool:
        if not self.fallback_model_name or self.fallback_model_name == self.model_name:
            return False

        memory_error_markers = [
            "requires more system memory",
            "not enough memory",
            "out of memory",
        ]
        return any(marker in error_message.lower() for marker in memory_error_markers)

    def _prompt_for_model(self, model_name: str | None, prompt: str) -> str:
        """Disable Qwen3 thinking mode so Ollama returns answer text."""
        if model_name and model_name.lower().startswith("qwen3"):
            return f"/no_think\n{prompt}"
        return prompt

    def _num_predict_for_model(self, model_name: str | None, max_tokens: int) -> int:
        if model_name and model_name.lower().startswith("qwen3"):
            return max(max_tokens, 512)
        return max_tokens

    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """Extract entities from text using the local model."""
        prompt = f"""Extract entities from the following text. Return ONLY valid JSON as a list of objects with "entity" and "type" keys.

Text: {text}"""

        response = self.generate_text(prompt, max_tokens=512)
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            return []

        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            return []

        entities = []
        for item in parsed:
            if isinstance(item, dict) and item.get("entity"):
                entities.append({
                    "entity": str(item.get("entity")),
                    "type": str(item.get("type", "unknown")),
                })
        return entities

    def generate_graph_insights(self, graph_data: str) -> str:
        prompt = f"""Analyze the following knowledge graph data and provide key insights, patterns, and relationships.

Graph Data:
{graph_data}

Provide:
1. Key entities and their importance
2. Main relationships and patterns
3. Potential insights from the connections
4. Anomalies or interesting findings"""
        return self.generate_text(prompt, max_tokens=4096)

    def generate_query_response(self, question: str, context: str) -> str:
        prompt = f"""You are a precise data analysis assistant answering questions based on a local knowledge graph.

User Question: {question}

Relevant Graph Context:
{context}

CRITICAL INSTRUCTIONS:
1. EXHAUSTIVE REPORTING: You must NEVER skip, summarize, or truncate rows. If the context contains matching rows, you must list the relevant details for ALL of them.
2. NO SHORTCUTS: Do NOT use phrases like "etc.", "and so on", or "here are a few examples".
3. ONLY use the provided "Matched Row Context" as your source of truth.
4. If the answer is not present in the graph context, say that the graph does not contain enough information to answer. Do not use outside knowledge or the original file directly.
5. The context is already restricted to the columns selected for the graph. Consider every supplied row group before answering, and do not ignore later rows.

Each "Matched Row Context" is one row group/community from the original dataset. Use the row_fields inside the matched row group as the authoritative values for that row.
Based on the provided graph context, answer the user's question completely and exhaustively."""

        return self.generate_text(prompt, max_tokens=8192)

    def summarize_data(self, data: str, max_length: int = 500) -> str:
        prompt = f"""Provide a concise summary of the following data in {max_length} characters or less:

{data}"""
        return self.generate_text(prompt)

    def rephrase_question(self, question: str) -> str:
        prompt = f"""Rephrase the following question to be more specific and structured for querying a knowledge graph:

Question: {question}

Return ONLY the rephrased question, no other text."""
        return self.generate_text(prompt, temperature=0.3).strip()

    def generate_cypher_suggestion(self, question: str, graph_schema: str) -> str:
        prompt = f"""Given the following graph schema and question, suggest a Cypher query.

Graph Schema:
{graph_schema}

Question: {question}

Return ONLY the Cypher query, no other text."""
        return self.generate_text(prompt, temperature=0.3).strip()
