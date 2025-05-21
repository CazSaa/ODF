from lark import Token, Transformer, Tree


# noinspection PyMethodMayBeStatic
class FormulaReconstructor(Transformer):
    """Transforms a parse tree of an doglog formula back into a string."""

    def __init__(self, multiline: bool):
        super().__init__()
        self.multiline = multiline

    def configuration(self, items: list[str]) -> str:
        """Reconstruct a configuration."""
        return "{" + ", ".join(items) + "}"

    def boolean_evidence(self, items: list[str]) -> str:
        """Reconstruct boolean evidence."""
        return "[" + ", ".join(items) + "]"

    def probability_evidence(self, items: list[str]) -> str:
        """Reconstruct probability evidence."""
        return "[" + ", ".join(items) + "]"

    def boolean_mapping(self, item: list[Token]) -> str:
        """Reconstruct a boolean mapping."""
        name = str(item[0])
        value = str(item[1])
        return f"{name}: {value}"

    def probability_mapping(self, item: list[Token]) -> str:
        """Reconstruct a probability mapping."""
        name = str(item[0])
        value = str(item[1])
        return f"{name}={value}"

    def layer1_query(self, items: list[str]) -> str:
        """Reconstruct a layer 1 query."""
        assert len(items) == 1
        return items[0]

    def layer2_query(self, items: list[str]) -> str:
        """Reconstruct a layer 2 query."""
        if len(items) == 1:
            return items[0]
        assert len(items) == 2
        conf, formula = items
        return f"{conf}\n  {formula}" if self.multiline else f"{conf} {formula}"

    def layer3_query(self, items: list[str]) -> str:
        """Reconstruct a layer 3 query."""
        assert len(items) == 1
        return items[0]

    def compute_all(self, items: list[str]) -> str:
        """Reconstruct a compute all query."""
        conf, formula = items
        return f"{conf}\n  [[{formula}]]" if self.multiline else f"{conf} [[{formula}]]"

    def check(self, items: list[str]) -> str:
        """Reconstruct a check query."""
        conf, formula = items
        return f"{conf}\n  {formula}" if self.multiline else f"{conf} {formula}"

    def mrs(self, items: list[str]) -> str:
        """Reconstruct an MRS formula."""
        return f"MRS({items[0]})"

    def with_boolean_evidence(self, items: list[str]) -> str:
        """Reconstruct a formula with boolean evidence."""
        formula, evidence = items
        return f"({formula} {evidence})"

    def with_probability_evidence(self, items: list[str]) -> str:
        """Reconstruct a formula with probability evidence."""
        formula, evidence = items
        return f"({formula} {evidence})"

    def probability_formula(self, items: list[str]) -> str:
        """Reconstruct a probability formula."""
        formula, relation, prob = items
        return f"P({formula}) {relation} {prob}"

    def neg_formula(self, items: list[str]) -> str:
        """Reconstruct a negation."""
        return f"!{items[0]}"

    def and_formula(self, items: list[str]) -> str:
        """Reconstruct an AND formula."""
        lhs, rhs = items
        return f"{lhs} && {rhs}"

    def or_formula(self, items: list[str]) -> str:
        """Reconstruct an OR formula."""
        lhs, rhs = items
        return f"{lhs} || {rhs}"

    def impl_formula(self, items: list[str]) -> str:
        """Reconstruct an implication formula."""
        lhs, rhs = items
        return f"{lhs} => {rhs}"

    def equiv_formula(self, items: list[str]) -> str:
        """Reconstruct an equivalence formula."""
        lhs, rhs = items
        return f"{lhs} == {rhs}"

    def nequiv_formula(self, items: list[str]) -> str:
        """Reconstruct a non-equivalence formula."""
        lhs, rhs = items
        return f"{lhs} != {rhs}"

    def most_risky_a(self, items: list[str]) -> str:
        """Reconstruct a MostRiskyA formula."""
        return f"MostRiskyA({items[0]})"

    def most_risky_f(self, items: list[str]) -> str:
        """Reconstruct a MostRiskyF formula."""
        return f"MostRiskyF({items[0]})"

    def optimal_conf(self, items: list[str]) -> str:
        """Reconstruct an OptimalConf formula."""
        return f"OptimalConf({items[0]})"

    def max_total_risk(self, items: list[str]) -> str:
        """Reconstruct a MaxTotalRisk formula."""
        return f"MaxTotalRisk({items[0]})"

    def min_total_risk(self, items: list[str]) -> str:
        """Reconstruct a MinTotalRisk formula."""
        return f"MinTotalRisk({items[0]})"

    def node_atom(self, items: list[Token]) -> str:
        """Reconstruct a node atom."""
        return str(items[0])


def reconstruct(tree: Tree, multiline: bool = False) -> str:
    """
    Reconstructs the string representation of a parse tree.

    Args:
        tree (Tree): The parse tree to reconstruct.
        multiline: If True, the output will be formatted for multiline.

    Returns:
        str: The reconstructed string representation of the parse tree.
    """
    # There is a bug in the lark Reconstructor so I had to make my own: https://github.com/lark-parser/lark/issues/1500
    reconstructor = FormulaReconstructor(multiline)
    return reconstructor.transform(tree)
