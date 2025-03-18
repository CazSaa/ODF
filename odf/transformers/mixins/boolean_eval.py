from lark import v_args, Tree


def check_bool(f, data, children, meta):
    """Check that all children are boolean values."""
    for child in children:
        if not isinstance(child, bool):
            return Tree(data, children, meta)
    return f(children)

# noinspection PyMethodMayBeStatic
class BooleanEvalMixin:
    """Mixin for evaluating boolean operators on boolean values."""

    @v_args(wrapper=check_bool)
    def impl_formula(self, items):
        return (not items[0]) or items[1]

    @v_args(wrapper=check_bool)
    def or_formula(self, items):
        return items[0] or items[1]

    @v_args(wrapper=check_bool)
    def and_formula(self, items):
        return items[0] and items[1]

    @v_args(wrapper=check_bool)
    def equiv_formula(self, items):
        return items[0] == items[1]

    @v_args(wrapper=check_bool)
    def nequiv_formula(self, items):
        return items[0] != items[1]

    @v_args(wrapper=check_bool)
    def neg_formula(self, items):
        return not items[0]
