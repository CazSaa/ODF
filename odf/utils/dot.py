import pathlib

from dd.cudd import Function

from odf.utils.dfs import dfs_nodes_with_complement


def write_bdd_to_dot_file(root: Function, path: str | pathlib.Path) -> None:
    """Write a BDD to a DOT file using integer node labels.

    Args:
        root: The root node of the BDD
        path: Path where to write the DOT file
    """
    manager = root.bdd
    with open(path, 'w') as f:
        f.write('digraph "BDD" {\n')
        f.write('    rankdir=TB;\n')
        f.write('    ordering=out;\n')

        # First pass: collect nodes by level
        nodes_by_var = {}
        for node, _ in dfs_nodes_with_complement(root, root.negated):
            if node.var is None:  # Terminal node
                continue
            nodes_by_var.setdefault(node.var, []).append(node)

        # Write nodes by level to ensure same-level nodes are aligned
        for var, nodes in sorted(nodes_by_var.items()):
            f.write(f'    {{ rank=same; ')
            for node in nodes:
                f.write(f'{int(node)} ')
            f.write('}\n')
            for node in nodes:
                f.write(
                    f'    {int(node)} [shape=circle, label="{int(node)}"];\n')

        # Write terminal nodes
        f.write('    { rank=sink; ')
        for node, _ in dfs_nodes_with_complement(root, root.negated):
            if node.var is not None:  # Skip non-terminal nodes
                continue
            f.write(f'{int(node)} ')
        f.write('}\n')
        for node, _ in dfs_nodes_with_complement(root, root.negated):
            if node.var is not None:
                continue
            if node == manager.true:
                f.write(f'    {int(node)} [shape=box, label="1"];\n')
            else:
                f.write(f'    {int(node)} [shape=box, label="0"];\n')

        # Write edges after all nodes are defined
        for node, _ in dfs_nodes_with_complement(root, root.negated):
            if node.var is None:  # Skip terminal nodes
                continue

            # Write low edge (dashed if complemented)
            low_style = 'dotted' if node.low.negated else 'dashed'
            f.write(
                f'    {int(node)} -> {int(node.low.regular)} [style={low_style}];\n')

            # Write high edge (dashed if complemented)
            high_style = 'dotted' if node.high.negated else 'solid'
            f.write(
                f'    {int(node)} -> {int(node.high.regular)} [style={high_style}];\n')

        f.write('}\n')
        f.close()
