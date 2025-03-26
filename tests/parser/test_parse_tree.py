from lark import Tree, Token


def test_basic_node_tree(parse_rule):
    """Test exact tree structure of a basic node."""
    result = parse_rule("A prob = 0.5", "basic_node")
    expected = Tree(Token("RULE", "basic_node"), [
        Token("NODE_NAME", "A"),
        Tree(Token("RULE", "attribute_list"), [
            Tree(Token("RULE", "probability"), [
                Token("PROB_VALUE", "0.5")
            ])
        ])
    ])
    assert result == expected


def test_basic_node_full_attributes_tree(parse_rule):
    """Test exact tree structure of a basic node with all attributes."""
    result = parse_rule("A prob = 0.5 objects = [obj1, obj2] cond = (x && y)",
                        "basic_node")
    expected = Tree(Token("RULE", "basic_node"), [
        Token("NODE_NAME", "A"),
        Tree(Token("RULE", "attribute_list"), [
            Tree(Token("RULE", "probability"), [
                Token("PROB_VALUE", "0.5")
            ]),
            Tree(Token("RULE", "objects"), [
                Tree(Token("RULE", "node_list"), [
                    Token("NODE_NAME", "obj1"),
                    Token("NODE_NAME", "obj2")
                ])
            ]),
            Tree(Token("RULE", "condition"), [
                Tree(Token("RULE", "and_formula"), [
                    Tree("node_atom", [
                        Token("NODE_NAME", "x")
                    ]),
                    Tree("node_atom", [
                        Token("NODE_NAME", "y")
                    ])
                ])
            ])
        ])
    ])
    assert result == expected


def test_intermediate_node_tree(parse_rule):
    """Test exact tree structure of an intermediate node."""
    result = parse_rule("A and B C", "intermediate_node")
    expected = Tree(Token("RULE", "intermediate_node"), [
        Token("NODE_NAME", "A"),
        Tree("and_gate", []),
        Token("NODE_NAME", "B"),
        Token("NODE_NAME", "C")
    ])
    assert result == expected


def test_disruption_tree_structure(parse_rule):
    """Test exact tree structure of a simple disruption tree."""
    tree_text = """toplevel Root;
    Root and A B;
    A prob = 0.5;
    B;"""
    result = parse_rule(tree_text, "disruption_tree")
    expected = Tree(Token("RULE", "disruption_tree"), [
        Tree(Token("RULE", "tln"), [
            Token("NODE_NAME", "Root")
        ]),
        Tree(Token("RULE", "intermediate_node"), [
            Token("NODE_NAME", "Root"),
            Tree("and_gate", []),
            Token("NODE_NAME", "A"),
            Token("NODE_NAME", "B")
        ]),
        Tree(Token("RULE", "basic_node"), [
            Token("NODE_NAME", "A"),
            Tree(Token("RULE", "attribute_list"), [
                Tree(Token("RULE", "probability"), [
                    Token("PROB_VALUE", "0.5")
                ])
            ])
        ]),
        Tree(Token("RULE", "basic_node"), [
            Token("NODE_NAME", "B")
        ])
    ])
    assert result == expected


def test_object_graph_tree_structure(parse_rule):
    """Test exact tree structure of an object graph."""
    graph_text = """
    System has Comp1 Comp2;
    Comp1 properties = [prop1];
    Comp2;"""
    result = parse_rule(graph_text, "object_graph_tree")
    expected = Tree(Token("RULE", "object_graph_tree"), [
        Tree(Token("RULE", "intermediate_object"), [
            Token("NODE_NAME", "System"),
            Token("NODE_NAME", "Comp1"),
            Token("NODE_NAME", "Comp2")
        ]),
        Tree(Token("RULE", "basic_object"), [
            Token("NODE_NAME", "Comp1"),
            Tree(Token("RULE", "properties"), [
                Tree(Token("RULE", "node_list"), [
                    Token("NODE_NAME", "prop1")
                ])
            ])
        ]),
        Tree(Token("RULE", "basic_object"), [
            Token("NODE_NAME", "Comp2")
        ])
    ])
    assert result == expected


def test_layer1_query_tree(parse_rule):
    """Test exact tree structure of a Layer 1 formula."""
    result = parse_rule("{}MRS(A && B)", "layer1_query")
    expected = Tree("check", [
        Tree(Token("RULE", "configuration"), []),
        Tree("mrs", [
            Tree(Token("RULE", "and_formula"), [
                Tree("node_atom", [
                    Token("NODE_NAME", "A")
                ]),
                Tree("node_atom", [
                    Token("NODE_NAME", "B")
                ])
            ])
        ])
    ])
    assert result == expected


def test_layer2_query_tree(parse_rule):
    """Test exact tree structure of a Layer 2 formula."""
    result = parse_rule("{A: 1} P(B) >= 0.5", "layer2_query")
    expected = Tree(Token("RULE", "layer2_query"), [
        Tree(Token("RULE", "configuration"), [
            Tree(Token("RULE", "boolean_mapping"), [
                Token("NODE_NAME", "A"),
                Token("TRUTH_VALUE", "1")
            ])
        ]),
        Tree("probability_formula", [
            Tree("node_atom", [
                Token("NODE_NAME", "B")
            ]),
            Token("RELATION", ">="),
            Token("PROB_VALUE", "0.5")
        ])
    ])
    assert result == expected


def test_layer3_formula_tree(parse_rule):
    """Test exact tree structure of a Layer 3 formula."""
    result = parse_rule("MostRiskyA(System)", "layer3_query")
    expected = Tree(Token("RULE", "layer3_query"), [
        Tree("most_risky_a", [
            Token("NODE_NAME", "System")
        ])
    ])
    assert result == expected


def test_complete_odg_tree(parse):
    """Test exact tree structure of a complete minimal ODG."""
    odg_text = """[odg.attack_tree]
    toplevel A;
    A;

    [odg.fault_tree]
    toplevel B;
    B;

    [odg.object_graph]
    C;

    [formulas]
    {}A;"""
    result = parse(odg_text)
    expected = Tree(Token("RULE", "start"), [
        Tree(Token("RULE", "attack_tree"), [
            Tree(Token("RULE", "disruption_tree"), [
                Tree(Token("RULE", "tln"), [
                    Token("NODE_NAME", "A")
                ]),
                Tree(Token("RULE", "basic_node"), [
                    Token("NODE_NAME", "A")
                ])
            ])
        ]),
        Tree(Token("RULE", "fault_tree"), [
            Tree(Token("RULE", "disruption_tree"), [
                Tree(Token("RULE", "tln"), [
                    Token("NODE_NAME", "B")
                ]),
                Tree(Token("RULE", "basic_node"), [
                    Token("NODE_NAME", "B")
                ])
            ])
        ]),
        Tree(Token("RULE", "object_graph"), [
            Tree(Token("RULE", "object_graph_tree"), [
                Tree(Token("RULE", "basic_object"), [
                    Token("NODE_NAME", "C")
                ])
            ])
        ]),
        Tree(Token("RULE", "odglog"), [
            Tree(Token("RULE", "layer1_query"), [
                Tree("check", [
                    Tree(Token("RULE", "configuration"), []),
                    Tree("node_atom", [
                        Token("NODE_NAME", "A")
                    ])
                ])
            ])
        ])
    ])
    assert result == expected


def test_complex_layer1_query_tree(parse_rule):
    """Test exact tree structure of a complex Layer 1 formula with nested operations and evidence."""
    result = parse_rule(
        "{}MRS(!A && B || ((C [ZZ: 1]) => D) [Z: 0]) [X: 1, Y: 0]",
                        "layer1_query")
    expected = Tree("check", [
        Tree(Token("RULE", "configuration"), []),
        Tree(Token("RULE", "with_boolean_evidence"), [
            Tree("mrs", [
                Tree(Token("RULE", "with_boolean_evidence"), [
                    Tree(Token("RULE", "or_formula"), [
                        Tree(Token("RULE", "and_formula"), [
                            Tree("neg_formula", [
                                Tree("node_atom", [
                                    Token("NODE_NAME", "A")
                                ])
                            ]),
                            Tree("node_atom", [
                                Token("NODE_NAME", "B")
                            ])
                        ]),
                        Tree(Token("RULE", "impl_formula"), [
                            Tree(Token("RULE", "with_boolean_evidence"), [
                                Tree("node_atom", [
                                    Token("NODE_NAME", "C")
                                ]),
                                Tree(Token("RULE", "boolean_evidence"), [
                                    Tree(Token("RULE", "boolean_mapping"), [
                                        Token("NODE_NAME", "ZZ"),
                                        Token("TRUTH_VALUE", "1")
                                    ])
                                ])
                            ]),
                            Tree("node_atom", [
                                Token("NODE_NAME", "D")
                            ])
                        ])
                    ]),
                    Tree(Token("RULE", "boolean_evidence"), [
                        Tree(Token("RULE", "boolean_mapping"), [
                            Token("NODE_NAME", "Z"),
                            Token("TRUTH_VALUE", "0")
                        ])
                    ])
                ])
            ]),
            Tree(Token("RULE", "boolean_evidence"), [
                Tree(Token("RULE", "boolean_mapping"), [
                    Token("NODE_NAME", "X"),
                    Token("TRUTH_VALUE", "1")
                ]),
                Tree(Token("RULE", "boolean_mapping"), [
                    Token("NODE_NAME", "Y"),
                    Token("TRUTH_VALUE", "0")
                ])
            ])
        ])
    ])
    assert result.pretty() == expected.pretty()
    assert result == expected


def test_complex_layer2_query_tree(parse_rule):
    """Test exact tree structure of a complex Layer 2 formula with multiple probability formulas."""
    result = parse_rule("{A: 1} P(X && Y) < 0.3 && P(Z) >= 0.7", "layer2_query")
    expected = Tree(Token("RULE", "layer2_query"), [
        Tree(Token("RULE", "configuration"), [
            Tree(Token("RULE", "boolean_mapping"), [
                Token("NODE_NAME", "A"),
                Token("TRUTH_VALUE", "1")
            ])
        ]),
        Tree(Token("RULE", "and_formula"), [
            Tree("probability_formula", [
                Tree(Token("RULE", "and_formula"), [
                    Tree("node_atom", [
                        Token("NODE_NAME", "X")
                    ]),
                    Tree("node_atom", [
                        Token("NODE_NAME", "Y")
                    ])
                ]),
                Token("RELATION", "<"),
                Token("PROB_VALUE", "0.3")
            ]),
            Tree("probability_formula", [
                Tree("node_atom", [
                    Token("NODE_NAME", "Z")
                ]),
                Token("RELATION", ">="),
                Token("PROB_VALUE", "0.7")
            ])
        ])
    ])
    assert result == expected


def test_layer3_formula_with_evidence_tree(parse_rule):
    """Test exact tree structure of a Layer 3 formula with evidence."""
    result = parse_rule("OptimalConf(System) [A: 1, B: 0]", "layer3_formula")
    expected = Tree("with_boolean_evidence", [
        Tree("optimal_conf", [
            Token("NODE_NAME", "System")
        ]),
        Tree(Token("RULE", "boolean_evidence"), [
            Tree(Token("RULE", "boolean_mapping"), [
                Token("NODE_NAME", "A"),
                Token("TRUTH_VALUE", "1")
            ]),
            Tree(Token("RULE", "boolean_mapping"), [
                Token("NODE_NAME", "B"),
                Token("TRUTH_VALUE", "0")
            ])
        ])
    ])
    assert result == expected


def test_compute_all_layer1_query_tree(parse_rule):
    """Test exact tree structure of a compute_all (double brackets) Layer 1 formula."""
    result = parse_rule("{A: 1} [[MRS(B) [X: 1]]]", "layer1_query")
    expected = Tree("compute_all", [
        Tree(Token("RULE", "configuration"), [
            Tree(Token("RULE", "boolean_mapping"), [
                Token("NODE_NAME", "A"),
                Token("TRUTH_VALUE", "1")
            ])
        ]),
        Tree(Token("RULE", "with_boolean_evidence"), [
            Tree("mrs", [
                Tree("node_atom", [
                    Token("NODE_NAME", "B")
                ])
            ]),
            Tree(Token("RULE", "boolean_evidence"), [
                Tree(Token("RULE", "boolean_mapping"), [
                    Token("NODE_NAME", "X"),
                    Token("TRUTH_VALUE", "1")
                ])
            ])
        ])
    ])
    print()
    print(expected.pretty())
    print(result.pretty())
    assert result == expected


def test_equiv_formula_tree(parse_rule):
    """Test exact tree structure of equiv and nequiv formulas."""
    result = parse_rule("A == B != C", "boolean_formula")
    expected = Tree(Token("RULE", "nequiv_formula"), [
        Tree(Token("RULE", "equiv_formula"), [
            Tree("node_atom", [
                Token("NODE_NAME", "A")
            ]),
            Tree("node_atom", [
                Token("NODE_NAME", "B")
            ])
        ]),
        Tree("node_atom", [
            Token("NODE_NAME", "C")
        ])
    ])
    assert result == expected


def test_all_layer3_formulas_tree(parse_rule):
    """Test exact tree structure of all Layer 3 formula types."""
    formulas = {
        "most_risky_a": "MostRiskyA(A)",
        "most_risky_f": "MostRiskyF(B)",
        "optimal_conf": "OptimalConf(C)",
        "max_total_risk": "MaxTotalRisk(D)",
        "min_total_risk": "MinTotalRisk(E)"
    }

    for data, formula in formulas.items():
        result = parse_rule(formula, "layer3_query")
        expected = Tree(Token("RULE", "layer3_query"), [
            Tree(data, [
                Token("NODE_NAME",
                      formula[formula.index("(") + 1:formula.index(")")])
            ])
        ])
        assert result == expected


def test_layer2_with_probability_evidence_tree(parse_rule):
    """Test exact tree structure of Layer 2 formula with probability evidence."""
    result = parse_rule("{A: 1} P(X) >= 0.5 [X=0.7, Y=0.3]", "layer2_query")
    expected = Tree(Token("RULE", "layer2_query"), [
        Tree(Token("RULE", "configuration"), [
            Tree(Token("RULE", "boolean_mapping"), [
                Token("NODE_NAME", "A"),
                Token("TRUTH_VALUE", "1")
            ])
        ]),
        Tree("with_probability_evidence", [
            Tree("probability_formula", [
                Tree("node_atom", [
                    Token("NODE_NAME", "X")
                ]),
                Token("RELATION", ">="),
                Token("PROB_VALUE", "0.5")
            ]),
            Tree(Token("RULE", "probability_evidence"), [
                Tree(Token("RULE", "probability_mapping"), [
                    Token("NODE_NAME", "X"),
                    Token("PROB_VALUE", "0.7")
                ]),
                Tree(Token("RULE", "probability_mapping"), [
                    Token("NODE_NAME", "Y"),
                    Token("PROB_VALUE", "0.3")
                ])
            ])
        ])
    ])
    assert result == expected


def test_layer2_with_more_probabilities(parse_rule):
    result = parse_rule(
        "{A: 1, B: 0} (P(X) >= 0.3 [X=0.8]) && (P(X) < 0.7 [X=0.2]) [Y=0.1]",
        "layer2_query")
    expected = Tree(Token("RULE", "layer2_query"), [
        Tree(Token("RULE", "configuration"), [
            Tree(Token("RULE", "boolean_mapping"), [
                Token("NODE_NAME", "A"),
                Token("TRUTH_VALUE", "1")
            ]),
            Tree(Token("RULE", "boolean_mapping"), [
                Token("NODE_NAME", "B"),
                Token("TRUTH_VALUE", "0")
            ])
        ]),
        Tree("with_probability_evidence", [
            Tree(Token("RULE", "and_formula"), [
                Tree("with_probability_evidence", [
                    Tree("probability_formula", [
                        Tree("node_atom", [
                            Token("NODE_NAME", "X")
                        ]),
                        Token("RELATION", ">="),
                        Token("PROB_VALUE", "0.3")
                    ]),
                    Tree(Token("RULE", "probability_evidence"), [
                        Tree(Token("RULE", "probability_mapping"), [
                            Token("NODE_NAME", "X"),
                            Token("PROB_VALUE", "0.8")
                        ])
                    ])
                ]),
                Tree("with_probability_evidence", [
                    Tree("probability_formula", [
                        Tree("node_atom", [
                            Token("NODE_NAME", "X")
                        ]),
                        Token("RELATION", "<"),
                        Token("PROB_VALUE", "0.7")
                    ]),
                    Tree(Token("RULE", "probability_evidence"), [
                        Tree(Token("RULE", "probability_mapping"), [
                            Token("NODE_NAME", "X"),
                            Token("PROB_VALUE", "0.2")
                        ])
                    ])
                ])
            ]),
            Tree(Token("RULE", "probability_evidence"), [
                Tree(Token("RULE", "probability_mapping"), [
                    Token("NODE_NAME", "Y"),
                    Token("PROB_VALUE", "0.1")
                ])
            ])
        ])
    ])
    assert result == expected


def test_attribute_list_orderings_tree(parse_rule):
    """Test exact tree structure of attribute lists with different orderings."""
    variations = [
        ("A objects = [o1] prob = 0.5 cond = (x)",
         Tree(Token("RULE", "basic_node"), [
             Token("NODE_NAME", "A"),
             Tree(Token("RULE", "attribute_list"), [
                 Tree(Token("RULE", "objects"), [
                     Tree(Token("RULE", "node_list"), [
                         Token("NODE_NAME", "o1")
                     ])
                 ]),
                 Tree(Token("RULE", "probability"), [
                     Token("PROB_VALUE", "0.5")
                 ]),
                 Tree(Token("RULE", "condition"), [
                     Tree("node_atom", [
                         Token("NODE_NAME", "x")
                     ])
                 ])
             ])
         ])),
        ("A cond = (x) objects = [o1] prob = 0.5",
         Tree(Token("RULE", "basic_node"), [
             Token("NODE_NAME", "A"),
             Tree(Token("RULE", "attribute_list"), [
                 Tree(Token("RULE", "condition"), [
                     Tree("node_atom", [
                         Token("NODE_NAME", "x")
                     ])
                 ]),
                 Tree(Token("RULE", "objects"), [
                     Tree(Token("RULE", "node_list"), [
                         Token("NODE_NAME", "o1")
                     ])
                 ]),
                 Tree(Token("RULE", "probability"), [
                     Token("PROB_VALUE", "0.5")
                 ])
             ])
         ])),
        ("A prob = 0.5 cond = (x) objects = [o1]",
         Tree(Token("RULE", "basic_node"), [
             Token("NODE_NAME", "A"),
             Tree(Token("RULE", "attribute_list"), [
                 Tree(Token("RULE", "probability"), [
                     Token("PROB_VALUE", "0.5")
                 ]),
                 Tree(Token("RULE", "condition"), [
                     Tree("node_atom", [
                         Token("NODE_NAME", "x")
                     ])
                 ]),
                 Tree(Token("RULE", "objects"), [
                     Tree(Token("RULE", "node_list"), [
                         Token("NODE_NAME", "o1")
                     ])
                 ])
             ])
         ]))
    ]

    for input_str, expected in variations:
        result = parse_rule(input_str, "basic_node")
        assert result == expected


def test_all_relations_tree(parse_rule):
    """Test exact tree structure with all available relations."""
    relations = ["<", "<=", "==", ">=", ">"]

    for rel in relations:
        result = parse_rule(f"{{A: 1}} P(X) {rel} 0.5", "layer2_query")
        expected = Tree(Token("RULE", "layer2_query"), [
            Tree(Token("RULE", "configuration"), [
                Tree(Token("RULE", "boolean_mapping"), [
                    Token("NODE_NAME", "A"),
                    Token("TRUTH_VALUE", "1")
                ])
            ]),
            Tree("probability_formula", [
                Tree("node_atom", [
                    Token("NODE_NAME", "X")
                ]),
                Token("RELATION", rel),
                Token("PROB_VALUE", "0.5")
            ])
        ])
        assert result == expected


def test_node_list_variations_tree(parse_rule):
    """Test exact tree structure of node lists with multiple nodes."""
    result = parse_rule("objects = [A, B, C, D]", "objects")
    expected = Tree(Token("RULE", "objects"), [
        Tree(Token("RULE", "node_list"), [
            Token("NODE_NAME", "A"),
            Token("NODE_NAME", "B"),
            Token("NODE_NAME", "C"),
            Token("NODE_NAME", "D")
        ])
    ])
    assert result == expected


def test_latex_operators_tree(parse_rule):
    """Test exact tree structure using LaTeX operators."""
    result = parse_rule(r"A \land B \lor \neg C \implies D \equiv E \nequiv F",
                        "boolean_formula")
    expected = Tree(Token("RULE", "impl_formula"), [
        Tree(Token("RULE", "or_formula"), [
            Tree(Token("RULE", "and_formula"), [
                Tree("node_atom", [
                    Token("NODE_NAME", "A")
                ]),
                Tree("node_atom", [
                    Token("NODE_NAME", "B")
                ])
            ]),
            Tree("neg_formula", [
                Tree("node_atom", [
                    Token("NODE_NAME", "C")
                ])
            ])
        ]),
        Tree(Token("RULE", "nequiv_formula"), [
            Tree(Token("RULE", "equiv_formula"), [
                Tree("node_atom", [
                    Token("NODE_NAME", "D")
                ]),
                Tree("node_atom", [
                    Token("NODE_NAME", "E")
                ])
            ]),
            Tree("node_atom", [
                Token("NODE_NAME", "F")
            ])
        ])
    ])
    assert result.pretty() == expected.pretty()
    assert result == expected


def test_operator_associativity(parse_rule):
    """Test operator associativity (left vs right) in boolean formulas."""
    # Test right-associative implication (a => b => c parses as a => (b => c))
    result = parse_rule("a => b => c", "boolean_formula")
    expected = Tree(Token("RULE", "impl_formula"), [
        Tree("node_atom", [
            Token("NODE_NAME", "a")
        ]),
        Tree(Token("RULE", "impl_formula"), [
            Tree("node_atom", [
                Token("NODE_NAME", "b")
            ]),
            Tree("node_atom", [
                Token("NODE_NAME", "c")
            ])
        ])
    ])
    assert result == expected

    # Test left-associative equality (a == b == c parses as (a == b) == c)
    result = parse_rule("a == b != c", "boolean_formula")
    expected = Tree(Token("RULE", "nequiv_formula"), [
        Tree(Token("RULE", "equiv_formula"), [
            Tree("node_atom", [
                Token("NODE_NAME", "a")
            ]),
            Tree("node_atom", [
                Token("NODE_NAME", "b")
            ])
        ]),
        Tree("node_atom", [
            Token("NODE_NAME", "c")
        ])
    ])
    assert result == expected

    # Test left-associative AND (a && b && c parses as (a && b) && c)
    result = parse_rule("a && b && c", "boolean_formula")
    expected = Tree(Token("RULE", "and_formula"), [
        Tree(Token("RULE", "and_formula"), [
            Tree("node_atom", [
                Token("NODE_NAME", "a")
            ]),
            Tree("node_atom", [
                Token("NODE_NAME", "b")
            ])
        ]),
        Tree("node_atom", [
            Token("NODE_NAME", "c")
        ])
    ])
    assert result == expected

    # Test left-associative OR (a || b || c parses as (a || b) || c)
    result = parse_rule("a || b || c", "boolean_formula")
    expected = Tree(Token("RULE", "or_formula"), [
        Tree(Token("RULE", "or_formula"), [
            Tree("node_atom", [
                Token("NODE_NAME", "a")
            ]),
            Tree("node_atom", [
                Token("NODE_NAME", "b")
            ])
        ]),
        Tree("node_atom", [
            Token("NODE_NAME", "c")
        ])
    ])
    assert result == expected

    # Test right-associative parenthesis with OR ( a || (b || c) parses as a || (b || c) )
    result = parse_rule("a || (b || c)", "boolean_formula")
    expected = Tree(Token("RULE", "or_formula"), [
        Tree("node_atom", [
            Token("NODE_NAME", "a")
        ]),
        Tree(Token("RULE", "or_formula"), [
            Tree("node_atom", [
                Token("NODE_NAME", "b")
            ]),
            Tree("node_atom", [
                Token("NODE_NAME", "c")
            ])
        ])
    ])
    assert result == expected


def test_multiple_probability_evidences_tree(parse_rule):
    """
    Test a Layer 2 query tree with multiple probability evidences
    on different levels.
    """
    input_str = "{A: 1, B: 0} (P(X) >= 0.3 [X=0.8]) && (P(Y) < 0.7 [Y=0.2]) [Z=0.1, W=0.9]"
    result = parse_rule(input_str, "layer2_query")

    # Expected parse tree:
    # layer2_query
    #   configuration
    #     boolean_mapping: A: 1
    #     boolean_mapping: B: 0
    #   with_probability_evidence (outer evidence from [Z=0.1, W=0.9])
    #     and_formula
    #       with_probability_evidence (left subformula evidence)
    #         probability_formula
    #           node_atom: X
    #           RELATION: >=
    #           PROB_VALUE: 0.3
    #         probability_evidence
    #           probability_mapping: X=0.8
    #       with_probability_evidence (right subformula evidence)
    #         probability_formula
    #           node_atom: Y
    #           RELATION: <
    #           PROB_VALUE: 0.7
    #         probability_evidence
    #           probability_mapping: Y=0.2
    #     probability_evidence (outer evidence)
    #       probability_mapping: Z=0.1
    #       probability_mapping: W=0.9
    expected = Tree(Token("RULE", "layer2_query"), [
        Tree(Token("RULE", "configuration"), [
            Tree(Token("RULE", "boolean_mapping"), [
                Token("NODE_NAME", "A"),
                Token("TRUTH_VALUE", "1")
            ]),
            Tree(Token("RULE", "boolean_mapping"), [
                Token("NODE_NAME", "B"),
                Token("TRUTH_VALUE", "0")
            ])
        ]),
        Tree("with_probability_evidence", [
            Tree("and_formula", [
                Tree("with_probability_evidence", [
                    Tree("probability_formula", [
                        Tree("node_atom", [
                            Token("NODE_NAME", "X")
                        ]),
                        Token("RELATION", ">="),
                        Token("PROB_VALUE", "0.3")
                    ]),
                    Tree(Token("RULE", "probability_evidence"), [
                        Tree(Token("RULE", "probability_mapping"), [
                            Token("NODE_NAME", "X"),
                            Token("PROB_VALUE", "0.8")
                        ])
                    ])
                ]),
                Tree("with_probability_evidence", [
                    Tree("probability_formula", [
                        Tree("node_atom", [
                            Token("NODE_NAME", "Y")
                        ]),
                        Token("RELATION", "<"),
                        Token("PROB_VALUE", "0.7")
                    ]),
                    Tree(Token("RULE", "probability_evidence"), [
                        Tree(Token("RULE", "probability_mapping"), [
                            Token("NODE_NAME", "Y"),
                            Token("PROB_VALUE", "0.2")
                        ])
                    ])
                ])
            ]),
            Tree(Token("RULE", "probability_evidence"), [
                Tree(Token("RULE", "probability_mapping"), [
                    Token("NODE_NAME", "Z"),
                    Token("PROB_VALUE", "0.1")
                ]),
                Tree(Token("RULE", "probability_mapping"), [
                    Token("NODE_NAME", "W"),
                    Token("PROB_VALUE", "0.9")
                ])
            ])
        ])
    ])

    assert result == expected
