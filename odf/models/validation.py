from odf.models.disruption_tree import DisruptionTree
from odf.models.exceptions import CrossReferenceError
from odf.models.object_graph import ObjectGraph


def validate_unique_node_names(attack_tree: DisruptionTree,
                               fault_tree: DisruptionTree,
                               object_graph: ObjectGraph) -> None:
    """Validate that all node names are unique across all trees.
    
    Names must be unique across attack tree nodes, fault tree nodes,
    and object graph nodes to prevent ambiguity in references. Object
    property names must also not conflict with node names.
    
    Args:
        attack_tree: The attack tree to validate
        fault_tree: The fault tree to validate
        object_graph: The object graph to validate
    
    Raises:
        CrossReferenceError: If any node names are duplicated
    """
    node_names = set()

    for tree in [attack_tree, fault_tree, object_graph]:
        for node_name in tree.nodes:
            if node_name in node_names:
                raise CrossReferenceError(f"Node name '{node_name}' is used in"
                                          f" multiple trees")
            node_names.add(node_name)

    # Check for conflicts between node names and property names
    for prop in object_graph.object_properties:
        if prop in node_names:
            raise CrossReferenceError(
                f"Property name '{prop}' conflicts with existing node name")


def validate_disruption_tree_references(dt: DisruptionTree,
                                        og: ObjectGraph) -> None:
    """Validate that all object and property references in a disruption tree
    exist in the object graph.
    
    Args:
        dt: The disruption tree to validate
        og: The object graph to validate against
    
    Raises:
        ValidationError: If any reference is invalid
    """
    # Build a map of object names to their properties
    object_properties: dict[str, set[str]] = {}
    for node in og.nodes_obj():
        if node.properties is not None:
            object_properties[node.name] = set(node.properties)
        else:
            object_properties[node.name] = set()

    # Validate each node in the disruption tree
    for node in dt.nodes_obj():
        # Validate object references
        if node.objects is not None:
            for obj_name in node.objects:
                if obj_name not in og:
                    raise CrossReferenceError(
                        f"Node '{node.name}' references non-existent object"
                        f" '{obj_name}'")

        # Validate object property references in conditions
        properties = node.object_properties

        # If node has no objects, it can't reference properties
        if node.objects is None and len(properties) > 0:
            raise CrossReferenceError(
                f"Node '{node.name}' has properties in its condition but no"
                f" associated objects")

        # Check each property exists in at least one of the node's objects
        for prop in properties:
            valid_property = False
            for obj_name in node.objects:
                if prop in object_properties[obj_name]:
                    valid_property = True
                    break
            if not valid_property:
                raise CrossReferenceError(
                    f"Node '{node.name}' references property '{prop}' which"
                    f" doesn't exist in any of its objects {node.objects}")
