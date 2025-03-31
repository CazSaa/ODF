import pytest
from dd import cudd

from odf.utils.dfs import find_config_reflection_nodes


@pytest.fixture(scope='function')
def bdd_manager():
    """Provides a BDD manager for tests."""
    manager = cudd.BDD()
    yield manager
    # No explicit cleanup needed for dd normally, but good practice if resources were held


def test_find_non_op_children_of_op(bdd_manager):
    """
    Tests the find_non_op_children_of_op function.
    Creates a BDD: OP1 & (NON_OP1 | ~OP2)
    OP1 is an object property node.
    OP2 is an object property node.
    NON_OP1 is not an object property node.
    """
    bdd = bdd_manager
    bdd.declare('OP1', 'OP2', 'NON_OP1')

    op_vars = {'OP1', 'OP2'}

    def is_op(node: cudd.Function) -> bool:
        if node.var is None:
            return False
        return node.var in op_vars

    # Build the BDD: OP1 & (NON_OP1 | ~OP2)
    # Note: dd builds BDDs top-down based on variable order if not explicitly managed.
    # Let's assume default order OP1 < OP2 < NON_OP1 for simplicity here.
    # If order matters critically, manage levels explicitly.
    op1_node = bdd.var('OP1')
    op2_node = bdd.var('OP2')
    non_op1_node = bdd.var('NON_OP1')

    term1 = non_op1_node | ~op2_node  # NON_OP1 | ~OP2
    expr = op1_node & term1  # OP1 & (NON_OP1 | ~OP2)

    # BDD Structure:
    # expr = OP1 & (NON_OP1 | ~OP2)
    #   OP1=1 -> NON_OP1 | ~OP2
    #     OP2=1 -> NON_OP1 | ~1 -> NON_OP1 | 0 -> NON_OP1
    #       NON_OP1=1 -> True
    #       NON_OP1=0 -> False (~True)
    #     OP2=0 -> NON_OP1 | ~0 -> NON_OP1 | 1 -> True
    #   OP1=0 -> False (~True)
    #
    # Stack starts: [(OP1, True, False)] # Assuming expr isn't complemented initially
    # Pop (OP1, True, False). Not visited. current_is_op=True. Don't yield.
    #   Push children:
    #     High child (term1, rooted at OP2): (OP2, True, False ^ term1.negated) -> (OP2, True, False)
    #     Low child (False = ~True): (True, True, False ^ True) -> (True, True, True)
    # Stack: [(OP2, True, False), (True, True, True)]
    #
    # Pop (True, True, True). Not visited. current_is_op=False (terminal). parent_is_op=True -> Yield (True, True)
    # Stack: [(OP2, True, False)]
    #
    # Pop (OP2, True, False). Not visited. current_is_op=True. Don't yield.
    #   Push children:
    #     High child (NON_OP1): (NON_OP1, True, False ^ NON_OP1.negated) -> (NON_OP1, True, False)
    #     Low child (True): (True, True, False ^ True.negated) -> (True, True, False)
    # Stack: [(NON_OP1, True, False), (True, True, False)]
    #
    # Pop (True, True, False). Not visited. current_is_op=False (terminal). parent_is_op=True -> Yield (True, False)
    # Stack: [(NON_OP1, True, False)]
    #
    # Pop (NON_OP1, True, False). Not visited. current_is_op=False. parent_is_op=True -> Yield (NON_OP1, False)
    # not current_is_op -> Continue
    # Stack: []

    # Run the function
    result_nodes = list(find_config_reflection_nodes(expr, is_op))

    # Define expected set
    expected = [
        (bdd.true, True),  # From OP1 low child (~True)
        (bdd.true, False),  # From OP2 low child (True)
        (non_op1_node, False)  # From OP2 high child (NON_OP1)
    ]

    assert result_nodes == expected


def test_find_non_op_children_with_terminals(bdd_manager):
    """
    Tests find_non_op_children_of_op with a simpler BDD where OP nodes have direct terminal children.
    Creates a BDD: OP1 & OP2

    The BDD structure will be:
    OP1=1 -> OP2
      OP2=1 -> True
      OP2=0 -> False (~True)
    OP1=0 -> False (~True)

    Since terminals are not OP nodes, they should be yielded when their parent is an OP node.
    """
    bdd = bdd_manager
    bdd.declare('OP1', 'OP2')

    op_vars = {'OP1', 'OP2'}

    def is_op(node: cudd.Function) -> bool:
        if node.var is None:
            return False
        return node.var in op_vars

    # Build the BDD: OP1 & OP2
    op1_node = bdd.var('OP1')
    op2_node = bdd.var('OP2')
    expr = op1_node & op2_node

    # BDD traversal trace:
    # Stack starts: [(OP1, True, False)] # Root node
    # Pop (OP1, True, False). Not visited. current_is_op=True. Don't yield.
    #   Push children:
    #     High child (OP2): (OP2, True, False) 
    #     Low child (False = ~True): (True, True, True)
    # Stack: [(OP2, True, False), (True, True, True)]
    #
    # Pop (True, True, True). Not visited. current_is_op=False (terminal). parent_is_op=True -> Yield (True, True)
    # Stack: [(OP2, True, False)]
    #
    # Pop (OP2, True, False). Not visited. current_is_op=True. Don't yield.
    #   Push children:
    #     High child (True): (True, True, False)
    #     Low child (False = ~True): (True, True, True)
    # Stack: [(True, True, False), (True, True, True)]
    #
    # Pop (True, True, True). Visited.
    # Stack: [(True, True, False)]
    #
    # Pop (True, True, False). Not visited. current_is_op=False (terminal). parent_is_op=True -> Yield (True, False)
    # Stack: []

    # Run the function
    result_nodes = list(find_config_reflection_nodes(expr, is_op))

    # Define expected results in traversal order
    expected = [
        (bdd.true, True),  # From OP1 low child (~True)
        (bdd.true, False),  # From OP2 high child (True)
    ]

    assert result_nodes == expected


def test_find_non_op_children_terminal_only(bdd_manager):
    """
    Tests find_non_op_children_of_op with terminal-only BDDs (True and False).
    Since parent_is_op=True initially, and terminals are not OPs,
    the terminal node itself should be yielded.
    """
    bdd = bdd_manager

    def is_op(node: cudd.Function) -> bool:
        if node.var is None:
            return False
        return False  # For terminal-only test, no nodes are OPs

    # Test with True terminal
    true_expr = bdd.true

    # Stack starts: [(True, True, False)] # Root node
    # Pop (True, True, False). Not visited. current_is_op=False. parent_is_op=True -> Yield (True, False)
    # Stack: []

    result_nodes = list(find_config_reflection_nodes(true_expr, is_op))
    expected = [(bdd.true, False)]  # True node with no complementation
    assert result_nodes == expected

    # Test with False terminal (~True)
    false_expr = ~true_expr

    # Stack starts: [(True, True, True)] # Root node (True complemented)
    # Pop (True, True, True). Not visited. current_is_op=False. parent_is_op=True -> Yield (True, True)
    # Stack: []

    result_nodes = list(find_config_reflection_nodes(false_expr, is_op))
    expected = [(bdd.true, True)]  # True node but complemented
    assert result_nodes == expected


def test_find_non_op_children_no_ops(bdd_manager):
    """
    Tests find_non_op_children_of_op with a BDD that contains no object properties.
    Creates a BDD: NON_OP1 & NON_OP2

    Since neither variable is an OP, and parent_is_op starts as True for the root,
    only the root node (NON_OP1) should be yielded.
    """
    bdd = bdd_manager
    bdd.declare('NON_OP1', 'NON_OP2')

    op_vars = set()  # Empty set - no variables are object properties

    def is_op(node: cudd.Function) -> bool:
        if node.var is None:
            return False
        return node.var in op_vars

    # Build the BDD: NON_OP1 & NON_OP2
    non_op1_node = bdd.var('NON_OP1')
    non_op2_node = bdd.var('NON_OP2')
    expr = non_op1_node & non_op2_node

    # Stack starts: [(NON_OP1, True, False)] # Root node
    # Pop (NON_OP1, True, False). Not visited. current_is_op=False. parent_is_op=True -> Yield (NON_OP1, False)
    # not current_is_op -> Continue
    # Stack: []

    # Run the function
    result_nodes = list(find_config_reflection_nodes(expr, is_op))

    # Define expected results in traversal order
    expected = [
        (expr, False),
        # Only root node yielded since parent_is_op=True for root
    ]

    assert result_nodes == expected


def test_find_non_op_children_complex_nested(bdd_manager):
    """
    Tests find_non_op_children_of_op with a highly complex BDD involving multiple
    nested operations, negations, and shared subgraphs.
    See test_find_non_op_children_complex_nested.pdf for a visual representation.
    The yielded node IDs are commented down below.

    Creates a BDD for the formula:
    (OP1 => (~OP2 & NON_OP1)) &
    (~OP3 | (OP4 & ~NON_OP2)) &
    ((OP5 => NON_OP3) | (NON_OP4 & ~OP6)) &
    ~(OP7 & (NON_OP5 => OP8))

    Equivalent to:
    ( ~OP1 | (~OP2 & NON_OP1) ) &
    ( ~OP3 | (OP4 & ~NON_OP2) ) &
    ( (~OP5 | NON_OP3) | (NON_OP4 & ~OP6) ) &
    ( ~OP7 | (NON_OP5 & ~OP8) )


    This formula tests:
    1. All boolean operators (AND, OR, NOT, IMPLIES)
    2. Multiple levels of nesting
    3. Shared subgraphs in the BDD
    4. Complex complement propagation
    """
    bdd = bdd_manager
    # Declare variables in order we want them in the BDD
    ops = ['OP1', 'OP2', 'OP3', 'OP4', 'OP5', 'OP6', 'OP7', 'OP8']
    non_ops = ['NON_OP1', 'NON_OP2', 'NON_OP3', 'NON_OP4', 'NON_OP5']

    # Declare all variables (order matters for BDD structure)
    for var in ops + non_ops:
        bdd.declare(var)

    op_vars = set(ops)

    def is_op(node: cudd.Function) -> bool:
        if node.var is None:
            return False
        return node.var in op_vars

    # Get all variable nodes
    nodes = {name: bdd.var(name) for name in ops + non_ops}

    # Build the complex formula piece by piece
    part1 = bdd.apply('implies', nodes['OP1'], ~nodes['OP2'] & nodes['NON_OP1'])
    part2 = ~nodes['OP3'] | (nodes['OP4'] & ~nodes['NON_OP2'])
    part3 = bdd.apply('implies', nodes['OP5'], nodes['NON_OP3']) | (
            nodes['NON_OP4'] & ~nodes['OP6'])
    part4 = ~(nodes['OP7'] & bdd.apply('implies', nodes['NON_OP5'],
                                       nodes['OP8']))

    # Combine all parts
    expr = part1 & part2 & part3 & part4

    # Run the function
    result_nodes = list(find_config_reflection_nodes(expr, is_op))

    # Define expected results
    expected = [
        (bdd.true, False),
        (nodes['NON_OP5'], False),  # NON_OP5-2
        (bdd.true, True),
        (nodes['NON_OP3'] | nodes['NON_OP4'], False),  # NON_OP3-9
        ((nodes['NON_OP3'] | nodes['NON_OP4']) & nodes['NON_OP5'], False),
        # NON_OP3-11
        (nodes['NON_OP3'], False),  # NON_OP3-8
        (nodes['NON_OP3'] & nodes['NON_OP5'], False),  # NON_OP3-14
        (nodes['NON_OP2'], True),  # NON_OP2-21
        (nodes['NON_OP2'] | ~nodes['NON_OP5'], True),  # NON_OP2-22
        (nodes['NON_OP2'] | (~nodes['NON_OP3'] & ~nodes['NON_OP4']), True),
        # NON_OP2-25
        (nodes['NON_OP2'] | ((~nodes['NON_OP3'] & ~nodes['NON_OP4']) | ~nodes[
            'NON_OP5']), True),  # NON_OP2-26
        (nodes['NON_OP2'] | ~nodes['NON_OP3'], True),  # NON_OP2-29
        (nodes['NON_OP2'] | ~nodes['NON_OP3'] | ~nodes['NON_OP5'], True),
        # NON_OP2-30
        (nodes['NON_OP1'], False),  # NON_OP1-39
        (nodes['NON_OP1'] & nodes['NON_OP5'], False),  # NON_OP1-40
        (nodes['NON_OP1'] & (nodes['NON_OP3'] | nodes['NON_OP4']), False),
        # NON_OP1-43
        (nodes['NON_OP1'] & (nodes['NON_OP3'] | nodes['NON_OP4']) & nodes[
            'NON_OP5'], False),  # NON_OP1-44
        (nodes['NON_OP1'] & nodes['NON_OP3'], False),  # NON_OP1-47
        (nodes['NON_OP1'] & nodes['NON_OP3'] & nodes['NON_OP5'], False),
        # NON_OP1-48
        (~nodes['NON_OP1'] | nodes['NON_OP2'], True),  # NON_OP1-53
        (~nodes['NON_OP1'] | nodes['NON_OP2'] | ~nodes['NON_OP5'], True),
        # NON_OP1-54
        (~nodes['NON_OP1'] | nodes['NON_OP2'] | (
                    ~nodes['NON_OP3'] & ~nodes['NON_OP4']), True),  # NON_OP1-57
        (~nodes['NON_OP1'] | nodes['NON_OP2'] | (
                    (~nodes['NON_OP3'] & ~nodes['NON_OP4']) | ~nodes[
                'NON_OP5']), True),  # NON_OP1-58
        (~nodes['NON_OP1'] | nodes['NON_OP2'] | ~nodes['NON_OP3'], True),
        # NON_OP1-61
        (~nodes['NON_OP1'] | nodes['NON_OP2'] | ~nodes['NON_OP3'] | ~nodes[
            'NON_OP5'], True),  # NON_OP1-62
    ]

    assert result_nodes == expected
