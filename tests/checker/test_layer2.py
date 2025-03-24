def test_layer2_basic_probability(do_check_layer2, paper_example_models):
    """Test a basic Layer 2 formula evaluating probability."""
    formula = "{DF:1, LP:1} P(Attacker_breaks_in_house) == 0.17"
    assert do_check_layer2(formula, *paper_example_models) == True


def test_layer2_with_probability_evidence(do_check_layer2,
                                          paper_example_models):
    """Test Layer 2 formula with probabilistic evidence."""
    # Base case without evidence
    formula = "{DF:1, LP:1} P(Attacker_breaks_in_house) == 0.17"
    assert do_check_layer2(formula, *paper_example_models) == True

    # Test with evidence that should increase the probability
    formula_with_evidence = "{DF:1, LP:1} P(Attacker_breaks_in_house) == 0.9 [EDLU=0.9]"
    assert do_check_layer2(formula_with_evidence, *paper_example_models) == True


def test_layer2_with_nested_probability_evidence(do_check_layer2,
                                                 paper_example_models):
    """Test Layer 2 formula with nested probabilistic evidence."""
    # Formula with evidence at different levels - outer and inner
    formula = """{DF:1, LP:1} 
              (P(Attacker_breaks_in_house) == 0.8 [EDLU=0.8]) && (P(FD) == 0.9 [PL=0.9]) [DD=0.5]"""
    assert do_check_layer2(formula, *paper_example_models) == True

    formula = """{DF:1, LP:1} 
              (P(Attacker_breaks_in_house) == 0.8 [EDLU=0.8]) && (P(FD) == 0.9 [PL=0.9]) [EDLU=0.5]"""
    assert do_check_layer2(formula, *paper_example_models) == True

    formula = """{DF:1, LP:1} 
              (P(Attacker_breaks_in_house) == 0.6 [EDLU=0.6]) && (P(FD) == 0.9 [PL=0.9]) [EDLU=0.9]"""
    assert do_check_layer2(formula, *paper_example_models) == True

    formula = """{DF:1, LP:1} 
              (P(Attacker_breaks_in_house) == 0.8 [EDLU=0.8]) && (P(FD) == 0.9 [PL=0.9]) [EDLU=0.5]"""
    assert do_check_layer2(formula, *paper_example_models) == True


def test_layer2_probability_evidence_precedence(do_check_layer2,
                                                paper_example_models):
    """Test evidence precedence where inner evidence overrides outer for the same node."""
    # In this case, the inner evidence for PL (0.9) should override the outer evidence (0.1)
    formula = """{DF:1, LP:1} 
              P(FD) > 0.3 [PL=0.9] [PL=0.1]"""
    assert do_check_layer2(formula, *paper_example_models) == True

    formula = """{DF:1, LP:1} 
              P(FD) < 0.3 [PL=0.1] [PL=0.9]"""
    assert do_check_layer2(formula, *paper_example_models) == True


def test_layer2_complex_combination(do_check_layer2, paper_example_models):
    """Test a complex combination of Boolean operators and evidence.
    
    FBO DSL LGJ  | Prob(bF)            | FIAE | ABIOH | P(ABIOH||FIAE) | Product
    0   0   0    | 0.79*0.8*0.3=0.1896 | 0    | 0.5   | 0.5            | 0.0948
    0   0   1    | 0.79*0.8*0.7=0.4424 | 0    | 0.5   | 0.5            | 0.2212
    0   1   0    | 0.79*0.2*0.3=0.0474 | 0    | 0.5   | 0.5            | 0.0237
    0   1   1    | 0.79*0.2*0.7=0.1106 | 0    | 0.5   | 0.5            | 0.0553
    1   0   0    | 0.21*0.8*0.3=0.0504 | 0    | 0.5   | 0.5            | 0.0252
    1   0   1    | 0.21*0.8*0.7=0.1176 | 0    | 0.5   | 0.5            | 0.0588
    1   1   0    | 0.21*0.2*0.3=0.0126 | 0    | 0.5   | 0.5            | 0.0063
    1   1   1    | 0.21*0.2*0.7=0.0294 | 1    | 0.5   | 1              | 0.0294
                                                               Total = 0.5147
    """
    formula = """{DF:1, LP:1, Inhab_in_House:1, HS:0, IU:1, LJ:1} 
              (P(Attacker_breaks_in_house || Fire_and_impossible_escape) == 0.5147 [EDLU=0.5]) && 
              (P(FD) == 0.9 [PL=0.9, DD=0.8])"""

    assert do_check_layer2(formula, *paper_example_models) == True


def test_layer2_boundary_evidence_values(do_check_layer2, paper_example_models):
    """Test with extreme probability evidence values (0 and 1)."""
    # Node with 0 probability (impossible)
    formula_zero = "{DF:1, LP:1} P(FD) == 0 [PL=0, DD=0]"
    assert do_check_layer2(formula_zero, *paper_example_models) == True

    # Node with 1 probability (certain)
    formula_one = "{DF:1, LP:1} P(FD) == 1 [PL=1, DD=1]"
    assert do_check_layer2(formula_one, *paper_example_models) == True

    # Combination of extreme values
    formula_mixed = ("{DF:1, LP:1, Inhab_in_House:1, HS:0, IU:1, LJ:1} "
                     "P(Attacker_breaks_in_house || Fire_and_impossible_escape) > 0 [EDLU=1, FBO=0]")
    assert do_check_layer2(formula_mixed, *paper_example_models) == True


def test_layer2_evidence_on_multiple_nodes(do_check_layer2,
                                           paper_example_models):
    """Test applying evidence to many nodes simultaneously.

    FBO DSL LGJ | Prob(bF)   | FIAE         | ABIOH  | P(ABIOH||FIAE) | Product
    0   0   0   | 0.102131   | 0            | 0.43   | 0.43           | 0.04391633
    0   0   1   | 0.115169   | 0            | 0.43   | 0.43           | 0.04952267
    0   1   0   | 0.090569   | 0            | 0.43   | 0.43           | 0.03894467
    0   1   1   | 0.102131   | 0            | 0.43   | 0.43           | 0.04391633
    1   0   0   | 0.146969   | 0            | 0.43   | 0.43           | 0.06319667
    1   0   1   | 0.165731   | 0            | 0.43   | 0.43           | 0.07126433
    1   1   0   | 0.130331   | 0            | 0.43   | 0.43           | 0.05604233
    1   1   1   | 0.146969   | 1            | 0.43   | 1              | 0.146969
                                                              Total = 0.51377233
    """
    formula = """{DF:1, LP:1, Inhab_in_House:1, HS:0, IU:1, LJ:1} 
              P(Attacker_breaks_in_house || Fire_and_impossible_escape) == 0.51377233
              [PL=0.37, DD=0.41, EDLU=0.43, DSL=0.47, LGJ=0.53, FBO=0.59]"""
    assert do_check_layer2(formula, *paper_example_models) == True


def test_layer2_evidence_with_boolean_operators(do_check_layer2,
                                                paper_example_models):
    """Test how evidence interacts with boolean operators."""
    formula_and = "{DF:1, LP:1} P(PL && DD) == 0.45 [PL=0.5, DD=0.9]"
    assert do_check_layer2(formula_and, *paper_example_models) == True

    formula_and = "{DF:1, LP:1} P(PL) == 0.5 && P(DD) == 0.9 [PL=0.5, DD=0.9]"
    assert do_check_layer2(formula_and, *paper_example_models) == True

    formula_or = "{DF:1, LP:1} P(PL || DD) == 0.90 [PL=0.5, DD=0.9]"
    assert do_check_layer2(formula_or, *paper_example_models) == True

    formula_or = "{DF:1, LP:1} P(PL) == 0.5 || P(DD) == 0.9 [PL=0.5, DD=0.9]"
    assert do_check_layer2(formula_or, *paper_example_models) == True

    formula_not = "{LP:1} P(!PL) == 1 [PL=0.5]"
    assert do_check_layer2(formula_not, *paper_example_models) == True

    formula_not = "{LP:1} !P(PL) == 1 [PL=0.5]"
    assert do_check_layer2(formula_not, *paper_example_models) == True

    formula_not = "{LP:1} !P(PL) < 0.3 [PL=0.3]"
    assert do_check_layer2(formula_not, *paper_example_models) == True

    formula_not = "{LP:1} !P(PL) > 0.3 [PL=0.3]"
    assert do_check_layer2(formula_not, *paper_example_models) == True

    formula_not = "{LP:1} !P(PL) == 0.3 [PL=0.3]"
    assert do_check_layer2(formula_not, *paper_example_models) == False

    formula_complex = "{DF:1, LP:1} P(!(PL && DD) || EDLU) == 1 [PL=0.5, DD=0.9, EDLU=0.8]"
    assert do_check_layer2(formula_complex, *paper_example_models) == True

    formula_complex = "{DF:1, LP:1} P((PL && DD) || EDLU) == 0.8 [PL=0.5, DD=0.9, EDLU=0.8]"
    assert do_check_layer2(formula_complex, *paper_example_models) == True

    formula_complex = "{DF:1, LP:1} P((PL && DD) && EDLU) == 0.36 [PL=0.5, DD=0.9, EDLU=0.8]"
    assert do_check_layer2(formula_complex, *paper_example_models) == True


def test_layer2_evidence_scoping(do_check_layer2, paper_example_models):
    """Test that evidence correctly applies only within its intended scope."""
    # Test evidence applied only to one subformula
    formula = """{LP:1} 
              (P(PL) == 0.9 [PL=0.9]) && (P(PL) == 0.1)"""
    assert do_check_layer2(formula, *paper_example_models) == True

    # Test that evidence doesn't leak between unrelated subformulas
    formula_isolated = """{DF:1, LP:1} 
                        (P(PL) == 0.9 [PL=0.9]) && 
                        (P(DD) == 0.5 [DD=0.5]) && 
                        (P(PL && DD) == 0.013)"""
    assert do_check_layer2(formula_isolated, *paper_example_models) == True


def test_layer2_evidence_interactions(do_check_layer2, paper_example_models):
    """Test interactions between evidence and configurations."""
    # Test how evidence interacts with configurations
    # This test shows that evidence overrides the probability but doesn't affect 
    # whether a node is triggered based on configuration
    formula = """{LP:0} P(PL) == 0 [PL=0.9]"""
    assert do_check_layer2(formula, *paper_example_models) == True

    # Shows that boolean config and prob evidence work together
    complex_formula = """{DF:1, LP:0} P(PL && DD) == 0 [PL=0.9, DD=0.9]"""
    assert do_check_layer2(complex_formula, *paper_example_models) == True
