"""LLM provider factory. Every graph node asks for a model here instead of importing
`ChatOllama`/`ChatAnthropic` directly, so `LLM_PROVIDER=claude` in `.env` is the only change
needed to swap the whole agent onto Claude -- no code edits.
"""

from __future__ import annotations

from typing import Any

import config


def get_chat_model(**kwargs: Any):
    """Return a LangChain chat model for the configured provider.

    kwargs are passed through (e.g. `temperature=0`) and override config.py defaults.
    """
    if config.LLM_PROVIDER == "claude":
        from langchain_anthropic import ChatAnthropic

        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "LLM_PROVIDER=claude but ANTHROPIC_API_KEY is not set. Add it to .env, or set "
                "LLM_PROVIDER=ollama to run locally instead."
            )
        params = {
            "model": config.ANTHROPIC_MODEL,
            "temperature": config.MODEL_TEMPERATURE,
            "api_key": config.ANTHROPIC_API_KEY,
        }
        params.update(kwargs)
        return ChatAnthropic(**params)

    if config.LLM_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama

        params = {
            "model": config.OLLAMA_MODEL,
            "base_url": config.OLLAMA_BASE_URL,
            "temperature": config.MODEL_TEMPERATURE,
            # Ollama defaults to a 4096-token context window regardless of what the model
            # actually supports. diagnose's prompt (live context + several retrieved knowledge
            # passages) blows past that easily, silently truncating input -- which is a far more
            # likely cause of `.with_structured_output()` returning None than the model just
            # "getting it wrong." Every node's prompt here is well under 16K tokens.
            "num_ctx": config.OLLAMA_NUM_CTX,
        }
        params.update(kwargs)
        return ChatOllama(**params)

    raise ValueError(f"Unknown LLM_PROVIDER: {config.LLM_PROVIDER!r} (expected 'ollama' or 'claude')")


def structured_output_method() -> str:
    """Which method `.with_structured_output()` should use.

    Ollama's default JSON-schema-prompting mode is noticeably less reliable at nested/enum
    schemas on small local models than routing structured output through native tool-calling.
    Claude's tool-calling is reliable either way, so it only matters for the Ollama path.
    """
    return "function_calling" if config.LLM_PROVIDER == "ollama" else "auto"
