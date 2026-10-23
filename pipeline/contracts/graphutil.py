"""Cycle checking and dependency-first topological wave scheduling."""
from __future__ import annotations

from collections import deque


def assert_acyclic(edges: list[tuple[str, str]]) -> None:
    """
    Verify directed graph has no cycles.
    Convention: edge (dependent, dependency) means `dependent` depends on `dependency`.
    """
    unique_edges = list(dict.fromkeys(edges))
    nodes = {n for e in unique_edges for n in e}
    adj: dict[str, list[str]] = {n: [] for n in nodes}
    indeg: dict[str, int] = {n: 0 for n in nodes}

    for dependent, dependency in unique_edges:
        if dependent == dependency:
            raise ValueError(f"dependency cycle: self-loop on {dependent}")
        adj[dependency].append(dependent)
        indeg[dependent] += 1

    queue = deque(sorted(n for n, d in indeg.items() if d == 0))
    visited = 0
    while queue:
        curr = queue.popleft()
        visited += 1
        for nxt in sorted(adj[curr]):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)

    if visited != len(nodes):
        cycling = sorted(n for n, d in indeg.items() if d > 0)
        raise ValueError(f"dependency cycle detected among: {', '.join(cycling)}")


def topological_waves(nodes: set[str], dependency_edges: list[tuple[str, str]]) -> list[list[str]]:
    """
    Group nodes into parallel execution waves.
    Edge (dependent, dependency) means `dependency` MUST be built and merged before `dependent`.
    Wave 0 contains leaf nodes with zero dependencies; Wave k depends only on Waves < k.
    """
    if not nodes:
        return []
    filtered_edges = [(a, b) for a, b in dependency_edges if a in nodes and b in nodes]
    assert_acyclic(filtered_edges)
    unique_edges = list(dict.fromkeys(filtered_edges))

    adj: dict[str, list[str]] = {n: [] for n in nodes}
    indeg: dict[str, int] = {n: 0 for n in nodes}
    for dependent, dependency in unique_edges:
        adj[dependency].append(dependent)
        indeg[dependent] += 1

    current_wave = sorted(n for n, d in indeg.items() if d == 0)
    waves: list[list[str]] = []
    while current_wave:
        waves.append(current_wave)
        next_wave: list[str] = []
        for u in current_wave:
            for v in sorted(adj[u]):
                indeg[v] -= 1
                if indeg[v] == 0:
                    next_wave.append(v)
        current_wave = sorted(next_wave)
    return waves
