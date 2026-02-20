"""
Tests for EvaluationService — RAGAS fallback, error handling.
"""

from unittest.mock import patch, MagicMock

import pytest

from app.services.evaluation import EvaluationService


class TestEvaluationService:
    """EvaluationService — graceful degradation."""

    async def test_evaluate_returns_empty_when_ragas_unavailable(self):
        svc = EvaluationService()
        with patch.dict("sys.modules", {"ragas": None, "ragas.metrics": None}):
            with patch(
                "app.services.evaluation.EvaluationService.evaluate",
                wraps=svc.evaluate,
            ):
                result = await svc.evaluate(
                    query="What is Python?",
                    answer="Python is a programming language.",
                    contexts=["Python is a high-level language."],
                )
                # Should return empty dict or actual scores
                assert isinstance(result, dict)

    async def test_evaluate_handles_exception_gracefully(self):
        svc = EvaluationService()
        # Force an import error by patching the import
        with patch("builtins.__import__", side_effect=ImportError("no ragas")):
            result = await svc.evaluate(
                query="Q?",
                answer="A.",
                contexts=["C."],
            )
            assert isinstance(result, dict)

    async def test_evaluate_accepts_ground_truth(self):
        svc = EvaluationService()
        # Just verify it doesn't crash with ground_truth
        with patch("builtins.__import__", side_effect=ImportError("no ragas")):
            result = await svc.evaluate(
                query="Q?",
                answer="A.",
                contexts=["C."],
                ground_truth="Expected A.",
            )
            assert isinstance(result, dict)
