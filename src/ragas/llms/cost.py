import typing as t
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import ChatResult, LLMResult, ChatGeneration
from langchain_core.pydantic_v1 import BaseModel, Field

from ragas.utils import get_from_dict


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    model: t.Optional[str] = None

    def __add__(self, y: "TokenUsage") -> "TokenUsage":
        if self.model == y.model or (self.model is None and y.model is None):
            return TokenUsage(
                input_tokens=self.input_tokens + y.input_tokens,
                output_tokens=self.output_tokens + y.output_tokens,
            )
        else:
            raise ValueError("Cannot add TokenUsage objects with different models")

    def cost(
        self,
        cost_per_input_token: float,
        cost_per_output_token: t.Optional[float] = None,
    ) -> float:
        if cost_per_output_token is None:
            cost_per_output_token = cost_per_input_token

        return (
            self.input_tokens * cost_per_input_token
            + self.output_tokens * cost_per_output_token
        )

    def __eq__(self, other: "TokenUsage") -> bool:
        return (
            self.input_tokens == other.input_tokens
            and self.output_tokens == other.output_tokens
            and self.is_same_model(other)
        )

    def is_same_model(self, other: "TokenUsage") -> bool:
        if self.model is None and other.model is None:
            return True
        elif self.model == other.model:
            return True
        else:
            return False


def parse_llm_result(llm_result: t.Union[LLMResult, ChatResult]) -> TokenUsage:
    # OpenAI like interfaces
    if llm_result.llm_output != {} and llm_result.llm_output is not None:
        llm_output = llm_result.llm_output
        output_tokens = get_from_dict(llm_output, "token_usage.completion_tokens", 0)
        input_tokens = get_from_dict(llm_output, "token_usage.input_tokens", 0)

        return TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)

    elif llm_result.llm_output == {}:
        token_usages = []
        for gs in llm_result.generations:
            for g in gs:
                if isinstance(g, ChatGeneration):
                    if g.message.response_metadata != {}:
                        # Anthropic
                        token_usages.append(
                            TokenUsage(
                                input_tokens=get_from_dict(
                                    g.message.response_metadata,
                                    "usage.input_tokens",
                                    0,
                                ),
                                output_tokens=get_from_dict(
                                    g.message.response_metadata,
                                    "usage.output_tokens",
                                    0,
                                ),
                            )
                        )

        print(token_usages)
        return sum(token_usages, TokenUsage(input_tokens=0, output_tokens=0))
    else:
        return TokenUsage(input_tokens=0, output_tokens=0)


class CostCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        self.usage_data: t.List[TokenUsage] = []
        self.llm_result_parser: t.Callable[[LLMResult], TokenUsage] = parse_llm_result

    def on_llm_end(self, response: LLMResult, **kwargs: t.Any) -> None:
        pass

    def get_usage_data(self):
        return self.usage_data
