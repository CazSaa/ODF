def test_paper_example(do_check_layer2, attack_tree_paper_example,
                       fault_tree_paper_example, object_graph_paper_example):
    assert do_check_layer2(
        "{LP:1,LJ:1,DF:1,HS:0,IU:1} P(FD && DGB || EDLU && FBO) == 0.050078",
        attack_tree_paper_example, fault_tree_paper_example,
        object_graph_paper_example)
