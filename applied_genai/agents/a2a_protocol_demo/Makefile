PYTHON ?= python3

.PHONY: weather coordinator ask chat pull

# `uv run` reads pyproject.toml's `requires-python = ">=3.13"` and provisions that
# interpreter automatically (via `uv python install`) if it's not already on this
# machine -- no need to install Python 3.13 globally yourself.

pull:
	ollama pull qwen3.5:latest

weather:
	uv run python -m weather_agent

coordinator:
	uv run python -m coordinator_agent

ask:
	uv run python client.py "$(Q)"

chat:
	uv run python client.py
