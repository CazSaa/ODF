"""
Pytest fixtures for parser tests.
"""
from pathlib import Path

import pytest
from lark import Lark


@pytest.fixture(scope="session")
def grammar_path():
    """Path to the grammar file."""
    return Path(__file__).parent.parent.parent / "src" / "parser" / "grammar.lark"


@pytest.fixture(scope="session")
def grammar_text(grammar_path):
    """Raw grammar text."""
    return grammar_path.read_text()


@pytest.fixture(scope="session")
def parser(grammar_text):
    """Lark parser instance."""
    return Lark(grammar_text, parser="earley", propagate_positions=True, strict=True)


@pytest.fixture(scope="session")
def make_parser(grammar_text):
    """Create a parser with a specific start rule."""

    def _make_parser(start):
        return Lark(grammar_text, parser="earley", propagate_positions=True, start=start, strict=True)

    return _make_parser


@pytest.fixture
def parse(parser):
    """Helper fixture to parse input text using the default start rule."""

    def _parse(text):
        return parser.parse(text)

    return _parse


@pytest.fixture
def parse_rule(make_parser):
    """Helper fixture to parse input text using a specific start rule."""

    def _parse_rule(text, start):
        parser = make_parser(start)
        return parser.parse(text)

    return _parse_rule
