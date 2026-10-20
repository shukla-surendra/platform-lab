# Appendix: Simple Agent Loop vs. Deep Agent

**Short answer: yes. For most use cases a simple loop with tools, MCP and a knowledge source is all you need.** A "deep agent" is that same loop with a few extra pieces added to handle long, messy tasks. It's not a different kind of thing.

## The simple agent (what you described)

```
while True:
    response = llm(messages, tools)        # tools = your functions + MCP + RAG search
    if response wants a tool:
        result = run_tool(...)
        messages.append(result)
    else:
        return response                    # done
```

This handles a lot:
- "Search the knowledge base and answer the question"
- "Check the pod status via MCP, then restart it"
- "Look up the customer, create a ticket, send an email"

These tasks take **2 to 10 steps**, the goal is clear, and the whole history fits in the context window.

## Where the simple loop breaks

Make the task bigger, like "Research 5 vendors, compare them, and write a 10-page report" or "Migrate this repo from library X to Y." Then problems show up:

| Problem | What happens in a simple loop |
|---|---|
| **Context fills up** | Each tool result (web pages, files, logs) piles up in `messages`. After 30 to 50 steps you hit the token limit, or the model gets confused by the noise. |
| **Loses the plan** | By step 25 the model forgets what it was trying to do and repeats work or stops early. |
| **No memory outside the chat** | Intermediate results only live in the message history, so it can't "save notes and come back later". |
| **One brain does everything** | The same context has to research, write code, review it and summarize, all mixed together. |

## What a "deep agent" adds (each piece fixes one problem above)

1. **Planning / todo tool.** The agent writes a todo list ("1. find vendors, 2. compare pricing...") and updates it as it goes. This keeps it on track. (Claude Code does exactly this.)
2. **Sub-agents.** The main agent hands a subtask like "research vendor A" to a child agent. The child uses its own fresh context, does 20 steps, and returns only a **short summary**. The main context stays clean.
3. **File system / scratchpad.** The agent writes notes and drafts to files instead of keeping everything in the conversation, and reads them back when needed. This is memory outside the context window.
4. **A detailed system prompt.** Long instructions on how to plan, when to delegate, and how to check its own work.

That's it. Underneath, it's **still the same loop**. The extra pieces are just more tools (`write_todos`, `spawn_subagent`, `write_file`, `read_file`).

## How to decide

- **Task takes under ~10 steps, and the input/output is clear?** → Simple loop. Don't overbuild.
- **Fixed sequence that's always the same (A → B → C)?** → You may not even need an agent. A plain workflow/pipeline that calls the LLM at each step is cheaper and more predictable.
- **Task is open-ended, takes dozens of steps, and reads lots of data?** → Add the deep-agent pieces, **one at a time, only when you see the problem**. For example, add a todo tool when it loses track, or sub-agents when the context gets too big.

A good rule: **start with the simple loop and only add complexity when you hit a real failure.** Many teams reach for LangGraph or deep-agent frameworks too early. For a RAG + MCP + 2 to 3 tools assistant, your simple loop is the right design.
