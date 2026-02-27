"""
Tests for AI Advisor Chatbot — /advisor/chat endpoint.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.advisor import _extract_recommendation


class TestAdvisorChat:
    """POST /advisor/chat — conversational AI advisor."""

    async def test_new_session_creates_id(
        self, client: AsyncClient, mock_cache_service: AsyncMock
    ):
        """First message without session_id creates a new session."""
        with patch("app.api.v1.advisor.litellm") as mock_litellm:
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="Hello! I'm Serpent. What domain?"))
            ]
            mock_litellm.acompletion = AsyncMock(return_value=mock_response)

            response = await client.post(
                "/advisor/chat",
                json={"message": "Hi, I need help choosing a strategy"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0
        assert "reply" in data
        assert data["is_complete"] is False

    async def test_session_continuity(
        self, client: AsyncClient, mock_cache_service: AsyncMock
    ):
        """Sending session_id loads existing history from cache."""
        # Pre-populate session in cache
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! What domain?"},
        ]
        mock_cache_service.get_advisor_session.return_value = history

        with patch("app.api.v1.advisor.litellm") as mock_litellm:
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="Great, and how complex are your queries?"))
            ]
            mock_litellm.acompletion = AsyncMock(return_value=mock_response)

            response = await client.post(
                "/advisor/chat",
                json={
                    "session_id": "test-session-123",
                    "message": "I work in healthcare",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
        # Cache was checked for existing session (now scoped by user_id)
        mock_cache_service.get_advisor_session.assert_called_with("anonymous", "test-session-123")
        # Session was saved after response
        mock_cache_service.set_advisor_session.assert_called_once()

    async def test_recommendation_extraction(
        self, client: AsyncClient, mock_cache_service: AsyncMock
    ):
        """When LLM includes recommendation JSON, it's extracted."""
        reply_with_rec = (
            'Based on your needs, I recommend Corrective RAG.\n\n'
            '```json\n'
            '{"recommended": "corrective", "scores": {"corrective": 0.9, '
            '"hybrid": 0.7}, "reasoning": "High accuracy needed for medical",'
            ' "settings": {"relevance_threshold": 0.8}}\n'
            '```'
        )

        with patch("app.api.v1.advisor.litellm") as mock_litellm:
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content=reply_with_rec))
            ]
            mock_litellm.acompletion = AsyncMock(return_value=mock_response)

            response = await client.post(
                "/advisor/chat",
                json={"message": "I need medical document search with high accuracy"},
            )

        data = response.json()
        assert data["is_complete"] is True
        assert data["recommendation"] is not None
        assert data["recommendation"]["recommended"] == "corrective"

    async def test_llm_error_graceful_fallback(
        self, client: AsyncClient, mock_cache_service: AsyncMock
    ):
        """LLM failure returns graceful fallback message."""
        with patch("app.api.v1.advisor.litellm") as mock_litellm:
            mock_litellm.acompletion = AsyncMock(
                side_effect=Exception("API Error")
            )

            response = await client.post(
                "/advisor/chat",
                json={"message": "Hello"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "Hybrid" in data["reply"]  # Fallback recommends Hybrid


class TestExtractRecommendation:
    """_extract_recommendation() — JSON parsing from LLM output."""

    def test_extracts_inline_json(self):
        reply = 'I recommend: {"recommended": "hybrid", "scores": {"hybrid": 0.9}}'
        rec = _extract_recommendation(reply)
        assert rec is not None
        assert rec.recommended == "hybrid"

    def test_extracts_code_block_json(self):
        reply = (
            'My recommendation:\n```json\n'
            '{"recommended": "graph", "scores": {"graph": 0.85}, '
            '"reasoning": "Structured data"}\n'
            '```'
        )
        rec = _extract_recommendation(reply)
        assert rec is not None
        assert rec.recommended == "graph"

    def test_returns_none_when_no_json(self):
        reply = "I need more information about your use case."
        rec = _extract_recommendation(reply)
        assert rec is None

    def test_returns_none_on_malformed_json(self):
        reply = '{"recommended": broken json}'
        rec = _extract_recommendation(reply)
        assert rec is None
