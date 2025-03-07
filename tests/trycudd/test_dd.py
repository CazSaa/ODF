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
