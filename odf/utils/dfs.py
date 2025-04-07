from collections import deque
from typing import Iterator, Callable, Set, Tuple

from dd import cudd, cudd_add
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


def dfs_mtbdd_terminals(root: cudd_add.Function) -> Iterator[float]:
    """
    Generator that traverses an ADD using DFS and yields the values of all
    terminal nodes encountered.

    Args:
        root: The root node of the ADD to traverse.

    Yields:
        The floating-point values of the terminal nodes.
    """
    stack = deque([root])
    visited: set[Function] = set()

    while stack:
        node = stack.pop()

        if node in visited:
            continue
        visited.add(node)

        # Check if it's a terminal node (leaf)
        if node.var is None:
            yield node.value  # ADD terminal nodes have a 'value' attribute
            continue

        # Push children onto the stack if they exist
        # ADDs do not have complemented edges, so we directly use low/high
        if node.low is not None:
            stack.append(node.low)
        if node.high is not None:
            stack.append(node.high)


# Define predicate type
NodeTypePredicate = Callable[[Function], bool]


def find_config_reflection_nodes(
        root: Function,
        is_op_node: NodeTypePredicate
) -> Iterator[Tuple[Function, bool]]:
    """
    Generator that traverses the BDD using DFS to find nodes that are direct
    children of an Object Property (OP) node but are not OP nodes themselves.

    Args:
        root: The root node of the BDD to traverse.
        is_op_node: A predicate function that takes a BDD node (Function)
                    and returns True if it's an Object Property node,
                    False otherwise. This function should handle terminal
                    nodes correctly (e.g., return False).

    Yields:
        Tuples of (node, complemented_state), where node is the BDD node
        (Function object) satisfying the condition, and complemented_state
        is True if the node was reached via an odd number of complemented edges
        from the root.
    """
    # Stack stores tuples: (node_regular, parent_is_op: bool, complement_flag: bool)
    # Start with root's regular form and assume initial complement state is False
    initial_complement_state = root.negated
    stack = deque([(root.regular, True, initial_complement_state)])
    # Visited stores tuples: (node_regular, parent_is_op: bool, complement_flag: bool)
    # This prevents processing the same node in the same parent context multiple times.
    visited: Set[Tuple[Function, bool, bool]] = set()

    while stack:
        current_node, parent_is_op, complement_flag = stack.pop()

        # Check if already visited in this specific context (node + parent type)
        if (current_node, parent_is_op, complement_flag) in visited:
            continue
        visited.add((current_node, parent_is_op, complement_flag))

        # Determine if the current node is an OP node
        # The predicate should handle terminals (e.g., return False)
        current_is_op = is_op_node(current_node)

        # Yield Check: Yield if parent was OP and current is not OP
        if parent_is_op and not current_is_op:
            yield current_node, complement_flag
        if not current_is_op:
            # If current is not OP, we don't need to traverse further.
            continue

        # Push children onto the stack with the current node's OP status
        # Note: We use current_node.low which might be a complemented pointer,
        # but we push its .regular form onto the stack.
        # Update complement flag based on the edge taken.
        high_child = current_node.high
        low_child = current_node.low
        new_comp_low = complement_flag ^ low_child.negated

        stack.append((high_child, current_is_op, complement_flag))
        stack.append((low_child.regular, current_is_op, new_comp_low))


def find_paths_to_min_terminal(root: cudd_add.Function) -> tuple[
    list[dict[str, bool]], float]:
    """
    Finds all paths from the root to terminal node with the minimum value in an ADD/MTBDD.

    Args:
        root: The root node of the ADD/MTBDD.

    Returns:
        A list of dictionaries. Each dictionary represents a path mapping variable names (str) to boolean assignments (True for high,
        False for low) that lead to a terminal node with the minimum value.
    """
    min_value = None
    min_paths = []
    stack = deque([(root, {})])

    while stack:
        node, path = stack.pop()
        if node.var is None:  # Terminal node reached
            if min_value is None or node.value < min_value:
                min_value = node.value
                min_paths = [path]
            elif node.value == min_value:
                min_paths.append(path)
            continue

        # Internal node: traverse children
        var_name = node.var

        # Explore low branch (assign False)
        if node.low is not None:
            new_path = path.copy()
            new_path[var_name] = False
            stack.append((node.low, new_path))

        # Explore high branch (assign True)
        if node.high is not None:
            new_path = path.copy()
            new_path[var_name] = True
            stack.append((node.high, new_path))

    return min_paths, min_value
