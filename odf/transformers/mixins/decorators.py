from functools import wraps
from typing import Callable, TypeVar, Any

from lark.visitors import Interpreter, visit_children_decor

T = TypeVar('T')


def interpreter_or_transformer(f: Callable[..., T]) -> Callable[..., T]:
    """Decorator that applies visit_children_decor only when the method is used in an Interpreter.
    When used in a Transformer, the original method behavior is preserved.
    """

    @wraps(f)
    def wrapper(self: Any, *args, **kwargs) -> T:
        # Check if we're in an Interpreter context
        if isinstance(self, Interpreter):
            # Apply the visit_children_decor to the method
            decorated = visit_children_decor(f)
            return decorated(self, *args, **kwargs)
        # In Transformer context, use original behavior
        return f(self, *args, **kwargs)

    return wrapper
