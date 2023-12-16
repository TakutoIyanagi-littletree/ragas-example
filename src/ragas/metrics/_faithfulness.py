from __future__ import annotations

import typing as t
from dataclasses import dataclass

import numpy as np
from langchain.callbacks.manager import CallbackManager, trace_as_chain_group
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

from ragas.llms.prompt import Prompt
from ragas.metrics.base import EvaluationMode, MetricWithLLM
from ragas.utils import json_loader

if t.TYPE_CHECKING:
    from datasets import Dataset
    from langchain.callbacks.base import Callbacks


LONG_FORM_ANSWER_PROMPT = HumanMessagePromptTemplate.from_template(
    """\
Create one or more statements from each sentence in the given answer.

question: Who was  Albert Einstein and what is he best known for?
answer: He was a German-born theoretical physicist, widely acknowledged to be one of the greatest and most influential physicists of all time. He was best known for developing the theory of relativity, he also made important contributions to the development of the theory of quantum mechanics.
statements in json:
{{
    "statements": [
        "Albert Einstein was born in Germany.",
        "Albert Einstein was best known for his theory of relativity."
    ]
}}

question: Cadmium Chloride is slightly soluble in this chemical, it is also called what?
answer: alcohol
statements in json:
{{
    "statements": [
        "Cadmium Chloride is slightly soluble in alcohol."
    ]
}}

question: Were Hitler and Benito Mussolini of the same nationality?
answer: Sorry, I can't provide answer to that question.
statements in json:
{{
    "statements": []
}}

question:{question}
answer: {answer}
statements in json:"""  # noqa: E501
)


NLI_STATEMENTS_MESSAGE = HumanMessagePromptTemplate.from_template(
    """
 Natural language inference. Only use "Yes" or "No" as verdict.

Context:
John is a student at XYZ University. He is pursuing a degree in Computer Science. He is enrolled in several courses this semester, including Data Structures, Algorithms, and Database Management. John is a diligent student and spends a significant amount of time studying and completing assignments. He often stays late in the library to work on his projects.
statement_1: John is majoring in Biology.
statement_2: John is taking a course on Artificial Intelligence. 
statement_3: John is a dedicated student. 
statement_4: John has a part-time job.
Answer:
[
    {{
        "statement_1": "John is majoring in Biology.",
        "reason": "John's major is explicitly mentioned as Computer Science. There is no information suggesting he is majoring in Biology.",
        "verdict": "No"
    }},
    {{
        "statement_2": "John is taking a course on Artificial Intelligence.",
        "reason": "The context mentions the courses John is currently enrolled in, and Artificial Intelligence is not mentioned. Therefore, it cannot be deduced that John is taking a course on AI.",
        "verdict": "No"
    }},
    {{
        "statement_3": "John is a dedicated student.",
        "reason": "The context states that he spends a significant amount of time studying and completing assignments. Additionally, it mentions that he often stays late in the library to work on his projects, which implies dedication.",
        "verdict": "Yes"
    }},
    {{
        "statement_4": "John has a part-time job.",
        "reason": "There is no information given in the context about John having a part-time job.",
        "verdict": "No"
    }}
]

Context:
Photosynthesis is a process used by plants, algae, and certain bacteria to convert light energy into chemical energy.
statement_1: Albert Einstein was a genius.
Answer:
[
     {{
        "statement_1": "Albert Einstein was a genius.",
        "reason": "The context and statement are unrelated"
        "verdict": "No"
    }}
]

Context:
Albert Einstein was a German-born theoretical physicist who is widely held to be one of the greatest and most influential scientists of all time.
statement_1: Nil
Answer:
[
     {{
        "statement_1": "Nil",
        "reason": "The statement is invalid",
        "verdict": "No"
    }}
]


context:
{context}
statements:
{statements}
Answer:
"""  # noqa: E501
)


@dataclass
class Faithfulness(MetricWithLLM):
    name: str = "faithfulness"  # type: ignore
    evaluation_mode: EvaluationMode = EvaluationMode.qac  # type: ignore
    batch_size: int = 15

    def ascore(
        self: t.Self,
        data_row: t.Dict,
        callbacks: t.Optional[Callbacks] = None,
    ) -> float:
        """
        returns the NLI score for each (q, c, a) pair
        """
        assert self.llm is not None, "LLM is not set"

        question, answer, contexts = (
            data_row["question"],
            data_row["answer"],
            data_row["contexts"],
        )

        # extract statements from answer given the question
        human_prompt = LONG_FORM_ANSWER_PROMPT.format(question=question, answer=answer)
        p = Prompt(
            chat_prompt_template=ChatPromptTemplate.from_messages([human_prompt])
        )
        result = self.llm.generate_text(p, callbacks=callbacks)

        # check if the statements are support in the contexts
        contexts_str: str = "\n".join(contexts)
        statements = json_loader.safe_load(result.generations[0][0].text, self.llm).get(
            "statements", []
        )
        statements = statements if statements != [] else ["Nil"]
        statements_str: str = "\n".join(
            [f"statement_{i+1}: {st}" for i, st in enumerate(statements)]
        )
        human_prompt = NLI_STATEMENTS_MESSAGE.format(
            context=contexts_str, statements=statements_str
        )
        p = Prompt(
            chat_prompt_template=ChatPromptTemplate.from_messages([human_prompt])
        )
        result = self.llm.generate_text(p, callbacks=callbacks)

        # check the verdicts and compute the score
        output = result.generations[0][0]
        verdict_score_map = {"yes": 1, "no": 0, "null": np.nan}
        output = json_loader.safe_load(output.text, self.llm)
        output = output if isinstance(output, list) else []
        faithful_statements = sum(
            verdict_score_map.get(dict.get("verdict", "").lower(), np.nan)
            for dict in output
        )
        num_statements = len(output)
        if num_statements:
            score = faithful_statements / num_statements
        else:
            score = np.nan

        return score


faithfulness = Faithfulness()
