from functools import cache
from pathlib import Path

from lark import Token, Tree, Lark


@cache
def parser():
    with open(Path(__file__).parent / "grammar.lark") as grammar:
        return Lark(grammar, maybe_placeholders=False)


def parse(text: str) -> Tree[Token]:
    return parser().parse(text, 'start')
