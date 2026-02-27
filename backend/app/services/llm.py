"""
LLM service — unified interface via LiteLLM for OpenAI, Anthropic, Ollama.
Supports both sync completion and async streaming.
"""

import logging
import re
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

    # Regex to detect ambiguous follow-up queries (Russian + English)
    _FOLLOWUP_PATTERN = re.compile(
        r"(подробнее|подробней|ещё|еще|больше|расскажи|объясни|"
        r"а\s+что|а\s+как|а\s+где|а\s+почему|это|этого|этом|этим|"
        r"tell me more|elaborate|explain|what about|more details)",
        re.IGNORECASE,
    )

    async def rewrite_query(
        self,
        query: str,
        history: list[dict],
        model: str = "gpt-4o-mini",
    ) -> str:
        """Rewrite ambiguous follow-up query using conversation history.

        Args:
            query: The user's follow-up query.
            history: Previous conversation messages [{"role": ..., "content": ...}].
            model: Model for rewriting (cheap/fast).

        Returns:
            Rewritten standalone query, or original if rewriting not needed.
        """
        if not history:
            return query

        # Only rewrite short or ambiguous queries
        is_short = len(query) < 80
        is_followup = bool(self._FOLLOWUP_PATTERN.search(query))
        if not (is_short or is_followup):
            return query

        # Take last 6 messages (3 turns) for context
        recent = history[-6:]
        history_text = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:300]}"
            for m in recent
        )

        prompt = (
            "You are a query rewriter. Given the conversation history below, "
            "rewrite the user's follow-up query into a complete standalone question "
            "that can be understood without the conversation context.\n\n"
            f"Conversation history:\n{history_text}\n\n"
            f"Follow-up query: {query}\n\n"
            "Rewritten standalone question (same language as follow-up):"
        )

        try:
            response = await litellm.acompletion(
                model=self._resolve_model(model),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=256,
            )
            rewritten = (response.choices[0].message.content or "").strip()
            if rewritten:
                logger.info(
                    "Query rewritten",
                    extra={"original": query, "rewritten": rewritten},
                )
                return rewritten
        except Exception as e:
            logger.warning("Query rewriting failed, using original: %s", e)

        return query

    async def generate(
        self,
        query: str,
        context: list[dict],
        model: str = "gpt-4o",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
        history: Optional[list[dict]] = None,
    ) -> str:
        """Generate a complete response (non-streaming)."""
        prompt = self._build_prompt(query, context, system_prompt, history)

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
        history: Optional[list[dict]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from LLM as an async generator."""
        prompt = self._build_prompt(query, context, system_prompt, history)

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
        history: Optional[list[dict]] = None,
    ) -> list[dict]:
        """Build chat messages with context for RAG.

        Message order: [system, *history, user(context + query)]
        """
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

        messages: list[dict] = [{"role": "system", "content": system}]

        # Insert conversation history between system and current turn
        if history:
            messages.extend(history)

        messages.append({
            "role": "user",
            "content": f"Context:\n{context_str}\n\nQuestion: {query}",
        })

        return messages

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
