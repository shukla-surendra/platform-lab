"""
Practical tiktoken recipes: counting tokens for a full chat conversation
(not just one string), truncating text to a hard token budget, and batch
encoding many documents efficiently.
"""

import tiktoken


def num_tokens_from_messages(messages: list[dict], model: str = "gpt-4o-mini") -> int:
    """Count tokens for a chat completion request the way OpenAI's API does.

    A chat request isn't just the sum of each message's text — the API adds
    a small fixed overhead per message (role/name formatting) and per reply.
    Undercounting this is the most common reason people hit a context-window
    error despite their own encode(text) math checking out.
    """
    encoding = tiktoken.encoding_for_model(model)

    # Overhead differs slightly by model family; these values match the
    # gpt-3.5-turbo / gpt-4 / gpt-4o chat formats.
    tokens_per_message = 3
    tokens_per_name = 1

    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with "<|start|>assistant<|message|>"
    return num_tokens


def truncate_to_token_limit(text: str, max_tokens: int, model: str = "gpt-4o-mini") -> str:
    """Truncate text to at most `max_tokens` tokens, decoding back to a clean string.

    Naively slicing by character count risks cutting mid-token or wildly
    over/under-shooting the actual limit. Truncating the token list itself
    is exact.
    """
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return encoding.decode(tokens[:max_tokens])


def batch_token_counts(documents: list[str], model: str = "gpt-4o-mini") -> list[int]:
    """Count tokens for many documents without re-loading the encoding each time.

    encoding_for_model()/get_encoding() do real work (loading the merge
    table) — call it once and reuse the returned encoding object across
    every document, not per-document. tiktoken also exposes encode_batch()
    for encoding many strings in one call, which parallelizes internally.
    """
    encoding = tiktoken.encoding_for_model(model)
    token_lists = encoding.encode_batch(documents)
    return [len(tokens) for tokens in token_lists]


if __name__ == "__main__":
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "How many tokens is this conversation?"},
    ]
    print("chat tokens:", num_tokens_from_messages(messages))

    long_text = "Tokenization is fun! " * 50
    print("truncated:", truncate_to_token_limit(long_text, max_tokens=10))

    print("batch counts:", batch_token_counts(["hello world", "a much longer document here"]))
