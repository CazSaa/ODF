from collections import deque
from typing import Iterator

from dd import cudd
from dd.cudd import Function


def dfs_nodes_with_complement(
        root: cudd.Function, is_complement: bool
) -> Iterator[tuple[Function, bool]]:
    """
    Generator that traverses the BDD in reverse-topological order in a
    non-recursive manner. For each node it yields a tuple: (node, complemented)
    where 'complemented' is True if an odd number of complemented edges were taken
    on the path from the original root to 'node'.

    Note:
      - Each node supports a "negated" attribute (True if the pointer is complemented).
      - Each node supports a "regular" property that returns the underlying (uncomplemented) node.
    """
    # Each stack element is a tuple: (node, complement_flag, visited_flag)
    stack = deque([(root, is_complement, False)])
    yielded = set()  # To avoid yielding the same (node, complement) pair more than once.
    iters = 0
    max_len = 0

    while stack:
        iters += 1
        max_len = max(max_len, len(stack))
        node, comp, visited = stack.pop()
        if (node, comp) in yielded:
            continue
        if visited:
            yielded.add((node, comp))
            yield node, comp
            continue

        # Mark the current node as visited
        stack.append((node, comp, True))

        # Terminal node?
        if node.var is None:
            continue

        # Process children (both low and high children)
        for child in (node.low, node.high):
            new_comp = comp ^ child.negated  # toggle complement flag if edge is complemented

            child_regular = child.regular
            stack.append((child_regular, new_comp, False))
