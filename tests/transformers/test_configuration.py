from odf.transformers.configuration import ConfigurationTransformer

def test_empty_configuration(parse_rule):
    """Test transforming an empty configuration."""
    transformer = ConfigurationTransformer()
    tree = parse_rule("{}", "configuration")
    result = transformer.transform(tree)
    assert result == {}

def test_single_boolean_mapping(parse_rule):
    """Test transforming a configuration with a single mapping."""
    transformer = ConfigurationTransformer()
    tree = parse_rule("{A:1}", "configuration")
    result = transformer.transform(tree)
    assert result == {"A": True}

def test_multiple_boolean_mappings(parse_rule):
    """Test transforming a configuration with multiple mappings."""
    transformer = ConfigurationTransformer()
    tree = parse_rule("{A:1, B:0}", "configuration")
    result = transformer.transform(tree)
    assert result == {"A": True, "B": False}
