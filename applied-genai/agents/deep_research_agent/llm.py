"""Chat model factory, so the main agent and subagents can use different OpenAI models."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

import config


def get_chat_model(model: str | None = None) -> ChatOpenAI:
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set (see .env.example).")
    # No temperature: GPT-5-family reasoning models only accept the default.
    return ChatOpenAI(model=model or config.OPENAI_MODEL, api_key=config.OPENAI_API_KEY)
