from fractions import Fraction

from lark import Tree
from lark.visitors import Interpreter

from odf.transformers.mixins.mappings import BooleanMappingMixin


class PrePassEvidenceInterpreter(Interpreter, BooleanMappingMixin):
    def __init__(self):
        super().__init__()
        # Maps each probability_formula node (using its id) to its inherited evidence.
        self.evidence_per_formula: dict[int, dict[str, Fraction]] = {}
        self.current_evidence: dict[str, Fraction] = {}

    def probability_evidence(self, tree: Tree):
        return self.mappings_to_dict(self.visit_children(tree))

    def probability_formula(self, tree: Tree):
        # Save the current evidence for this probability_formula node.
        self.evidence_per_formula[
            id(tree.children[0])] = self.current_evidence.copy()

    def with_probability_evidence(self, tree: Tree):
        old_evidence = self.current_evidence.copy()

        # Process the evidence block (last child) and update the current evidence.
        local_evidence = self.visit(tree.children[1])
        self.current_evidence.update(local_evidence)

        self.visit(tree.children[0])

        self.current_evidence = old_evidence
