import pytest


def test_basic_check(do_layer1_check):
    """Test checking a basic formula with complete configuration."""
    # Test single node satisfaction
    assert do_layer1_check(
        "BasicAttack",
        "{BasicAttack:1}",
    )

    assert not do_layer1_check(
        "BasicAttack",
        "{BasicAttack:0}",
    )

    # Test negation
    assert do_layer1_check(
        "!BasicAttack",
        "{BasicAttack:0}",
    )


def test_complex_formula_check(do_layer1_check):
    """Test checking complex formulas with gates and conditions."""
    # Test ComplexAttack which requires its basic events and conditions
    assert do_layer1_check(
        "ComplexAttack",
        "{SubAttack1:1, SubAttack2:1, obj_prop1:1, obj_prop2:1}"
    )

    # Test complex formula with multiple operators
    assert do_layer1_check(
        "(BasicAttack || BasicFault) && ComplexAttack",
        "{BasicAttack:1, BasicFault:0, SubAttack1:1, SubAttack2:1, obj_prop1:1, obj_prop2:1}"
    )


def test_missing_variables(do_layer1_check):
    """Test error handling when configuration is missing required variables."""
    with pytest.raises(ValueError, match="Missing variables:"):
        do_layer1_check(
            "ComplexAttack",
            "{SubAttack1:1}"  # Missing SubAttack2 and object properties
        )


def test_extra_variables(do_layer1_check, capsys):
    """Test handling of extra variables in configuration."""
    result = do_layer1_check(
        "BasicAttack",
        "{BasicAttack:1, NonexistentVar:1}"
    )

    # Check that warning was printed
    captured = capsys.readouterr()
    assert "You specified variables that either do not exist" in captured.out
    assert "NonexistentVar" in captured.out
    # Check that the formula was still evaluated correctly
    assert result == True


def test_complex_conditions_check(do_layer1_check):
    """Test checking formulas with complex conditions."""
    # Test ComplexFault which has nested conditions
    assert do_layer1_check(
        "ComplexFault",
        "{SubFault1:1, SubFault2:1, obj_prop4:1, obj_prop5:1, obj_prop6:1}"
    )

    # Test when one condition is false
    assert not do_layer1_check(
        "ComplexFault",
        "{SubFault1:1, SubFault2:1, obj_prop4:0, obj_prop5:1, obj_prop6:1}"
    )
    assert not do_layer1_check(
        "ComplexFault",
        "{SubFault1:1, SubFault2:1, obj_prop4:1, obj_prop5:0, obj_prop6:1}"
    )
    assert not do_layer1_check(
        "ComplexFault",
        "{SubFault1:1, SubFault2:1, obj_prop4:1, obj_prop5:1, obj_prop6:0}"
    )


def test_boolean_operators(do_layer1_check):
    """Test various boolean operators in formulas."""
    # Test AND
    assert do_layer1_check(
        "BasicAttack && BasicFault",
        "{BasicAttack:1, BasicFault:1}"
    )

    # Test OR
    assert do_layer1_check(
        "BasicAttack || BasicFault",
        "{BasicAttack:1, BasicFault:0}"
    )

    # Test IMPLIES
    assert do_layer1_check(
        "BasicAttack => BasicFault",
        "{BasicAttack:0, BasicFault:1}"
    )
    assert not do_layer1_check(
        "BasicAttack => BasicFault",
        "{BasicAttack:1, BasicFault:0}"
    )

    # Test EQUIV
    assert do_layer1_check(
        "BasicAttack == BasicFault",
        "{BasicAttack:1, BasicFault:1}"
    )

    # Test NOT EQUIV
    assert do_layer1_check(
        "BasicAttack != BasicFault",
        "{BasicAttack:1, BasicFault:0}"
    )


def test_object_property_check(do_layer1_check):
    """Test checking formulas with object properties."""
    # Test direct object property
    assert do_layer1_check(
        "obj_prop1",
        "{obj_prop1:1}"
    )

    # Test object property in condition
    assert not do_layer1_check(
        "SubFault2",
        "{SubFault2:1, obj_prop6:0}"
    )
    assert not do_layer1_check(
        "SubFault2",
        "{SubFault2:0, obj_prop6:1}"
    )
    assert do_layer1_check(
        "SubFault2",
        "{SubFault2:1, obj_prop6:1}"
    )


def test_evidence_in_check(do_layer1_check):
    """Test checking formulas with boolean evidence."""
    # Simple evidence
    assert do_layer1_check(
        "ComplexAttack [SubAttack1:1, SubAttack2:1]",
        "{obj_prop1:1, obj_prop2:1}"
    )

    # Evidence overriding configuration
    assert do_layer1_check(
        "BasicAttack [BasicAttack:1]",
        "{BasicAttack:0}"  # Evidence should override configuration
    )

    # Evidence in complex formula
    assert do_layer1_check(
        "(ComplexAttack [SubAttack1:1, SubAttack2:1]) && !(ComplexFault [SubFault1:0])",
        "{obj_prop1:1, obj_prop2:1, obj_prop4:1, obj_prop5:1, obj_prop6:1}"
    )

    # Evidence affecting conditions
    assert do_layer1_check(
        "ComplexAttack [obj_prop1:1, obj_prop2:1]",
        "{SubAttack1:1, SubAttack2:1}"  # Evidence sets the conditions
    )


def test_mrs_operator(do_layer1_check):
    """Test checking formulas with MRS operator."""
    assert do_layer1_check(
        "MRS(BasicAttack)",
        "{BasicAttack:1}"
    )

    assert do_layer1_check(
        "MRS(BasicAttack || BasicFault)",
        "{BasicAttack:0, BasicFault:1}"
    )
    assert do_layer1_check(
        "MRS(BasicAttack || BasicFault)",
        "{BasicAttack:1, BasicFault:0}"
    )
    assert not do_layer1_check(
        "MRS(BasicAttack || BasicFault)",
        "{BasicAttack:1, BasicFault:1}"
    )
    assert not do_layer1_check(
        "MRS(BasicAttack || BasicFault)",
        "{BasicAttack:0, BasicFault:0}"
    )

    assert do_layer1_check(
        "MRS(ComplexAttack)",
        "{SubAttack1:1, SubAttack2:1, obj_prop1:1, obj_prop2:1}"
    )


def test_mrs_with_evidence(do_layer1_check):
    """Test checking formulas with both MRS and evidence."""
    assert do_layer1_check(
        "MRS(BasicAttack || BasicFault) [BasicFault:1]",
        "{BasicAttack:0}"  # Only BasicFault should be minimal
    )

    # MRS with evidence inside formula
    assert do_layer1_check(
        "MRS(ComplexAttack [SubAttack1:1])",
        "{SubAttack2:1, obj_prop1:1, obj_prop2:1}"
    )


def test_nested_mrs(do_layer1_check):
    """Test checking formulas with nested MRS operators."""
    # Nested MRS
    assert do_layer1_check(
        "MRS(MRS(BasicAttack || BasicFault))",
        "{BasicAttack:0, BasicFault:1}"
    )
    assert do_layer1_check(
        "MRS(MRS(BasicAttack || BasicFault))",
        "{BasicAttack:1, BasicFault:0}"
    )
    assert not do_layer1_check(
        "MRS(MRS(BasicAttack || BasicFault))",
        "{BasicAttack:1, BasicFault:1}"
    )
    assert not do_layer1_check(
        "MRS(MRS(BasicAttack || BasicFault))",
        "{BasicAttack:0, BasicFault:0}"
    )

    # Nested MRS with evidence at different levels
    assert do_layer1_check(
        "MRS(BasicAttack || BasicFault) [BasicFault:1]",
        "{BasicAttack:0}"
    )
    assert do_layer1_check(
        "MRS(BasicAttack) && (ComplexFault || !ComplexFault)",
        "{BasicAttack:1}"
    )
    assert do_layer1_check(
        "MRS(BasicAttack || BasicFault [BasicFault:1])",
        "{BasicAttack:0}"
    )
    assert do_layer1_check(
        "MRS(MRS(BasicAttack || BasicFault) [BasicFault:1])",
        "{BasicAttack:0}"
    )


def test_evidence_configuration_interaction(do_layer1_check):
    """Test complex interactions between evidence and configuration."""
    assert do_layer1_check(
        "(ComplexAttack [SubAttack1:1]) && (ComplexFault [SubFault1:1])",
        """{
            SubAttack2:1, obj_prop1:1, obj_prop2:1,  // For ComplexAttack
            SubFault2:1, obj_prop4:1, obj_prop5:1, obj_prop6:1  // For ComplexFault
        }"""
    )

    with pytest.raises(ValueError, match="Missing variables"):
        do_layer1_check(
            "ComplexAttack [SubAttack1:1, SubAttack2:1]",
            "{obj_prop1:1}"  # Missing obj_prop2
        )


def test_mrs_with_mixed_gates(do_layer1_check, attack_tree_mixed_gates, capsys):
    """Test MRS computation with a complex tree containing mixed gate types."""

    # Test MRS of PathA - requires all basic events in path
    assert do_layer1_check(
        "MRS(PathA)",
        "{Attack1:1, Attack2:1, StepA2:1}",
        attack_tree=attack_tree_mixed_gates
    )

    # Still minimal because Attack3 is ignored since it's not in PathA
    assert do_layer1_check(
        "MRS(PathA)",
        "{Attack1:1, Attack2:1, StepA2:1, Attack3:1}",
        attack_tree=attack_tree_mixed_gates
    )
    # Will print warning about extra variable
    captured = capsys.readouterr()
    assert "You specified variables that either do not exist" in captured.out
    assert "Attack3" in captured.out

    # PathB - should work with either SubPath
    assert do_layer1_check(
        "MRS(PathB)",
        "{Attack3:1, Attack4:1, Attack5:0, Attack6:0}",  # First minimal set
        attack_tree=attack_tree_mixed_gates
    )
    assert do_layer1_check(
        "MRS(PathB)",
        "{Attack5:1, Attack6:1, Attack3:0, Attack4:0}",  # Second minimal set
        attack_tree=attack_tree_mixed_gates
    )

    # Both paths together is not minimal
    assert not do_layer1_check(
        "MRS(PathB)",
        "{Attack3:1, Attack4:1, Attack5:1, Attack6:1}",
        attack_tree=attack_tree_mixed_gates
    )
    assert not do_layer1_check(
        "MRS(PathB)",
        "{Attack3:1, Attack4:0, Attack5:1, Attack6:1}",
        attack_tree=attack_tree_mixed_gates
    )
    assert not do_layer1_check(
        "MRS(PathB)",
        "{Attack3:1, Attack4:1, Attack5:0, Attack6:1}",
        attack_tree=attack_tree_mixed_gates
    )


def test_mrs_with_conditions_mixed_gates(do_layer1_check,
                                         attack_tree_mixed_gates):
    """Test MRS computation with nodes that have conditions in mixed gate tree."""

    # Test SubPathC1 which has conditional nodes
    assert do_layer1_check(
        "MRS(SubPathC1)",
        "{Attack7:1, prop1:1, Attack8:0, prop2:0}",
        attack_tree=attack_tree_mixed_gates
    )

    assert do_layer1_check(
        "MRS(SubPathC1)",
        "{Attack8:1, prop2:1, Attack7:0, prop1:0}",
        attack_tree=attack_tree_mixed_gates
    )

    # Both paths together is not minimal
    assert not do_layer1_check(
        "MRS(SubPathC1)",
        "{Attack7:1, Attack8:1, prop1:1, prop2:1}",
        attack_tree=attack_tree_mixed_gates
    )
    assert not do_layer1_check(
        "MRS(SubPathC1)",
        "{Attack7:1, Attack8:1, prop1:0, prop2:1}",
        attack_tree=attack_tree_mixed_gates
    )
    assert not do_layer1_check(
        "MRS(SubPathC1)",
        "{Attack7:1, Attack8:1, prop1:1, prop2:0}",
        attack_tree=attack_tree_mixed_gates
    )


def test_mrs_nested_gates_mixed(do_layer1_check, attack_tree_mixed_gates):
    """Test MRS computation with deeply nested mixed gates."""

    # Test SubPathC2 which has nested OR inside AND
    # Minimal sets are: {Attack9, Attack10} or {Attack9, Attack11}
    assert do_layer1_check(
        "MRS(SubPathC2)",
        "{Attack9:1, Attack10:1, Attack11:0}",
        attack_tree=attack_tree_mixed_gates
    )

    assert do_layer1_check(
        "MRS(SubPathC2)",
        "{Attack9:1, Attack11:1, Attack10:0}",
        attack_tree=attack_tree_mixed_gates
    )

    # All attacks together is not minimal
    assert not do_layer1_check(
        "MRS(SubPathC2)",
        "{Attack9:1, Attack10:1, Attack11:1}",
        attack_tree=attack_tree_mixed_gates
    )


def test_mrs_root_mixed_gates(do_layer1_check, attack_tree_mixed_gates):
    """Test MRS computation at the root level with all paths through mixed gates."""

    # Test complete tree - each path represents a different minimal set
    assert do_layer1_check(
        "MRS(Root)",
        "{Attack1:1, Attack2:1, StepA2:1, Attack3:0, Attack4:0, Attack5:0, Attack6:0, Attack7:0, Attack8:0, Attack9:0, Attack10:0, Attack11:0, SubPathC3:0, prop1:0, prop2:0}",
        # PathA minimal set
        attack_tree=attack_tree_mixed_gates
    )

    assert do_layer1_check(
        "MRS(Root)",
        "{Attack3:1, Attack4:1, Attack1:0, Attack2:0, StepA2:0, Attack5:0, Attack6:0, Attack7:0, Attack8:0, Attack9:0, Attack10:0, Attack11:0, SubPathC3:0, prop1:0, prop2:0}",
        # PathB (first option) minimal set
        attack_tree=attack_tree_mixed_gates
    )

    assert do_layer1_check(
        "MRS(Root)",
        "{Attack5:1, Attack6:1, Attack1:0, Attack2:0, StepA2:0, Attack3:0, Attack4:0, Attack7:0, Attack8:0, Attack9:0, Attack10:0, Attack11:0, SubPathC3:0, prop1:0, prop2:0}",
        # PathB (second option) minimal set
        attack_tree=attack_tree_mixed_gates
    )

    # One minimal set through PathC
    assert do_layer1_check(
        "MRS(Root)",
        "{Attack7:1, Attack9:1, Attack10:1, SubPathC3:1, prop1:1, Attack1:0, Attack2:0, StepA2:0, Attack3:0, Attack4:0, Attack5:0, Attack6:0, Attack8:0, Attack11:0, prop2:0}",
        # With conditions
        attack_tree=attack_tree_mixed_gates
    )

    # Alternative through PathC using different OR choices
    assert do_layer1_check(
        "MRS(Root)",
        "{Attack8:1, Attack9:1, Attack11:1, SubPathC3:1, prop2:1, Attack1:0, Attack2:0, StepA2:0, Attack3:0, Attack4:0, Attack5:0, Attack6:0, Attack7:0, Attack10:0, prop1:0}",
        attack_tree=attack_tree_mixed_gates
    )

    # Multiple paths together is not minimal
    assert not do_layer1_check(
        "MRS(Root)",
        "{Attack1:1, Attack2:1, StepA2:1, Attack3:1, Attack4:1, Attack5:0, Attack6:0, Attack7:0, Attack8:0, Attack9:0, Attack10:0, Attack11:0, SubPathC3:0, prop1:0, prop2:0}",
        attack_tree=attack_tree_mixed_gates
    )
    assert not do_layer1_check(
        "MRS(Root)",
        "{Attack1:1, Attack2:1, StepA2:1, Attack3:1, Attack4:0, Attack5:0, Attack6:0, Attack7:0, Attack8:0, Attack9:0, Attack10:0, Attack11:0, SubPathC3:0, prop1:0, prop2:0}",
        attack_tree=attack_tree_mixed_gates
    )
