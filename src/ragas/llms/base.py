from __future__ import annotations

import typing as t
import asyncio
from abc import ABC, abstractmethod
from functools import partial
from dataclasses import dataclass

from langchain_community.chat_models import AzureChatOpenAI, ChatOpenAI, ChatVertexAI
from langchain_community.llms import AzureOpenAI, OpenAI, VertexAI
from langchain_core.language_models import BaseLanguageModel
from langchain_core.outputs import LLMResult
from tenacity import stop_after_attempt  # for exponential backoff
from tenacity import retry, wait_random_exponential

if t.TYPE_CHECKING:
    from langchain_core.callbacks import Callbacks

    from ragas.llms.prompt import PromptValue


MULTIPLE_COMPLETION_SUPPORTED = [
    OpenAI,
    ChatOpenAI,
    AzureOpenAI,
    AzureChatOpenAI,
    ChatVertexAI,
    VertexAI,
]


def is_multiple_completion_supported(llm: BaseLanguageModel) -> bool:
    """Return whether the given LLM supports n-completion."""
    for llm_type in MULTIPLE_COMPLETION_SUPPORTED:
        if isinstance(llm, llm_type):
            return True
    return False


@dataclass
class BaseRagasLLM(ABC):
    def get_temperature(self, n: int) -> float:
        """Return the temperature to use for completion based on n."""
        return 0.3 if n > 1 else 1e-8

    @abstractmethod
    def generate_text(
        self,
        prompt: PromptValue,
        n: int = 1,
        temperature: float = 1e-8,
        stop: t.Optional[t.List[str]] = None,
        callbacks: Callbacks = [],
    ) -> LLMResult:
        ...

    @abstractmethod
    async def agenerate_text(
        self,
        prompt: PromptValue,
        n: int = 1,
        temperature: float = 1e-8,
        stop: t.Optional[t.List[str]] = None,
        callbacks: Callbacks = [],
    ) -> LLMResult:
        ...

    async def generate(
        self,
        prompt: PromptValue,
        n: int = 1,
        temperature: float = 1e-8,
        stop: t.Optional[t.List[str]] = None,
        callbacks: Callbacks = [],
        is_async: bool = True,
    ) -> LLMResult:
        """Generate text using the given event loop."""
        loop = asyncio.get_event_loop()

        if is_async:
            return await self.agenerate_text(
                prompt=prompt,
                n=n,
                temperature=temperature,
                stop=stop,
                callbacks=callbacks,
            )
        else:
            loop = asyncio.get_event_loop()
            generate_text = partial(
                self.generate_text,
                prompt=prompt,
                n=n,
                temperature=temperature,
                stop=stop,
                callbacks=callbacks,
            )
            return await loop.run_in_executor(None, generate_text)


@dataclass
class LangchainLLMWrapper(BaseRagasLLM):
    """
    A simple base class for RagasLLMs that is based on Langchain's BaseLanguageModel
    interface. it implements 2 functions:
    - generate_text: for generating text from a given PromptValue
    - agenerate_text: for generating text from a given PromptValue asynchronously
    """

    langchain_llm: BaseLanguageModel

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    def generate_text(
        self,
        prompt: PromptValue,
        n: int = 1,
        temperature: float = 1e-8,
        stop: t.Optional[t.List[str]] = None,
        callbacks: t.Optional[Callbacks] = None,
    ) -> LLMResult:
        temperature = self.get_temperature(n=n)
        if is_multiple_completion_supported(self.langchain_llm):
            return self.langchain_llm.generate_prompt(
                prompts=[prompt],
                n=n,
                temperature=temperature,
                stop=stop,
                callbacks=callbacks,
            )
        else:
            result = self.langchain_llm.generate_prompt(
                prompts=[prompt] * n,
                temperature=temperature,
                stop=stop,
                callbacks=callbacks,
            )
            # make LLMResult.generation appear as if it was n_completions
            # note that LLMResult.runs is still a list that represents each run
            generations = [[g[0] for g in result.generations]]
            result.generations = generations
            return result

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def agenerate_text(
        self,
        prompt: PromptValue,
        n: int = 1,
        temperature: float = 1e-8,
        stop: t.Optional[t.List[str]] = None,
        callbacks: t.Optional[Callbacks] = None,
    ) -> LLMResult:
        temperature = self.get_temperature(n=n)
        if is_multiple_completion_supported(self.langchain_llm):
            return await self.langchain_llm.agenerate_prompt(
                prompts=[prompt],
                n=n,
                temperature=temperature,
                stop=stop,
                callbacks=callbacks,
            )
        else:
            result = await self.langchain_llm.agenerate_prompt(
                prompts=[prompt] * n,
                temperature=temperature,
                stop=stop,
                callbacks=callbacks,
            )
            # make LLMResult.generation appear as if it was n_completions
            # note that LLMResult.runs is still a list that represents each run
            generations = [[g[0] for g in result.generations]]
            result.generations = generations
            return result
