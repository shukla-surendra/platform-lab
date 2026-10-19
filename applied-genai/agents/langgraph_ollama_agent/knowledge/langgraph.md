# LangGraph notes

LangGraph models an agent as a graph: nodes are functions (often calling an LLM or a
tool), edges define control flow, and a shared state object flows through every node.

A `StateGraph` is built by adding nodes, then edges. `add_conditional_edges` lets a
node's output decide which node runs next, which is how a ReAct loop is expressed: the
`agent` node calls the model, and `tools_condition` checks whether the response
contains tool calls; if so, route to a `tools` node, otherwise route to `END`.

Checkpointing gives a graph memory across runs. A checkpointer (SQLite, Postgres, or
in-memory) saves the state after every step, keyed by a `thread_id`. Passing the same
`thread_id` on a later invocation resumes exactly where the conversation left off, even
across separate process invocations.

`stream_mode="updates"` yields the output of each node as it finishes, instead of
waiting for the whole run to complete — the difference between showing "thinking..."
and showing nothing until the final answer.

A `recursion_limit` caps how many graph steps a single invocation can take, which is
the guardrail against a model stuck calling tools in a loop and never producing a final
answer.
