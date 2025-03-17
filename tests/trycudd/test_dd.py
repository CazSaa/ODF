import pytest
from dd import cudd, cudd_add
from dd.cudd import restrict

from odf.checker.layer1.layer1_bdd import Layer1BDDTransformer


def test_simple():
    """
    Test creating a BDD/ADD and modifying specific edges
    """
    manager = cudd.BDD()
    manager.declare('a', 'b')
    f1 = manager.add_expr('a & b')

    f2 = manager.add_expr('a & b')

    assert f1 == f2

    a = manager.var('a')
    b = manager.var('b')

    f1 = manager.apply('equiv', a, b)
    f2 = a.equiv(b)

    assert f1 == f2

    ne = ~f2
    f3 = manager.apply('xor', a, b)

    assert ne == f3


def test_restrict():
    """
    Test the restrict operator which assigns values to specific variables.
    This is useful for simplifying decision diagrams and focusing on specific subproblems.
    """
    manager = cudd.BDD()
    manager.declare('a', 'b', 'c', 'd')

    # Create an expression with multiple variables: (a & b) | (c & d)
    # This creates a more complex BDD structure
    expr = '(a & b) | (c & d)'
    f = manager.add_expr(expr)

    # Export the initial BDD to a dot file
    manager.dump('original_bdd.dot', [f])

    # Apply restriction: a = True, c = False
    # This should simplify the expression to: b | (False & d) = b
    restriction = {'a': True, 'c': False}
    restricted_f = manager.let(restriction, f)

    # Export the restricted BDD
    manager.dump('restricted_bdd.dot', [restricted_f])

    # Verify the restriction worked correctly
    b = manager.var('b')
    assert restricted_f == b, "After restriction with a=True and c=False, expression should simplify to just 'b'"

    # Test another restriction case: b = False, d = True
    # This should simplify the expression to: (a & False) | (c & True) = c
    restriction2 = {'b': False, 'd': True}
    restricted_f2 = manager.let(restriction2, f)

    # Export the second restricted BDD
    manager.dump('restricted_bdd2.dot', [restricted_f2])

    # Verify the second restriction
    c = manager.var('c')
    assert restricted_f2 == c, "After restriction with b=False and d=True, expression should simplify to just 'c'"


def test_restrict_operator():
    """
    Test the restrict operator directly which optimizes BDD structures
    based on Coudert's algorithm for restricting functions to care sets.
    """
    manager = cudd.BDD()
    manager.declare('a', 'b', 'c', 'd')

    # Create an expression with multiple variables: (a & b) | (c & d)
    # This creates a more complex BDD structure
    expr = '(a & b) | (c & d)'
    f = manager.add_expr(expr)

    # Export the initial BDD to a dot file
    manager.dump('original_bdd_restrict.dot', [f])

    # Apply restriction: a = True, c = False
    # First, create a care set BDD that represents the variable assignments
    a = manager.var('a')
    c = manager.var('c')
    care_set = a & ~c

    # Apply restrict operator 
    restricted_f = restrict(f, care_set)

    # Export the restricted BDD
    manager.dump('restricted_bdd_restrict.dot', [restricted_f])

    # Verify the restriction worked correctly
    b = manager.var('b')
    assert restricted_f == b, "After restriction with a=True and c=False, expression should simplify to just 'b'"

    # Test another restriction case: b = False, d = True
    b = manager.var('b')
    d = manager.var('d')
    care_set2 = ~b & d

    # Apply restrict operator
    restricted_f2 = restrict(f, care_set2)

    # Export the second restricted BDD
    manager.dump('restricted_bdd_restrict2.dot', [restricted_f2])

    # Verify the second restriction
    c = manager.var('c')
    assert restricted_f2 == c, "After restriction with b=False and d=True, expression should simplify to just 'c'"


def test_mrs_pattern():
    manager = cudd_add.ADD()
    manager.declare('x1', 'x2', 'x3', 'x4', 'p1', 'p2', 'p3', 'p4')
    f1 = manager.add_expr(
        '(p1 => x1) & (p2 => x2) & (p3 => x3) & (p4 => x4) & ((p1 ^ x1) | (p2 ^ x2) | (p3 ^ x3) | (p4 ^ x4))')
    manager.dump('mrs_pattern.dot', [f1])

    manager2 = cudd_add.ADD()
    manager2.declare('x1', 'p1', 'x2', 'p2', 'x3', 'p3', 'x4', 'p4')
    f2 = manager2.add_expr(
        '(p1 => x1) & (p2 => x2) & (p3 => x3) & (p4 => x4) & ((p1 ^ x1) | (p2 ^ x2) | (p3 ^ x3) | (p4 ^ x4))')
    manager2.dump('mrs_pattern2.dot', [f2])

    manager3 = cudd_add.ADD()
    manager3.declare('p1', 'x1', 'p2', 'x2', 'p3', 'x3', 'p4', 'x4')
    f3 = manager3.add_expr(
        '(p1 => x1) & (p2 => x2) & (p3 => x3) & (p4 => x4) & ((p1 ^ x1) | (p2 ^ x2) | (p3 ^ x3) | (p4 ^ x4))')
    manager3.dump('mrs_pattern3.dot', [f3])

    # With 5
    manager4 = cudd_add.ADD()
    manager4.declare('x1', 'x2', 'x3', 'x4', 'x5', 'p1', 'p2', 'p3', 'p4', 'p5')
    f4 = manager4.add_expr(
        '(p1 => x1) & (p2 => x2) & (p3 => x3) & (p4 => x4) & (p5 => x5) & ((p1 ^ x1) | (p2 ^ x2) | (p3 ^ x3) | (p4 ^ x4) | (p5 ^ x5))')
    manager4.reorder()
    manager4.dump('mrs_pattern4.dot', [f4])


def test_eval():
    bdd = cudd.BDD()
    bdd.declare('a', 'b', 'c', 'd')

    an = bdd.add_expr("a & b")
    or_ = bdd.add_expr("c | d")

    assert an.eval({'a': True, 'b': True}) == True
    assert an.eval({'a': True, 'b': False}) == False
    assert an.eval({'a': False, 'b': True}) == False
    assert an.eval({'a': False, 'b': False}) == False

    assert or_.eval({'c': True, 'd': False}) == True
    assert or_.eval({'c': False, 'd': True}) == True
    assert or_.eval({'c': True, 'd': True}) == True
    assert or_.eval({'c': False, 'd': False}) == False

    with pytest.raises(ValueError):
        an.eval({'a': True})


def test_mrs_vars(parse_rule, attack_tree1, fault_tree1, object_graph1):
    formula_tree = parse_rule(
        "MRS(BasicAttack) && (ComplexFault || !ComplexFault)", "layer1_formula")
    transformer = Layer1BDDTransformer(attack_tree1, fault_tree1, object_graph1)
    bdd = transformer.transform(formula_tree)
    manager = transformer.bdd
    manager.dump('mrs_vars_all_vars.dot', [bdd])
