import argparse
import sys

from lark import UnexpectedInput, Tree
from lark.exceptions import VisitError

from odf.parser.parser import parse
from odf.transformers.disruption_tree import DisruptionTreeTransformer
from odf.transformers.exceptions import MyVisitError
from odf.transformers.object_graph import ObjectGraphTransformer


def extract_parse_trees(parse_tree: Tree):
    assert parse_tree.data == "start"

    attack_parse_tree = None
    fault_parse_tree = None
    object_parse_tree = None
    formulas_parse_tree = None
    for child in parse_tree.children:
        if child.data == "attack_tree":
            attack_parse_tree = child
        elif child.data == "fault_tree":
            fault_parse_tree = child
        elif child.data == "object_graph":
            object_parse_tree = child
        elif child.data == "odglog":
            formulas_parse_tree = child

    assert (attack_parse_tree is not None and fault_parse_tree is not None and
            object_parse_tree is not None and formulas_parse_tree is not None)

    return [attack_parse_tree, fault_parse_tree,
            object_parse_tree, formulas_parse_tree]


def execute_str(odl_text):
    parse_tree = parse(odl_text)
    [attack_parse_tree, fault_parse_tree,
     object_parse_tree, formulas_parse_tree] = extract_parse_trees(parse_tree)
    try:
        attack_tree = DisruptionTreeTransformer().transform(attack_parse_tree)
    except VisitError as e:
        raise MyVisitError(e, "attack tree")
    try:
        fault_tree = DisruptionTreeTransformer().transform(fault_parse_tree)
    except VisitError as e:
        raise MyVisitError(e, "fault tree")
    try:
        object_graph = ObjectGraphTransformer().transform(object_parse_tree)
    except VisitError as e:
        raise MyVisitError(e, "object graph")


def main(odl_text: str):
    try:
        return execute_str(odl_text)
    except UnexpectedInput as e:
        print(f"Parse error:\n{e}\n", file=sys.stderr)
        sys.exit(1)
    except MyVisitError as e:
        print(f"Error in {e.part}: {e.visit_error.orig_exc}\n",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        prog="python -m odf",
        description="Executes a BFL file and prints the results.")
    argparser.add_argument("file",
                           help="path to the BFL file you want to execute",
                           type=argparse.FileType("r"))
    args = argparser.parse_args()
    try:
        file_text = args.file.read()
    finally:
        args.file.close()
    main(file_text)
