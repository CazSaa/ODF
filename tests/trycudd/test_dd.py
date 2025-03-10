import dd.cudd
import dd.cudd_add


def test_simple():
    """
    Test creating a BDD/ADD and modifying specific edges
    """
    manager = dd.cudd.BDD()
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
    manager = dd.cudd.BDD()
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
    from dd.cudd import restrict
    
    manager = dd.cudd.BDD()
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
