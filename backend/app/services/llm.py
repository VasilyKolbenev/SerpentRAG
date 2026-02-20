"""
LLM service — unified interface via LiteLLM for OpenAI, Anthropic, Ollama.
Supports both sync completion and async streaming.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Optional

import litellm

from app.config import settings

logger = logging.getLogger("serpent.llm")

# Configure LiteLLM
litellm.drop_params = True

if settings.openai_api_key:
    litellm.openai_key = settings.openai_api_key
if settings.anthropic_api_key:
    litellm.anthropic_key = settings.anthropic_api_key


class LLMService:
    """Unified LLM interface supporting multiple providers."""

    CITATION_SYSTEM_PROMPT = (
        "You are a helpful research assistant. Answer the user's question based on "
        "the provided context. Always cite your sources using [1], [2], etc. markers "
        "corresponding to the context chunks provided. If the context does not contain "
        "enough information, say so honestly. Be concise and precise."
    )

    async def generate(
        self,
        query: str,
        context: list[dict],
        model: str = "gpt-4o",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate a complete response (non-streaming)."""
        prompt = self._build_prompt(query, context, system_prompt)

        try:
            response = await litellm.acompletion(
                model=self._resolve_model(model),
                messages=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("LLM generation failed", extra={"model": model, "error": str(e)})
            raise

    async def stream_generate(
        self,
        query: str,
        context: list[dict],
        model: str = "gpt-4o",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from LLM as an async generator."""
        prompt = self._build_prompt(query, context, system_prompt)

        try:
            response = await litellm.acompletion(
                model=self._resolve_model(model),
                messages=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content

        except Exception as e:
            logger.error(
                "LLM streaming failed", extra={"model": model, "error": str(e)}
            )
            raise

    async def structured_extract(
        self,
        prompt: str,
        model: str = "gpt-4o",
        temperature: float = 0.0,
    ) -> str:
        """Call LLM for structured extraction (entities, planning, etc.)."""
        try:
            response = await litellm.acompletion(
                model=self._resolve_model(model),
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=4096,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(
                "LLM extraction failed", extra={"model": model, "error": str(e)}
            )
            raise

    def _build_prompt(
        self,
        query: str,
        context: list[dict],
        system_prompt: Optional[str] = None,
    ) -> list[dict]:
        """Build chat messages with context for RAG."""
        system = system_prompt or self.CITATION_SYSTEM_PROMPT

        context_parts = []
        for i, chunk in enumerate(context, 1):
            source = chunk.get("metadata", {}).get("source", "unknown")
            page = chunk.get("metadata", {}).get("page", "")
            page_info = f" (page {page})" if page else ""
            context_parts.append(
                f"[{i}] {chunk['content']}\n  — Source: {source}{page_info}"
            )

        context_str = "\n\n".join(context_parts)

        return [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"Context:\n{context_str}\n\nQuestion: {query}",
            },
        ]

    def _resolve_model(self, model: str) -> str:
        """Resolve model name to LiteLLM-compatible format."""
        # Ollama models need prefix
        if model.startswith("ollama/") or model.startswith("ollama_chat/"):
            return model

        # Check if it's a known provider model
        known_openai = {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"}
        known_anthropic = {"claude-3-haiku-20240307", "claude-3-sonnet-20240229",
                           "claude-3-opus-20240229", "claude-3-5-sonnet-20241022",
                           "claude-3-5-haiku-20241022"}

        if model in known_openai:
            return model
        if model in known_anthropic:
            return f"anthropic/{model}"

        # If Ollama URL is set and model isn't recognized, try Ollama
        if settings.ollama_base_url and not settings.openai_api_key:
            return f"ollama/{model}"

        return model
