"""
RAG evaluation service using RAGAS metrics.
"""

import logging
from typing import Optional

logger = logging.getLogger("serpent.evaluation")


class EvaluationService:
    """Computes RAGAS quality metrics for RAG responses."""

    async def evaluate(
        self,
        query: str,
        answer: str,
        contexts: list[str],
        ground_truth: Optional[str] = None,
    ) -> dict[str, float]:
        """Evaluate a RAG response using RAGAS metrics.

        Returns dict with keys: faithfulness, context_precision,
        context_recall, answer_relevancy.
        """
        try:
            from ragas import evaluate as ragas_evaluate
            from ragas.metrics import (
                answer_relevancy,
                context_precision,
                context_recall,
                faithfulness,
            )
            from datasets import Dataset

            data = {
                "question": [query],
                "answer": [answer],
                "contexts": [contexts],
            }
            if ground_truth:
                data["ground_truth"] = [ground_truth]

            dataset = Dataset.from_dict(data)

            metrics = [faithfulness, answer_relevancy, context_precision]
            if ground_truth:
                metrics.append(context_recall)

            result = ragas_evaluate(dataset=dataset, metrics=metrics)

            scores = {}
            for key in ("faithfulness", "answer_relevancy", "context_precision", "context_recall"):
                if key in result:
                    scores[key] = round(float(result[key]), 4)

            return scores

        except ImportError:
            logger.warning("RAGAS not available, skipping evaluation")
            return {}
        except Exception as e:
            logger.error("RAGAS evaluation failed", extra={"error": str(e)})
            return {}
