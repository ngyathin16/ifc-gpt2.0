"""
LLM client factory for the IFC generation agent.

Uses gpt-5.4-pro via the Azure OpenAI Responses API endpoint.

Provides a single ``get_llm()`` function that returns a LangChain-compatible
chat model backed by the Azure OpenAI **Responses API** endpoint.

``gpt-5.4-pro`` only supports ``POST /openai/responses`` — NOT the
Chat Completions endpoint used by ``AzureChatOpenAI``.  This module wraps
that API in a minimal ``BaseChatModel`` subclass so the rest of the agent
can call ``.invoke()`` / ``.stream()`` as normal.

Environment variables (set in .env):
    AZURE_OPENAI_API_KEY       — Azure resource key
    AZURE_OPENAI_ENDPOINT      — Full Responses API URL, e.g.
                                 https://ov-virginia.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview
    AZURE_OPENAI_DEPLOYMENT    — Model name / deployment (e.g. gpt-5.4-pro)
    OPENAI_API_KEY             — Fallback plain OpenAI key
    OPENAI_BASE_URL            — Fallback base URL
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
_llm_instance: BaseChatModel | None = None


def reset_llm() -> None:
    """Clear the cached LLM singleton. Call this after changing env vars."""
    global _llm_instance
    _llm_instance = None


# ---------------------------------------------------------------------------
class AzureResponsesChatModel(BaseChatModel):
    """Minimal LangChain BaseChatModel backed by the Azure OpenAI Responses API.

    The Responses API schema differs from Chat Completions:
      - Input:  {"model": ..., "input": [{"role": ..., "content": ...}]}
      - Output: {"output": [{"type": "message", "content": [{"text": ...}]}]}
    """

    api_key: str
    endpoint: str          # full URL including api-version query string
    model: str
    temperature: float = 0.2
    request_timeout: int = 180

    @property
    def _llm_type(self) -> str:
        return "azure-responses-api"

    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """Convert LangChain messages to Responses API input format."""
        converted: List[Dict[str, Any]] = []
        for m in messages:
            if isinstance(m, SystemMessage):
                converted.append({"role": "developer", "content": str(m.content)})
            elif isinstance(m, HumanMessage):
                converted.append({"role": "user", "content": str(m.content)})
            elif isinstance(m, AIMessage):
                converted.append({"role": "assistant", "content": str(m.content)})
            else:
                converted.append({"role": "user", "content": str(m.content)})
        return converted

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        import requests

        payload: Dict[str, Any] = {
            "model": self.model,
            "input": self._convert_messages(messages),
            "stream": True,
            "reasoning": {"effort": "medium"},
        }
        # "stop" is NOT supported by the Responses API for reasoning models
        if stop:
            logger.warning("[llm] Ignoring unsupported 'stop' parameter for Responses API")

        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

        logger.info(f"[llm] Responses API (streaming) → {self.endpoint[:60]}...")

        # Use streaming to avoid read-timeout on long generations.
        # The server sends SSE events as tokens are produced, keeping
        # the connection alive.  We accumulate the text content.
        import json as _json

        resp = requests.post(
            self.endpoint, json=payload, headers=headers,
            timeout=(30, self.request_timeout),   # (connect, read-between-chunks)
            stream=True,
        )

        if not resp.ok:
            error_body = resp.text[:1000]
            logger.error("[llm] Azure Responses API %s: %s", resp.status_code, error_body)
            raise ValueError(
                f"Azure Responses API error {resp.status_code}: {error_body}"
            )

        text = ""
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data_str = line[len("data:"):].strip()
            if data_str == "[DONE]":
                break
            try:
                event = _json.loads(data_str)
            except _json.JSONDecodeError:
                continue

            # Responses API stream events have type "response.output_text.delta"
            # with a "delta" field containing the text chunk.
            etype = event.get("type", "")
            if etype == "response.output_text.delta":
                text += event.get("delta", "")
            elif etype == "response.completed":
                # Final event — extract full text if we missed deltas
                output = event.get("response", {}).get("output", [])
                if not text and output:
                    for item in output:
                        if item.get("type") == "message":
                            for part in item.get("content", []):
                                if isinstance(part, dict):
                                    text += part.get("text", "")
                                elif isinstance(part, str):
                                    text += part

        resp.close()

        if not text:
            raise ValueError("Azure Responses API returned empty response (streaming)")

        message = AIMessage(content=text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])


# ---------------------------------------------------------------------------
def extract_text(response) -> str:
    """Extract plain text from an LLM response, handling both string and list content blocks."""
    content = response.content if hasattr(response, "content") else str(response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts) if parts else str(content)
    return str(content)


# ---------------------------------------------------------------------------
def get_llm(temperature: float = 0.2) -> BaseChatModel:
    """Return a cached LangChain chat-model instance.

    Uses the Azure Responses API when ``AZURE_OPENAI_API_KEY`` is set,
    otherwise falls back to ``langchain_openai.ChatOpenAI``.

    Args:
        temperature: Sampling temperature (lower = more deterministic).

    Returns:
        A ``BaseChatModel`` instance ready for ``.invoke()``.
    """
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    azure_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_endpoint = os.getenv(
        "AZURE_OPENAI_ENDPOINT",
        "https://ov-virginia.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview",
    )
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-pro")

    if azure_key:
        logger.info(
            f"[llm] Using Azure Responses API: model={azure_deployment}"
        )
        _llm_instance = AzureResponsesChatModel(
            api_key=azure_key,
            endpoint=azure_endpoint,
            model=azure_deployment,
            temperature=temperature,
            request_timeout=600,
        )
        return _llm_instance

    # Fallback: plain OpenAI-compatible
    openai_key = os.getenv("OPENAI_API_KEY", "")
    openai_base = os.getenv("OPENAI_BASE_URL", "")

    if not openai_key:
        raise RuntimeError(
            "No LLM credentials found. Set AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT "
            "or OPENAI_API_KEY in your .env file."
        )

    logger.info("[llm] Falling back to plain OpenAI endpoint")

    from langchain_openai import ChatOpenAI

    kwargs: dict = {"temperature": temperature, "model": "gpt-5.4-pro"}
    if openai_key:
        kwargs["api_key"] = openai_key
    if openai_base:
        kwargs["base_url"] = openai_base

    _llm_instance = ChatOpenAI(**kwargs)
    return _llm_instance
