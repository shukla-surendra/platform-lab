"""Consistent hashing ring with virtual nodes, weights, and bounded replica lookups.

Uses SHA-256 (truncated to 64 bits) so hash distribution is stable across
processes and Python versions, unlike Python's salted built-in hash().
"""

from __future__ import annotations

import bisect
import hashlib
import threading
from dataclasses import dataclass, field


def _hash(key: str) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big")


@dataclass(frozen=True)
class Node:
    name: str
    weight: int = 1
    metadata: dict = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError(f"weight must be positive, got {self.weight}")


class ConsistentHashRing:
    """Maps keys to nodes on a hash ring, minimizing remapping on membership changes.

    Each node gets `base_replicas * node.weight` points on the ring, so
    heavier nodes receive proportionally more keys. Thread-safe: all mutating
    and lookup operations hold a single lock, since ring rebuilds are
    infrequent relative to lookups in most production workloads.
    """

    def __init__(self, nodes: list[Node] | None = None, base_replicas: int = 150) -> None:
        if base_replicas <= 0:
            raise ValueError(f"base_replicas must be positive, got {base_replicas}")
        self._base_replicas = base_replicas
        self._lock = threading.RLock()
        self._nodes: dict[str, Node] = {}
        self._ring: dict[int, str] = {}
        self._sorted_points: list[int] = []
        for node in nodes or []:
            self.add_node(node)

    def _points_for(self, node: Node) -> list[int]:
        replicas = self._base_replicas * node.weight
        return [_hash(f"{node.name}#{i}") for i in range(replicas)]

    def add_node(self, node: Node) -> None:
        with self._lock:
            if node.name in self._nodes:
                raise ValueError(f"node {node.name!r} already present")
            self._nodes[node.name] = node
            for point in self._points_for(node):
                if point in self._ring:
                    raise RuntimeError(
                        f"hash collision on ring for node {node.name!r}; "
                        "increase base_replicas variance or investigate key naming"
                    )
                self._ring[point] = node.name
            self._sorted_points = sorted(self._ring)

    def remove_node(self, name: str) -> None:
        with self._lock:
            node = self._nodes.pop(name, None)
            if node is None:
                raise KeyError(f"node {name!r} not found")
            for point in self._points_for(node):
                self._ring.pop(point, None)
            self._sorted_points = sorted(self._ring)

    def get_node(self, key: str) -> str:
        with self._lock:
            if not self._sorted_points:
                raise LookupError("ring is empty, no nodes registered")
            h = _hash(key)
            idx = bisect.bisect_right(self._sorted_points, h) % len(self._sorted_points)
            return self._ring[self._sorted_points[idx]]

    def get_nodes(self, key: str, count: int) -> list[str]:
        """Return up to `count` distinct nodes for `key`, walking the ring clockwise.

        Useful for replication: write to the first N distinct nodes past the
        key's point so a single node failure doesn't lose availability.
        """
        with self._lock:
            if count <= 0:
                raise ValueError(f"count must be positive, got {count}")
            if not self._sorted_points:
                raise LookupError("ring is empty, no nodes registered")

            distinct_count = len(self._nodes)
            count = min(count, distinct_count)
            h = _hash(key)
            start = bisect.bisect_right(self._sorted_points, h) % len(self._sorted_points)

            result: list[str] = []
            seen: set[str] = set()
            n = len(self._sorted_points)
            for offset in range(n):
                point = self._sorted_points[(start + offset) % n]
                name = self._ring[point]
                if name not in seen:
                    seen.add(name)
                    result.append(name)
                    if len(result) == count:
                        break
            return result

    @property
    def nodes(self) -> list[Node]:
        with self._lock:
            return list(self._nodes.values())

    def __len__(self) -> int:
        with self._lock:
            return len(self._nodes)

    def __contains__(self, name: str) -> bool:
        with self._lock:
            return name in self._nodes

    def key_distribution(self, sample_keys: list[str]) -> dict[str, int]:
        """Count how many of `sample_keys` land on each node — useful for testing skew."""
        counts: dict[str, int] = {name: 0 for name in self._nodes}
        for key in sample_keys:
            counts[self.get_node(key)] += 1
        return counts
