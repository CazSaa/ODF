"""Tests for the case study formulas."""
import math

import pytest
from _pytest.python_api import approx as pytest_approx

from odf.checker.layer2.check_layer2 import calc_prob
from odf.checker.layer3.check_layer3 import total_risk
from odf.transformers.configuration import parse_configuration


def approx(value, *args, **kwargs):
    """Helper function for pytest.approx that automatically sets abs parameter.
    
    For a value with exponent E, sets abs=10^(E-2) if not explicitly provided.
    For example, if value is 5.05e-06, abs will be set to 1e-08.
    """
    if 'abs' not in kwargs:
        if value != 0:
            exponent = math.floor(math.log10(abs(value)))
            kwargs['abs'] = 10 ** (exponent - 2)
    return pytest_approx(value, *args, **kwargs)


@pytest.fixture
def case_study_configuration_str():
    """Common configuration for case study tests."""
    return """{
        Strong_material: 0,
        Reflex_action_enabled: 1,
        Allow_firmware_rollback: 0,
        Sensor_redundancy: 0,
        Remote_CC_override_enabled: 1,
        Wireless_RTU_RTU_link: 1,
        RTU_CC_comm_encryption: 0
    }"""


@pytest.fixture
def case_study_configuration(case_study_configuration_str, parse_rule):
    return


@pytest.fixture
def do_case_study_layer2(do_check_layer2, case_study_models):
    """Helper to run layer 2 probability checks with case study models."""

    def _do_check(formula, configuration):
        attack_tree, fault_tree, object_graph = case_study_models
        return do_check_layer2(f"{configuration}{formula}",
                               attack_tree=attack_tree,
                               fault_tree=fault_tree,
                               object_graph=object_graph)

    return _do_check


@pytest.fixture
def max_total_risk(case_study_models):
    def _max_total_risk(object_name, evidence=None):
        if evidence is None:
            evidence = {}
        return total_risk(object_name, max, evidence, *case_study_models)

    return _max_total_risk


@pytest.fixture
def min_total_risk(case_study_models):
    def _min_total_risk(object_name, evidence=None):
        if evidence is None:
            evidence = {}
        return total_risk(object_name, min, evidence, *case_study_models)

    return _min_total_risk


@pytest.fixture
def calc_prob_fixture(case_study_models, parse_rule):
    def _calc_prob(formula, configuration_str, evidence=None):
        configuration = parse_configuration(
            parse_rule(configuration_str, "configuration"))
        if evidence is None:
            evidence = {}
        formula_tree = parse_rule(formula, "layer1_formula")
        return \
            calc_prob(configuration, evidence, formula_tree,
                      *case_study_models)[1]

    return _calc_prob


def relative_difference(a, b):
    if a == 0 and b == 0:
        return 0
    return abs(a - b) / ((a + b) / 2) if (a + b) != 0 else float('inf')


def relative_increase(a, b):
    if a == 0:
        return float('inf') if b > 0 else 0
    return (b - a) / a if a != 0 else float('inf')


def test_case_study(do_case_study_layer2, case_study_configuration_str,
                    max_total_risk, min_total_risk, calc_prob_fixture, case_study_models):
    print()
    attack_tree = case_study_models[0]
    pipeline_max_total_risk = max_total_risk("Pipeline")
    assert pipeline_max_total_risk == approx(13.2364, abs=1e-04)
    pipeline_min_total_risk = min_total_risk("Pipeline")
    assert pipeline_min_total_risk == approx(13.2305, abs=1e-04)

    relative_diff = relative_difference(pipeline_max_total_risk,
                                        pipeline_min_total_risk)
    print(
        f"Relative percent difference between max and min total risk: {relative_diff * 100}%")
    assert relative_diff == approx(4.49e-4)
    relative_inc = relative_increase(pipeline_min_total_risk,
                                     pipeline_max_total_risk)
    print(f"Relative increase in total risk: {relative_inc * 100}%")

    environment_max_total_risk = max_total_risk("Environment")
    assert environment_max_total_risk == approx(3.48e-3)
    environment_min_total_risk = min_total_risk("Environment")
    assert environment_min_total_risk == approx(2.56e-4)
    relative_diff = relative_difference(environment_max_total_risk,
                                        environment_min_total_risk)
    print(
        f"Relative percent difference between max and min total risk: {relative_diff * 100}%")
    assert relative_diff == approx(1.72)
    relative_inc = relative_increase(environment_min_total_risk,
                                     environment_max_total_risk)
    print(f"Relative increase in total risk: {relative_inc * 100}%")
    factor_increase = environment_max_total_risk / environment_min_total_risk
    assert factor_increase == approx(13.5985, abs=1e-04)
    print(f"Factor increase in total risk: {factor_increase}")

    print(
        f"The difference between max-min total risks for pipeline is {pipeline_max_total_risk - pipeline_min_total_risk}, and for environment is {environment_max_total_risk - environment_min_total_risk}")

    waterhammer_attack_prob = calc_prob_fixture("Waterhammer_attack", "{}")
    print(
        f"Waterhammer_attack probability: {float(waterhammer_attack_prob)}")
    waterhammer_attack_impact = attack_tree.nodes["Waterhammer_attack"]["data"].impact
    waterhammer_attack_risk = waterhammer_attack_prob * waterhammer_attack_impact

    waterhammer_contribution_to_min_risk = waterhammer_attack_risk * 100 / pipeline_min_total_risk
    assert waterhammer_contribution_to_min_risk == approx(99.996, abs=1e-03)
    print(f"Fraction of pipeline min risk due to Waterhammer_attack: {waterhammer_contribution_to_min_risk}")
    waterhammer_contribution_to_max_risk = waterhammer_attack_risk * 100 / pipeline_max_total_risk
    assert waterhammer_contribution_to_max_risk == approx(99.951, abs=1e-03)
    print(f"Fraction of pipeline max risk due to Waterhammer_attack: {waterhammer_contribution_to_max_risk}")









    result = do_case_study_layer2("P(Accidental_pollution) > 0.5",
                                  case_study_configuration_str)
    assert result == False
    accidental_pollution_prob = calc_prob_fixture("Accidental_pollution",
                                                  case_study_configuration_str)
    print(
        f"Accidental_pollution probability: {float(accidental_pollution_prob)}")
    assert float(accidental_pollution_prob) == approx(5.05e-06)

    result = do_case_study_layer2("P(Attacker_causes_pollution) > 0.5",
                                  case_study_configuration_str)
    assert result == False

    assert max_total_risk("Pipeline")

    assert max_total_risk("RTU")

    assert max_total_risk("Environment")

    assert min_total_risk("Pipeline")

    assert min_total_risk("RTU")
