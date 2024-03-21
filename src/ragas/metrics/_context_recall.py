from __future__ import annotations

import logging
import typing as t
from dataclasses import dataclass, field

import numpy as np
from langchain_core.pydantic_v1 import BaseModel, Field, ValidationError

from ragas.llms.json_load import json_loader
from ragas.llms.prompt import Prompt
from ragas.llms.output_parser import get_json_format_instructions
from ragas.metrics.base import EvaluationMode, MetricWithLLM


if t.TYPE_CHECKING:
    from langchain_core.callbacks import Callbacks

    from ragas.llms.prompt import PromptValue

logger = logging.getLogger(__name__)


class ContextRecallClassificationAnswer(BaseModel):
    """The answer for a single sentence classification."""
    statement: str = Field(
        ...,
        description="the sentence extracted from the answer"
    )
    attributed: bool = Field(
        ...,
        description="whether the sentence can be attributed to the context"
    )
    reason: str = Field(
        ...,
        description="the reason why the sentence can or can not be attributed to the context"
    )

class ContextRecallClassificationAnswers(BaseModel):
    """List of classification answers for all sentences."""
    __root__: t.List[ContextRecallClassificationAnswer]

    def dicts(self):
        return self.dict()["__root__"]


_classification_output_instructions = get_json_format_instructions(ContextRecallClassificationAnswers)


CONTEXT_RECALL_RA = Prompt(
    name="context_recall",
    instruction="""Given a context, and an answer, analyze each sentence in the answer and classify if the sentence can be attributed to the given context or not. Use only "true" or "false" as a binary classification. Output json with reason.""",
    output_format_instruction=_classification_output_instructions,
    examples=[
        {
            "question": """What can you tell me about albert Albert Einstein?""",
            "context": """Albert Einstein (14 March 1879 - 18 April 1955) was a German-born theoretical physicist, widely held to be one of the greatest and most influential scientists of all time. Best known for developing the theory of relativity, he also made important contributions to quantum mechanics, and was thus a central figure in the revolutionary reshaping of the scientific understanding of nature that modern physics accomplished in the first decades of the twentieth century. His mass-energy equivalence formula E = mc2, which arises from relativity theory, has been called 'the world's most famous equation'. He received the 1921 Nobel Prize in Physics 'for his services to theoretical physics, and especially for his discovery of the law of the photoelectric effect', a pivotal step in the development of quantum theory. His work is also known for its influence on the philosophy of science. In a 1999 poll of 130 leading physicists worldwide by the British journal Physics World, Einstein was ranked the greatest physicist of all time. His intellectual achievements and originality have made Einstein synonymous with genius.""",
            "answer": """Albert Einstein born in 14 March 1879 was  German-born theoretical physicist, widely held to be one of the greatest and most influential scientists of all time. He received the 1921 Nobel Prize in Physics for his services to theoretical physics. He published 4 papers in 1905.  Einstein moved to Switzerland in 1895""",
            "classification": ContextRecallClassificationAnswers.parse_obj([
                ContextRecallClassificationAnswer(
                    statement="Albert Einstein, born on 14 March 1879, was a German-born theoretical physicist, widely held to be one of the greatest and most influential scientists of all time.",
                    reason="The date of birth of Einstein is mentioned clearly in the context.",
                    attributed=True,
                ),
                ContextRecallClassificationAnswer(
                    statement="He received the 1921 Nobel Prize in Physics for his services to theoretical physics.",
                    reason="The exact sentence is present in the given context.",
                    attributed=True,
                ),
                ContextRecallClassificationAnswer(
                    statement="He published 4 papers in 1905.",
                    reason="There is no mention about papers he wrote in the given context.",
                    attributed=False,
                ),
                ContextRecallClassificationAnswer(
                    statement="Einstein moved to Switzerland in 1895.",
                    reason="There is no supporting evidence for this in the given context.",
                    attributed=False,
                ),
            ]).dicts(),
        },
        {
            "question": """who won 2020 icc world cup?""",
            "context": """The 2022 ICC Men's T20 World Cup, held from October 16 to November 13, 2022, in Australia, was the eighth edition of the tournament. Originally scheduled for 2020, it was postponed due to the COVID-19 pandemic. England emerged victorious, defeating Pakistan by five wickets in the final to clinch their second ICC Men's T20 World Cup title.""",
            "answer": """England""",
            "classification": ContextRecallClassificationAnswers.parse_obj([
                ContextRecallClassificationAnswer(
                    statement="England won the 2022 ICC Men's T20 World Cup.",
                    reason="From context it is clear that England defeated Pakistan to win the World Cup.",
                    attributed=True,
                ),
            ]).dicts(),
        },
        {
            "question": """What is the primary fuel for the Sun?""",
            "context": """NULL""",
            "answer": """Hydrogen""",
            "classification": ContextRecallClassificationAnswers.parse_obj([
                ContextRecallClassificationAnswer(
                    statement="The Sun's primary fuel is hydrogen.",
                    reason="The context contains no information",
                    attributed=False,
                ),
            ]).dicts(),
        },
    ],
    input_keys=["question", "context", "answer"],
    output_key="classification",
    output_type="json",
)


@dataclass
class ContextRecall(MetricWithLLM):

    """
    Estimates context recall by estimating TP and FN using annotated answer and
    retrieved context.

    Attributes
    ----------
    name : str
    """

    name: str = "context_recall"  # type: ignore
    evaluation_mode: EvaluationMode = EvaluationMode.qcg  # type: ignore
    context_recall_prompt: Prompt = field(default_factory=lambda: CONTEXT_RECALL_RA)

    def _create_context_recall_prompt(self, row: t.Dict) -> PromptValue:
        qstn, ctx, gt = row["question"], row["contexts"], row["ground_truth"]
        ctx = "\n".join(ctx) if isinstance(ctx, list) else ctx

        return self.context_recall_prompt.format(question=qstn, context=ctx, answer=gt)

    def _compute_score(self, response: t.Any) -> float:
        if isinstance(response, dict) and "classification" in response:
            response = response["classification"]

        try:
            response = ContextRecallClassificationAnswers.parse_obj(response)
        except ValidationError as err:
            logger.warning(f"Could not parse LLM response: {response}")
            logger.warning(f"Error: {err}")
            return np.nan

        # TODO: real error handling and retry?
        # https://python.langchain.com/docs/modules/model_io/output_parsers/types/retry

        response = [
            1 if item.attributed else 0
            for item in response.__root__
        ]
        denom = len(response)
        numerator = sum(response)
        score = numerator / denom if denom > 0 else np.nan

        if np.isnan(score):
            logger.warning(
                "The LLM did not return a valid classification."
            )

        return score

    async def _ascore(self, row: t.Dict, callbacks: Callbacks, is_async: bool) -> float:
        assert self.llm is not None, "set LLM before use"

        result = await self.llm.generate(
            self._create_context_recall_prompt(row), callbacks=callbacks
        )
        response = await json_loader.safe_load(
            result.generations[0][0].text, self.llm, is_async=is_async
        )

        return self._compute_score(response)

    def adapt(self, language: str, cache_dir: str | None = None) -> None:
        assert self.llm is not None, "set LLM before use"

        logger.info(f"Adapting Context Recall to {language}")
        self.context_recall_prompt = self.context_recall_prompt.adapt(
            language, self.llm, cache_dir
        )

    def save(self, cache_dir: str | None = None) -> None:
        self.context_recall_prompt.save(cache_dir)


context_recall = ContextRecall()
