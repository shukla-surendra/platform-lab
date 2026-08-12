"""Leaderboard using a sorted set - the score IS the rank, maintained
by Redis on every write, so "top N" and "this player's rank" are O(log
N) reads instead of a sort-on-read over the whole player base.

Run against a Redis instance reachable at REDIS_HOST/REDIS_PORT:
    python3 leaderboard.py
"""

import os

import redis

r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    decode_responses=True,
)

BOARD = "leaderboard:weekly"


def record_score(player: str, score: int) -> None:
    r.zadd(BOARD, {player: score})


def top_n(n: int) -> list[tuple[str, float]]:
    return r.zrevrange(BOARD, 0, n - 1, withscores=True)


def rank_of(player: str) -> int | None:
    rank = r.zrevrank(BOARD, player)
    return None if rank is None else rank + 1  # 0-indexed -> human-facing


if __name__ == "__main__":
    r.delete(BOARD)

    for player, score in [("ana", 1500), ("bo", 2200), ("cy", 1800), ("dev", 2500)]:
        record_score(player, score)

    print("top 3:")
    for player, score in top_n(3):
        print(f"  {player:<5} {int(score)}")

    print(f"\ncy's rank: #{rank_of('cy')}")

    # ZINCRBY: bump a score without a read-modify-write round trip -
    # useful when many concurrent games are updating the same board.
    r.zincrby(BOARD, 400, "ana")
    print(f"ana's rank after +400: #{rank_of('ana')}")

    assert rank_of("dev") == 1, "dev (2500) should still be #1"
    print("\nleaderboard confirmed working")
