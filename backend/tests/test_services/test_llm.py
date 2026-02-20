"""
Tests for LLMService — prompt building, model resolution.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm import LLMService


class TestLLMServicePromptBuilding:
    """_build_prompt — pure logic."""

    def test_build_prompt_includes_system_and_user(self):
        svc = LLMService()
        context = [
            {"content": "Chunk 1 text", "metadata": {"source": "doc.pdf", "page": 1}},
            {"content": "Chunk 2 text", "metadata": {"source": "doc.pdf"}},
        ]
        messages = svc._build_prompt("What is X?", context)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "[1]" in messages[1]["content"]
        assert "[2]" in messages[1]["content"]
        assert "What is X?" in messages[1]["content"]

    def test_build_prompt_with_custom_system(self):
        svc = LLMService()
        messages = svc._build_prompt("Q?", [], system_prompt="Custom system")
        assert messages[0]["content"] == "Custom system"

    def test_build_prompt_with_page_info(self):
        svc = LLMService()
        context = [{"content": "text", "metadata": {"source": "f.pdf", "page": 5}}]
        messages = svc._build_prompt("Q?", context)
        assert "(page 5)" in messages[1]["content"]

    def test_build_prompt_without_page_info(self):
        svc = LLMService()
        context = [{"content": "text", "metadata": {"source": "f.pdf"}}]
        messages = svc._build_prompt("Q?", context)
        assert "(page" not in messages[1]["content"]


class TestLLMServiceModelResolution:
    """_resolve_model — model name routing."""

    def test_openai_model_passes_through(self):
        svc = LLMService()
        assert svc._resolve_model("gpt-4o") == "gpt-4o"
        assert svc._resolve_model("gpt-4o-mini") == "gpt-4o-mini"

    def test_anthropic_model_gets_prefix(self):
        svc = LLMService()
        assert svc._resolve_model("claude-3.5-sonnet") == "anthropic/claude-3.5-sonnet"

    def test_ollama_model_passes_through(self):
        svc = LLMService()
        assert svc._resolve_model("ollama/llama3") == "ollama/llama3"

    def test_unknown_model_returns_as_is_with_openai_key(self):
        svc = LLMService()
        with patch("app.services.llm.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test"
            mock_settings.ollama_base_url = ""
            result = svc._resolve_model("custom-model")
        assert result == "custom-model"


class TestLLMServiceGenerate:
    """Generate / stream — with mocked litellm."""

    @patch("app.services.llm.litellm")
    async def test_generate_returns_content(self, mock_litellm):
        mock_choice = MagicMock()
        mock_choice.message.content = "Generated answer"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)

        svc = LLMService()
        result = await svc.generate("Q?", [{"content": "ctx", "metadata": {}}])
        assert result == "Generated answer"

    @patch("app.services.llm.litellm")
    async def test_structured_extract_returns_content(self, mock_litellm):
        mock_choice = MagicMock()
        mock_choice.message.content = '["entity1", "entity2"]'
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)

        svc = LLMService()
        result = await svc.structured_extract("Extract entities from X")
        assert result == '["entity1", "entity2"]'
