# Appendix: Why Do We Need a Graph in Agents?

**Short answer: you often don't.** A graph is just a way to write down *who decides what happens next*. In a simple loop, the LLM decides everything. In a graph, **you** decide some of it in code.

## The simple loop is already a tiny graph

```
        ┌──────────┐
 start →│   LLM    │── no tool call ──→ end
        └──────────┘
           ↑    │ tool call
           │    ↓
        ┌──────────┐
        │  Tools   │
        └──────────┘
```

Two nodes (LLM, Tools) and one decision ("did it ask for a tool?"). That's what LangGraph's `create_react_agent` builds for you. So "agent vs. graph" is a false choice. Every agent is a graph, and the only question is how many boxes you draw yourself.

## Why draw more boxes? Because some steps should NOT be up to the LLM

| Need | Simple loop (LLM decides) | Graph (you decide in code) |
|---|---|---|
| **Fixed order** ("always validate input, then search, then answer") | You *hope* the LLM follows the prompt | Edges force the order every time |
| **Branching** ("billing question → billing agent, tech question → tech agent") | One LLM with every tool, gets confused | A router node sends each request down the right path |
| **Loop limits** ("retry the SQL query up to 3 times") | Might loop forever or give up early | A counter in state plus a conditional edge |
| **Human approval** ("ask before restarting prod") | Hard to pause the loop mid-way | Built in: pause at a node, wait, resume |
| **Crash / resume** | Process dies, all progress lost | State is saved after each node (checkpointer), so it resumes from the last step |
| **Parallel work** ("search 5 sources at once") | Usually one tool at a time | Fan out to 5 nodes, then merge the results |
| **Debugging** | One long message list | You can see exactly which node ran, with what state |

## The core idea: predictability vs. flexibility

- **LLM decides** → flexible, handles surprises, but less predictable and harder to test.
- **Code decides (graph edges)** → predictable, testable, auditable, but rigid.

A graph lets you **mix the two**: the steps that *must* happen a certain way get fixed edges, and the steps that need judgment get an LLM node. In production (prod changes, money, customer data) you usually want more fixed edges.

## Example: an on-call agent

```
alert → [classify (LLM)] → is it critical?
            │ no → [summarize (LLM)] → post to Slack → end
            │ yes
            ↓
      [diagnose (LLM + MCP tools loop)]
            ↓
      [propose fix (LLM)]
            ↓
      [HUMAN APPROVAL]  ← pause here, resume when approved
            ↓
      [apply fix (tool)] → [verify] → failed? retry (max 2) → else end
```

You *could* put all of that in one prompt and a simple loop. But you could never *guarantee* it asks for approval, stops after 2 retries, or survives a restart. The graph guarantees it.

## How to decide

- **Q&A over a knowledge base, or a few tool calls** → simple loop. No graph needed.
- **You keep writing "ALWAYS do X before Y" in the prompt and it still sometimes skips it** → that's a sign to make it an edge.
- **You need approval, resume after a crash, parallel steps, or routing to different specialists** → use a graph.

Same rule as before: **start with the loop, and turn a step into a graph node only when you need a guarantee the LLM can't give you.**

See also: [Simple Agent Loop vs. Deep Agent](17-simple-loop-vs-deep-agent.md).
