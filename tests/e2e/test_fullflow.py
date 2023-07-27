import pytest
from datasets import load_dataset

from ragas import evaluate
from ragas.metrics import answer_relevancy, context_relevancy, faithfulness
from ragas.metrics.critique import harmfulness


@pytest.mark.skip
def test_evaluate_e2e():
    ds = load_dataset("explodinggradients/fiqa", "ragas_eval")["baseline"]
    result = evaluate(
        ds.select(range(5)),
        metrics=[answer_relevancy, context_relevancy, faithfulness, harmfulness],
    )
    assert result is not None


def test_fail():
    assert 1 == 2
