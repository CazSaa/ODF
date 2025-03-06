from typing import Optional

import pycudd

def list_to_int_array(arr):
    int_arr = pycudd.IntArray(len(arr))
    for i, e in enumerate(arr):
        if not isinstance(e, int):
            raise TypeError(f"Element at index {i} is not an integer")
        int_arr[i] = e
    return int_arr

def reordered(m: Optional[pycudd.DdManager] = None):
    m = pycudd.DdManager() if m is None else m
    m.SetDefault()
    dd = m.NewVar()
    df = m.NewVar()
    dsl = m.NewVar()
    edlu = m.NewVar()
    fbo = m.NewVar()
    hs = m.NewVar()
    iu = m.NewVar()
    lgj = m.NewVar()
    lj = m.NewVar()
    lp = m.NewVar()
    pl = m.NewVar()

    fd = (pl & lp) | (dd & df)
    dgb = (lgj & lj) & dsl
    fbo_ = fbo & (~hs & iu)

    formula = (fd & dgb) | (edlu & fbo_)

    vars = ["DD", "DF", "DSL", "EDLU", "FBO", "HS", "IU", "LGJ", "LJ", "LP", "PL"]
    # ind    0     1     2      3       4      5     6     7      8     9     10
    # formula.DumpDott(vars)

    intended_reordering = ['LP', 'LJ', 'DF', 'HS', 'IU', 'DSL', 'LGJ', 'FBO', 'PL',
                           'DD', 'EDLU']
    # indices               0     1     2     3     4     5      6      7      8     9     10
    permutation = [vars.index(e) for e in intended_reordering]
    print(permutation)

    m.ShuffleHeap(list_to_int_array(permutation))
    formula.DumpDott(vars)

    return formula


def correct_order_from_start(m: Optional[pycudd.DdManager] = None):
    m = pycudd.DdManager() if m is None else m
    m.SetDefault()
    lp = m.NewVar()
    lj = m.NewVar()
    df = m.NewVar()
    hs = m.NewVar()
    iu = m.NewVar()
    dsl = m.NewVar()
    lgj = m.NewVar()
    fbo = m.NewVar()
    pl = m.NewVar()
    dd = m.NewVar()
    edlu = m.NewVar()

    fd = (pl & lp) | (dd & df)
    dgb = (lgj & lj) & dsl
    fbo_ = fbo & (~hs & iu)

    formula = (fd & dgb) | (edlu & fbo_)

    vars = ["LP", "LJ", "DF", "HS", "IU", "DSL", "LGJ", "FBO", "PL", "DD", "EDLU"]
    # ind    0     1     2      3       4      5     6     7      8     9     10
    formula.DumpDott(vars)

    return formula

def test_formula_equivalence():
    """
    Create two equivalent formulas with different variable orders and test their equivalence.
    Each formula uses its own separate set of variables.
    """
    m = pycudd.DdManager()
    m.SetDefault()
    
    # Create first set of variables for formula1
    # Order: LP, LJ, DF, HS, IU, DSL, LGJ, FBO, PL, DD, EDLU
    lp1 = m.NewVar()
    lj1 = m.NewVar()
    df1 = m.NewVar()
    hs1 = m.NewVar()
    iu1 = m.NewVar()
    dsl1 = m.NewVar()
    lgj1 = m.NewVar()
    fbo1 = m.NewVar()
    pl1 = m.NewVar()
    dd1 = m.NewVar()
    edlu1 = m.NewVar()
    
    # Create formula1
    fd1 = (pl1 & lp1) | (dd1 & df1)
    dgb1 = (lgj1 & lj1) & dsl1
    fbo_1 = fbo1 & (~hs1 & iu1)
    formula1 = (fd1 & dgb1) | (edlu1 & fbo_1)
    
    # Create second set of variables for formula2
    # Order: DD, DF, DSL, EDLU, FBO, HS, IU, LGJ, LJ, LP, PL
    dd2 = m.NewVar()
    df2 = m.NewVar()
    dsl2 = m.NewVar()
    edlu2 = m.NewVar()
    fbo2 = m.NewVar()
    hs2 = m.NewVar()
    iu2 = m.NewVar()
    lgj2 = m.NewVar()
    lj2 = m.NewVar()
    lp2 = m.NewVar()
    pl2 = m.NewVar()
    
    # Create formula2
    fd2 = (pl2 & lp2) | (dd2 & df2)
    dgb2 = (lgj2 & lj2) & dsl2
    fbo_2 = fbo2 & (~hs2 & iu2)
    formula2 = (fd2 & dgb2) | (edlu2 & fbo_2)
    
    # Define lists of variables for clarity
    vars1 = [lp1, lj1, df1, hs1, iu1, dsl1, lgj1, fbo1, pl1, dd1, edlu1]
    vars2 = [dd2, df2, dsl2, edlu2, fbo2, hs2, iu2, lgj2, lj2, lp2, pl2]
    
    # Define variable name mappings
    var_names1 = ["LP", "LJ", "DF", "HS", "IU", "DSL", "LGJ", "FBO", "PL", "DD", "EDLU"]
    var_names2 = ["DD", "DF", "DSL", "EDLU", "FBO", "HS", "IU", "LGJ", "LJ", "LP", "PL"]
    
    # Create variable name to BDD node mappings
    name_to_var1 = {name: var for name, var in zip(var_names1, vars1)}
    name_to_var2 = {name: var for name, var in zip(var_names2, vars2)}
    
    # Build constraints: for each variable name, the corresponding variables must be equal
    var_constraints = m.One()
    for name in set(var_names1):
        if name in name_to_var1 and name in name_to_var2:
            var1 = name_to_var1[name]
            var2 = name_to_var2[name]
            # var1 <=> var2 is (var1 & var2) | (~var1 & ~var2)
            equiv = (var1 & var2) | (~var1 & ~var2)
            var_constraints = var_constraints & equiv
    
    # formula1 <=> formula2 is (formula1 & formula2) | (~formula1 & ~formula2)
    formula_equiv = (formula1 & formula2) | (~formula1 & ~formula2)
    
    # The implication: var_constraints => formula_equiv
    implication = ~var_constraints | formula_equiv
    
    # Check if implication is a tautology
    is_tautology = implication == m.ReadZero()
    
    # Generate dot files for visualization
    formula1.DumpDottt("formula1.dot")
    formula2.DumpDottt("formula2.dot")
    var_constraints.DumpDottt("var_constraints.dot")
    formula_equiv.DumpDottt("formula_equivalence.dot")
    implication.DumpDottt("implication.dot")
    
    print("Variable constraints => formulas equivalent:", is_tautology)
    return is_tautology



def dfs(node):
    """
    Generator function that performs depth-first traversal of a BDD starting from the given node.

    Args:
        node: A pycudd DdNode object to start the traversal from

    Yields:
        DdNode objects in DFS order
    """
    if node is None:
        return

    # Using a set to track visited nodes
    visited = set()
    stack = [node]

    while stack:
        current = stack.pop()

        # Skip if already visited
        if current in visited:
            continue

        # Mark as visited and yield
        visited.add(current)
        yield current

        # Skip further traversal if this is a terminal node
        if current.IsConstant():
            continue

        # Get then and else children and add to stack (then branch visited first)
        then_child = current.T()
        else_child = current.E()

        # Add children to stack (then branch will be processed first)
        if else_child is not None:
            stack.append(else_child)
        if then_child is not None:
            stack.append(then_child)


def replace_specific_nodes_rebuild(m, add, config_reflection_nodes, idx_to_name, vars):
    """
    Replace specific nodes by rebuilding the ADD from scratch, replacing
    target child nodes with zero.
    
    Args:
        m: DdManager instance
        add: Original ADD
        config_reflection_nodes: List of (parent, child) node tuples to replace
        idx_to_name: Dictionary mapping indices to variable names
        
    Returns:
        The modified ADD
    """
    print("\nRebuilding ADD with specific nodes replaced by zero...")
    
    # Create a set of node IDs to be replaced (for faster lookup)
    # target_edges = {(int(parent.GetNodeId()), int(child.GetNodeId())): (parent, child)
    #                 for parent, child in config_reflection_nodes}

    config_refl_set = set(config_reflection_nodes)
    
    # Cache to store already processed nodes (original_node_id -> new_node)
    processed_nodes = {}

    new_const = 2.0
    def new_const_node():
        nonlocal new_const
        ep = m.ReadEpsilon()
        # print(ep)
        new_node = m.addConst(new_const)
        new_const += 1.0
        return new_node
    
    def rebuild_node(node):
        """
        Recursively rebuild the ADD, replacing specific nodes with zero.
        """
        if node.IsConstant():
            print(f"Node {hex(node.GetNodeId())} is a terminal node with value {node.V()}")
            # Constants remain the same
            return node
        
        # Check if we've already processed this node
        if node in processed_nodes:
            print(f"Node {hex(node.GetNodeId())} already processed)")
            return processed_nodes[node]
        
        # Get children
        then_child = node.T()
        else_child = node.E()

        # Check if either child should be replaced
        new_then = new_const_node() if (node, then_child) in config_refl_set else rebuild_node(then_child)

        # If a replacement happened, print info
        if (node, then_child) in config_refl_set:
            parent, child = node, then_child
            parent_index = parent.NodeReadIndex()
            parent_name = idx_to_name.get(parent_index, "unknown")
            child_index = child.NodeReadIndex()
            child_name = idx_to_name.get(child_index, "unknown")
            print(f"  Replacing THEN edge from {parent_name}({hex(parent.GetNodeId())}) "
                  f"to {child_name}({hex(child.GetNodeId())}) with {new_then.V()}({hex(new_then.GetNodeId())})")

        new_else = new_const_node() if (node, else_child) in config_refl_set else rebuild_node(else_child)
        if (node, else_child) in config_refl_set:
            parent, child = node, else_child
            parent_index = parent.NodeReadIndex()
            parent_name = idx_to_name.get(parent_index, "unknown")
            child_index = child.NodeReadIndex()
            child_name = idx_to_name.get(child_index, "unknown")
            print(f"  Replacing ELSE edge from {parent_name}({hex(parent.GetNodeId())}) "
                  f"to {child_name}({hex(child.GetNodeId())}) with {new_else.V()}({hex(new_else.GetNodeId())})")
        
        # Create a new node with the possibly modified children
        new_node = node.addIte(new_then, new_else)
        print(f"Calling Ite for node {hex(node.GetNodeId())} with new_then={hex(new_then.GetNodeId())} and new_else={hex(new_else.GetNodeId())} resulted in {hex(new_node.GetNodeId())}")

        print("---\n")
        # Cache the result
        processed_nodes[node] = new_node
        return new_node
    
    # Start rebuilding from the root
    add.DumpDotttt("original_add.dot", vars)
    modified_add = rebuild_node(add)

    # Dump the original and modified ADDs for comparison
    modified_add.DumpDotttt("rebuild_add.dot", vars)
    
    print("Rebuild complete. Check original_add.dot and rebuild_add.dot for visualization.")
    return modified_add

def test_mtbdd(m: Optional[pycudd.DdManager] = None):
    m = pycudd.DdManager() if m is None else m
    m.SetDefault()
    lp = m.NewVar()
    lj = m.NewVar()
    df = m.NewVar()
    hs = m.NewVar()
    iu = m.NewVar()
    dsl = m.NewVar()
    lgj = m.NewVar()
    fbo = m.NewVar()
    pl = m.NewVar()
    dd = m.NewVar()
    edlu = m.NewVar()

    fd = (pl & lp) | (dd & df)
    dgb = (lgj & lj) & dsl
    fbo_ = fbo & (~hs & iu)

    formula = (fd & dgb) | (edlu & fbo_)

    vars = ["LP", "LJ", "DF", "HS", "IU", "DSL", "LGJ", "FBO", "PL", "DD", "EDLU"]
    # ind    0     1     2      3       4      5     6     7      8     9     10
    object_properties = {"LP", "LJ", "DF", "HS", "IU"}
    ft_nodes = {"DSL", "LGJ", "FBO"}
    at_nodes = {"PL", "DD", "EDLU"}
    idx_to_name = {i: name for i, name in enumerate(vars)}

    add = m.BddToAdd(formula)

    add.DumpDott(vars)

    config_reflection_nodes = []


    for node in dfs(add):
        index = node.NodeReadIndex() if not node.IsConstant() else None
        name = idx_to_name[index] if index is not None else None
        value = node.V() if node.IsConstant() else None
        is_complemented = node.IsComplement()
        print(f"node: {hex(node.GetNodeId())} ;; index: {index} ;; name: {name} ;; value: {value} ;; is_complemented: {is_complemented}")
        if node.IsConstant(): continue

        for child in [node.T(), node.E()]:
            if child is None: continue
            if name not in object_properties: continue
            if child.IsConstant():
                child_value = child.V()
                child_is_complemented = child.IsComplement()
                print(f"  Found reflection terminal: {child_value} ;; is_complemented: {child_is_complemented}")
                continue

            child_index = child.NodeReadIndex()
            child_name = idx_to_name[child_index]
            if name in object_properties and (child_name in ft_nodes or child_name in at_nodes):
                print(f"  Found reflection node: {child_name} ;; node: {hex(child.GetNodeId())}")
                config_reflection_nodes.append((node,child))

    print(config_reflection_nodes)

    # Choose which replacement method to use
    # Method 1: Vector compose approach (replaces all instances of variables)
    # modified_add1 = replace_specific_nodes_vectorcompose(m, formula, config_reflection_nodes, idx_to_name)
    
    # Method 2: Path constrained approach (replaces only specific instances)
    # modified_add2 = replace_specific_nodes_path_constrained(m, add, config_reflection_nodes, idx_to_name)

    # Method 3: Rebuild approach (builds a new ADD with specific nodes replaced)
    modified_add3 = replace_specific_nodes_rebuild(m, add, config_reflection_nodes, idx_to_name, vars)

    return formula

if __name__ == '__main__':
    test_mtbdd()
    # result = test_formula_equivalence()
    # print("Test result:", result)

