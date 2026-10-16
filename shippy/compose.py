from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class Answer:
    answer: str
    quote: str
    proposed_action: str


@runtime_checkable
class LLMProvider(Protocol):
    def complete(self, prompt: str) -> str: ...


class MockLLM:
    def __init__(self, responses: dict[str, str]) -> None:
        self._responses = responses

    def complete(self, prompt: str) -> str:
        for key, value in self._responses.items():
            if key in prompt:
                return value
        raise ValueError(f"MockLLM has no response for prompt: {prompt[:100]!r}")


class BedrockLLM:
    def __init__(self) -> None:
        self._model = os.environ.get(
            "BEDROCK_MODEL_ID", "anthropic.claude-haiku-4-5-20251001-v1:0"
        )
        self._region = os.environ.get("BEDROCK_REGION", "us-east-1")
        self._token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "")

    def complete(self, prompt: str) -> str:
        from langchain_aws import ChatBedrockConverse
        from langchain_core.messages import HumanMessage

        llm = ChatBedrockConverse(
            model=self._model,
            bedrock_api_key=self._token,
            region_name=self._region,
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        return str(response.content)


def _build_prompt(query: str, chunks: list[dict]) -> str:
    context = "\n\n".join(chunk["text"] for chunk in chunks)
    return (
        f"You are an operations assistant. Answer the question using only the provided SOP excerpts.\n"
        f"Return a JSON object with exactly three keys: answer, quote, proposed_action.\n"
        f"The quote must be a verbatim substring from one of the excerpts.\n\n"
        f"SOP excerpts:\n{context}\n\n"
        f"Question: {query}\n\n"
        f"Respond with JSON only, no other text."
    )


def compose(query: str, chunks: list[dict], provider: LLMProvider) -> Answer:
    prompt = _build_prompt(query, chunks)
    raw = provider.complete(prompt)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned non-JSON: {raw[:200]!r}") from exc
    return Answer(
        answer=data["answer"],
        quote=data["quote"],
        proposed_action=data["proposed_action"],
    )
