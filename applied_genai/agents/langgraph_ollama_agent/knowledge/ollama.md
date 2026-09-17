# Ollama notes

Ollama runs open-weight models locally and exposes them over an HTTP API on port 11434
by default, with no cloud dependency once a model is pulled.

Not every model supports tool calling. Run `ollama show <model>` and check the
Capabilities section: a model needs `tools` listed to be usable with `bind_tools` in
LangChain. Models without it will either ignore the tool schema or hallucinate a tool
call in plain text instead of a real structured one.

`ChatOllama(model=..., base_url=...)` is the LangChain wrapper used to talk to a local
model as if it were any other chat model, including `.bind_tools(...)` for tool calling
and streaming support.

Context length matters for agent loops specifically because every tool call and its
result gets appended back into the message history — a long multi-step tool-calling
conversation can exceed a short context window even if the original question was
short.

Larger, newer local models generally follow tool-call schemas and multi-step
instructions more reliably than smaller ones, at the cost of slower inference and more
memory. Check `ollama list` for what's already pulled before downloading a new one.
