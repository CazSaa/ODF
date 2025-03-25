from dd import cudd

from odf.transformers.mixins.decorators import interpreter_or_transformer


# noinspection PyMethodMayBeStatic
class BooleanFormulaMixin:
    """Mixin for transforming boolean formulas into BDDs. Assumes that the class
    has a `bdd` attribute."""
    bdd: cudd.BDD

    @interpreter_or_transformer
    def impl_formula(self, items):
        formula1, formula2 = items
        return formula1.implies(formula2)

    @interpreter_or_transformer
    def or_formula(self, items):
        return items[0] | items[1]

    @interpreter_or_transformer
    def and_formula(self, items):
        return items[0] & items[1]

    @interpreter_or_transformer
    def equiv_formula(self, items):
        formula1, formula2 = items
        return self.bdd.apply('equiv', formula1, formula2)

    @interpreter_or_transformer
    def nequiv_formula(self, items):
        formula1, formula2 = items
        return self.bdd.apply('xor', formula1, formula2)

    @interpreter_or_transformer
    def node_atom(self, items):
        return self.bdd.var(items[0].value)

    @interpreter_or_transformer
    def neg_formula(self, items):
        return ~items[0]
