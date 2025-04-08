import pytest

from odf.checker.exceptions import MissingConfigurationError


def test_basic_compute_all(do_layer1_compute_all):
    """Test computing all minimal configurations for basic formulas."""
    result = do_layer1_compute_all("BasicAttack", "{}")
    assert result == {frozenset({"BasicAttack"})}

    result = do_layer1_compute_all("!BasicAttack", "{}")
    assert result == {frozenset()}


def test_complex_formula_compute_all(do_layer1_compute_all):
    """Test computing all minimal configurations for complex formulas with gates and conditions."""
    # ComplexAttack requires its basic events and conditions
    result = do_layer1_compute_all("ComplexAttack",
                                   "{obj_prop1: 1, obj_prop2: 1}")
    assert result == {frozenset({"SubAttack1", "SubAttack2"})}

    result = do_layer1_compute_all(
        "(BasicAttack || BasicFault) && ComplexAttack",
        "{obj_prop1: 1, obj_prop2: 1}")
    assert result == {
        frozenset({"BasicAttack", "SubAttack1", "SubAttack2"}),
        frozenset({"BasicFault", "SubAttack1", "SubAttack2"})
    }


def test_missing_object_properties(do_layer1_compute_all):
    """Test error handling when configuration is missing required variables."""
    with pytest.raises(MissingConfigurationError,
                       match="Missing object properties") as excinfo:
        do_layer1_compute_all("ComplexAttack",
                              "{}")  # Missing required object properties
    assert "obj_prop1" in str(excinfo.value)
    assert "obj_prop2" in str(excinfo.value)

    # Partial configuration should still fail
    with pytest.raises(MissingConfigurationError,
                       match="Missing object properties") as excinfo:
        do_layer1_compute_all("ComplexAttack",
                              "{obj_prop1: 1}")  # Missing obj_prop2
    assert "obj_prop2" in str(excinfo.value)


def test_extra_object_properties(do_layer1_compute_all, caplog):
    """Test handling of extra variables in configuration."""
    result = do_layer1_compute_all(
        "BasicAttack",
        "{NonexistentVar: 1}"
    )

    # Check that warning was printed
    assert "are not used by the formula and will be ignored" in caplog.text
    assert "NonexistentVar" in caplog.text
    caplog.clear()

    # Check that the formula was still evaluated correctly
    assert result == {frozenset({"BasicAttack"})}

    assert do_layer1_compute_all(
        "BasicAttack && (obj_prop1 || !obj_prop1)",
        "{}"
    ) == {frozenset({"BasicAttack"})}

    assert do_layer1_compute_all(
        "BasicAttack && (obj_prop1 || !obj_prop1)",
        "{obj_prop1: 1}"
    ) == {frozenset({"BasicAttack"})}
    assert "are not used by the formula and will be ignored" in caplog.text
    assert "obj_prop1" in caplog.text


def test_complex_conditions_compute_all(do_layer1_compute_all):
    """Test computing all configurations for formulas with complex conditions."""
    # Test ComplexFault which has nested conditions
    result = do_layer1_compute_all("ComplexFault",
                                   "{obj_prop4: 1, obj_prop5: 1, obj_prop6: 1}")
    assert result == {frozenset({"SubFault1", "SubFault2"})}

    # When one condition is false, there should be no valid configurations
    result = do_layer1_compute_all("ComplexFault",
                                   "{obj_prop4: 0, obj_prop5: 1, obj_prop6: 1}")
    assert result == set()

    result = do_layer1_compute_all("ComplexFault",
                                   "{obj_prop4: 1, obj_prop5: 0, obj_prop6: 1}")
    assert result == set()

    result = do_layer1_compute_all("ComplexFault",
                                   "{obj_prop4: 1, obj_prop5: 1, obj_prop6: 0}")
    assert result == set()


def test_boolean_operators_compute_all(do_layer1_compute_all):
    """Test various boolean operators in compute_all formulas."""
    # Test AND
    result = do_layer1_compute_all("BasicAttack && BasicFault", "{}")
    assert result == {frozenset({"BasicAttack", "BasicFault"})}

    # Test OR
    result = do_layer1_compute_all("BasicAttack || BasicFault", "{}")
    assert result == {frozenset({"BasicAttack"}), frozenset({"BasicFault"})}

    # Test IMPLIES
    result = do_layer1_compute_all("BasicAttack => BasicFault", "{}")
    assert result == {frozenset()}  # Both BasicAttack=False or BasicFault=True

    # Test EQUIV
    result = do_layer1_compute_all("BasicAttack == BasicFault", "{}")
    assert result == {frozenset()}  # Both True or both False

    # Test NOT EQUIV
    result = do_layer1_compute_all("BasicAttack != BasicFault", "{}")
    assert result == {frozenset({"BasicAttack"}),
                      frozenset({"BasicFault"})}  # One True, one False


def test_object_property_compute_all(do_layer1_compute_all):
    """Test computing formulas with object properties."""
    # Test direct object property
    result = do_layer1_compute_all("obj_prop1", "{obj_prop1: 1}")
    assert result == {frozenset()}

    # Test object property in condition
    result = do_layer1_compute_all("SubFault2", "{obj_prop6: 1}")
    assert result == {frozenset({"SubFault2"})}

    # False object property makes the node unreachable
    result = do_layer1_compute_all("SubFault2", "{obj_prop6: 0}")
    assert result == set()


def test_evidence_in_compute_all(do_layer1_compute_all):
    """Test computing formulas with boolean evidence."""
    # Simple evidence
    result = do_layer1_compute_all(
        "ComplexAttack [SubAttack1: 1, SubAttack2: 1]",
        "{obj_prop1: 1, obj_prop2: 1}"
    )
    assert result == {
        frozenset()}  # Empty set since all needed variables are in evidence

    # Evidence with partial definition
    result = do_layer1_compute_all(
        "ComplexAttack [SubAttack1: 1]",
        "{obj_prop1: 1, obj_prop2: 1}"
    )
    assert result == {frozenset({"SubAttack2"})}

    # Evidence affecting conditions
    result = do_layer1_compute_all(
        "ComplexAttack [obj_prop1: 1, obj_prop2: 1]",
        "{}"
    )
    assert result == {frozenset({"SubAttack1", "SubAttack2"})}

    # Evidence in complex formula
    result = do_layer1_compute_all(
        "(ComplexAttack [SubAttack1: 1]) && (ComplexFault [SubFault1: 1])",
        "{obj_prop1: 1, obj_prop2: 1, obj_prop4: 1, obj_prop5: 1, obj_prop6: 1}"
    )
    assert result == {frozenset({"SubAttack2", "SubFault2"})}


def test_mrs_operator_compute_all(do_layer1_compute_all):
    """Test computing formulas with MRS operator."""
    # MRS of a basic event
    result = do_layer1_compute_all("MRS(BasicAttack)", "{}")
    assert result == {frozenset({"BasicAttack"})}

    # MRS of OR expression
    result = do_layer1_compute_all("MRS(BasicAttack || BasicFault)", "{}")
    assert result == {frozenset({"BasicAttack"}), frozenset({"BasicFault"})}

    # MRS of complex expression
    result = do_layer1_compute_all("MRS(ComplexAttack)",
                                   "{obj_prop1: 1, obj_prop2: 1}")
    assert result == {frozenset({"SubAttack1", "SubAttack2"})}

    # MRS with evidence
    result = do_layer1_compute_all(
        "MRS(BasicAttack || BasicFault) [BasicFault: 1]", "{}")
    assert result == {
        frozenset()}  # BasicFault is already true, so minimal set is empty


def test_mrs_mixed_gates_compute_all(do_layer1_compute_all,
                                     attack_tree_mixed_gates):
    """Test computing minimal configurations with mixed gate types."""
    # Test PathA - requires all basic events in path
    result = do_layer1_compute_all(
        "PathA",
        "{}",
        attack_tree=attack_tree_mixed_gates
    )
    assert result == {frozenset({"Attack1", "Attack2", "StepA2"})}

    # Test PathB - should get two minimal configurations
    result = do_layer1_compute_all(
        "PathB",
        "{}",
        attack_tree=attack_tree_mixed_gates
    )
    expected = {
        frozenset({"Attack3", "Attack4"}),
        frozenset({"Attack5", "Attack6"})
    }
    assert result == expected

    # Test root level with complex conditions
    result = do_layer1_compute_all(
        "RootA",
        "{obj_prop1: 1, obj_prop2: 1}",
        attack_tree=attack_tree_mixed_gates
    )
    expected = {
        frozenset({"Attack1", "Attack2", "StepA2"}),  # Via PathA
        frozenset({"Attack3", "Attack4"}),  # Via PathB option 1
        frozenset({"Attack5", "Attack6"}),  # Via PathB option 2
        # Via PathC option 1
        frozenset({"Attack7", "Attack9", "Attack10", "SubPathC3"}),
        # Via PathC option 2
        frozenset({"Attack7", "Attack9", "Attack11", "SubPathC3"}),
        # Via PathC option 3
        frozenset({"Attack8", "Attack9", "Attack10", "SubPathC3"}),
        # Via PathC option 4
        frozenset({"Attack8", "Attack9", "Attack11", "SubPathC3"})
    }
    assert result == expected


def test_nested_mrs_compute_all(do_layer1_compute_all):
    """Test computing formulas with nested MRS operators."""
    # Nested MRS operators
    result = do_layer1_compute_all("MRS(MRS(BasicAttack || BasicFault))", "{}")
    assert result == {frozenset({"BasicAttack"}), frozenset({"BasicFault"})}

    # Nested MRS with evidence
    result = do_layer1_compute_all(
        "MRS(MRS(BasicAttack || BasicFault) [BasicFault: 1])", "{}")
    assert result == {frozenset()}
    result = do_layer1_compute_all(
        "MRS(MRS(BasicAttack && BasicFault) [BasicFault: 1])", "{}")
    assert result == {frozenset({"BasicAttack"})}

    # MRS with partial evidence
    result = do_layer1_compute_all(
        "MRS(ComplexAttack [SubAttack1: 1])",
        "{obj_prop1: 1, obj_prop2: 1}"
    )
    assert result == {frozenset({"SubAttack2"})}


def test_tautologies_and_contradictions(do_layer1_compute_all):
    """Test computing results for tautologies and contradictions."""
    # Tautology
    result = do_layer1_compute_all("BasicAttack || !BasicAttack", "{}")
    assert result == {frozenset()}  # Always true, so empty set is the minimal

    # Contradiction
    result = do_layer1_compute_all("BasicAttack && !BasicAttack", "{}")
    assert result == set()  # No satisfying assignment


def test_complex_trees_compute_all(do_layer1_compute_all,
                                   attack_tree_mixed_gates):
    """Test computing results for complex tree structures."""
    # Test a path that combines multiple gate types
    result = do_layer1_compute_all(
        "PathC",
        "{obj_prop1: 1, obj_prop2: 1}",
        attack_tree=attack_tree_mixed_gates
    )

    # PathC requires SubPathC1, SubPathC2, and SubPathC3
    # SubPathC1 can be satisfied by either Attack7 or Attack8 (with conditions)
    # SubPathC2 requires Attack9 AND either Attack10 or Attack11

    expected_results = {
        frozenset({"Attack7", "Attack9", "Attack10", "SubPathC3"}),
        frozenset({"Attack7", "Attack9", "Attack11", "SubPathC3"}),
        frozenset({"Attack8", "Attack9", "Attack10", "SubPathC3"}),
        frozenset({"Attack8", "Attack9", "Attack11", "SubPathC3"})
    }

    assert result == expected_results

    assert do_layer1_compute_all(
        "PathC",
        "{obj_prop1: 0, obj_prop2: 1}",
        attack_tree=attack_tree_mixed_gates
    ) == {
               frozenset({"Attack8", "Attack9", "Attack10", "SubPathC3"}),
               frozenset({"Attack8", "Attack9", "Attack11", "SubPathC3"})
           }

    assert do_layer1_compute_all(
        "PathC",
        "{obj_prop1: 1, obj_prop2: 0}",
        attack_tree=attack_tree_mixed_gates
    ) == {
               frozenset({"Attack7", "Attack9", "Attack10", "SubPathC3"}),
               frozenset({"Attack7", "Attack9", "Attack11", "SubPathC3"})
           }

    assert do_layer1_compute_all(
        "PathC",
        "{obj_prop1: 0, obj_prop2: 0}",
        attack_tree=attack_tree_mixed_gates
    ) == set()
