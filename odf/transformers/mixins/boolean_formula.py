from dd import cudd


# noinspection PyMethodMayBeStatic
class BooleanFormulaMixin:
    """Mixin for transforming boolean formulas into BDDs. Assumes that the class
    has a `bdd` attribute."""
    bdd: cudd.BDD

    def impl_formula(self, items):
        formula1, formula2 = items
        return formula1.implies(formula2)

    def or_formula(self, items):
        return items[0] | items[1]

    def and_formula(self, items):
        return items[0] & items[1]

    def equiv_formula(self, items):
        formula1, formula2 = items
        return self.bdd.apply('equiv', formula1, formula2)

    def nequiv_formula(self, items):
        formula1, formula2 = items
        return self.bdd.apply('xor', formula1, formula2)

    def node_atom(self, items):
        return self.bdd.var(items[0].value)

    def neg_formula(self, items):
        return ~items[0]
