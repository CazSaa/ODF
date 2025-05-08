"""Tests for the case study formulas."""
import math

import pytest
from _pytest.python_api import approx as pytest_approx

from odf.checker.layer2.check_layer2 import calc_prob
from odf.checker.layer3.check_layer3 import total_risk, optimal_conf
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
        RTU_CC_comm_encrypted: 0
    }"""


@pytest.fixture
def case_study_configuration(case_study_configuration_str, parse_rule):
    return


@pytest.fixture
def do_case_study_layer2(do_check_layer2):
    """Helper to run layer 2 probability checks with case study models."""

    def _do_check(formula, configuration, case_study_models):
        attack_tree, fault_tree, object_graph = case_study_models
        return do_check_layer2(f"{configuration}{formula}",
                               attack_tree=attack_tree,
                               fault_tree=fault_tree,
                               object_graph=object_graph)

    return _do_check


@pytest.fixture
def max_total_risk():
    def _max_total_risk(object_name, case_study_models, evidence=None):
        if evidence is None:
            evidence = {}
        return total_risk(object_name, max, evidence, *case_study_models)

    return _max_total_risk


@pytest.fixture
def min_total_risk():
    def _min_total_risk(object_name, case_study_models, evidence=None):
        if evidence is None:
            evidence = {}
        return total_risk(object_name, min, evidence, *case_study_models)

    return _min_total_risk


@pytest.fixture
def calc_prob_fixture(parse_rule):
    def _calc_prob(formula, configuration_str, case_study_models,
                   evidence=None):
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
                    max_total_risk, min_total_risk, calc_prob_fixture,
                    case_study_models, alternative_case_study_models):
    print()
    attack_tree = case_study_models[0]
    pipeline_max_total_risk = max_total_risk("Pipeline", case_study_models)
    assert pipeline_max_total_risk == approx(13.2364, abs=1e-04)
    pipeline_min_total_risk = min_total_risk("Pipeline", case_study_models)
    assert pipeline_min_total_risk == approx(13.2305, abs=1e-04)

    relative_diff = relative_difference(pipeline_max_total_risk,
                                        pipeline_min_total_risk)
    print(
        f"Relative percent difference between max and min total risk: {relative_diff * 100}%")
    assert relative_diff == approx(4.49e-4)
    relative_inc = relative_increase(pipeline_min_total_risk,
                                     pipeline_max_total_risk)
    print(f"Relative increase in total risk: {relative_inc * 100}%")

    environment_max_total_risk = max_total_risk("Environment",
                                                case_study_models)
    assert environment_max_total_risk == approx(3.48e-3)
    environment_min_total_risk = min_total_risk("Environment",
                                                case_study_models)
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
    assert factor_increase == approx(13.5901, abs=1e-04)
    print(f"Factor increase in total risk: {factor_increase}")

    print(
        f"The difference between max-min total risks for pipeline is {pipeline_max_total_risk - pipeline_min_total_risk}, and for environment is {environment_max_total_risk - environment_min_total_risk}")

    waterhammer_attack_prob = calc_prob_fixture("Waterhammer_attack", "{}",
                                                case_study_models)
    print(
        f"Waterhammer_attack probability: {float(waterhammer_attack_prob)}")
    waterhammer_attack_impact = attack_tree.nodes["Waterhammer_attack"][
        "data"].impact
    waterhammer_attack_risk = waterhammer_attack_prob * waterhammer_attack_impact

    waterhammer_contribution_to_min_risk = waterhammer_attack_risk * 100 / pipeline_min_total_risk
    assert waterhammer_contribution_to_min_risk == approx(99.996, abs=1e-03)
    print(
        f"Fraction of pipeline min risk due to Waterhammer_attack: {waterhammer_contribution_to_min_risk}")
    waterhammer_contribution_to_max_risk = waterhammer_attack_risk * 100 / pipeline_max_total_risk
    assert waterhammer_contribution_to_max_risk == approx(99.951, abs=1e-03)
    print(
        f"Fraction of pipeline max risk due to Waterhammer_attack: {waterhammer_contribution_to_max_risk}")

    print(
        "\n\n=================== Switching to alternative case study models ===================\n")

    pipeline_max_total_risk = max_total_risk("Pipeline",
                                             alternative_case_study_models)
    assert pipeline_max_total_risk == approx(0.1851, abs=1e-04)
    pipeline_min_total_risk = min_total_risk("Pipeline",
                                             alternative_case_study_models)
    assert pipeline_min_total_risk == approx(0.0667, abs=1e-04)
    relative_diff = relative_difference(pipeline_max_total_risk,
                                        pipeline_min_total_risk)
    print(
        f"Relative percent difference between max and min total risk: {relative_diff * 100}%")
    assert relative_diff == approx(0.9404, abs=1e-04)
    relative_inc = relative_increase(pipeline_min_total_risk,
                                     pipeline_max_total_risk)
    print(f"Relative increase in total risk: {relative_inc * 100}%")
    factor_increase = pipeline_max_total_risk / pipeline_min_total_risk
    assert factor_increase == approx(2.775, abs=1e-04)
    print(f"Factor increase in total risk: {factor_increase}")

    environment_max_total_risk = max_total_risk("Environment",
                                                alternative_case_study_models)
    assert environment_max_total_risk == approx(3.48e-3)
    environment_min_total_risk = min_total_risk("Environment",
                                                alternative_case_study_models)
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
    assert factor_increase == approx(13.5901, abs=1e-04)
    print(f"Factor increase in total risk: {factor_increase}")
    print(
        f"The difference between max-min total risks for pipeline is {pipeline_max_total_risk - pipeline_min_total_risk}, and for environment is {environment_max_total_risk - environment_min_total_risk}")

    attack_prep3_prob = calc_prob_fixture(
        "Attack_preparation3",
        "{Reflex_action_enabled: 0, Wireless_RTU_RTU_link: 1}",
        alternative_case_study_models)
    falsify_rtu_output_prob = calc_prob_fixture(
        "Falsify_RTU_output",
        "{Allow_firmware_rollback: 1}",
        alternative_case_study_models)
    protection_deactivation_prob = calc_prob_fixture(
        "Protection_deactivation",
        "{Reflex_action_enabled: 0, Remote_CC_override_enabled: 1, Wireless_RTU_RTU_link: 1, Allow_firmware_rollback: 1, RTU_CC_comm_encrypted: 0}",
        alternative_case_study_models)
    assert attack_prep3_prob != protection_deactivation_prob, "Not most likely attack"
    assert falsify_rtu_output_prob == protection_deactivation_prob, "Most likely attack"

    wao_max_risk = max_total_risk("WAO", alternative_case_study_models)
    assert wao_max_risk == approx(0.178605, abs=1e-06)
    wao_min_risk = min_total_risk("WAO", alternative_case_study_models)
    assert wao_min_risk == approx(0.06615, abs=1e-05)
    wao_div_pipeline_max = wao_max_risk / pipeline_max_total_risk
    assert wao_div_pipeline_max == approx(0.9650, abs=1e-04)
    print(
        f"WAO max risk / pipeline max risk: {wao_div_pipeline_max * 100}%")
    wao_div_pipeline_min = wao_min_risk / pipeline_min_total_risk
    assert wao_div_pipeline_min == approx(0.9918, abs=1e-04)
    print(
        f"WAO min risk / pipeline min risk: {wao_div_pipeline_min * 100}%")

    optimal_conf_environment = \
        optimal_conf("Environment", {}, *alternative_case_study_models)[1]
    optimal_conf_pipeline = \
        optimal_conf("Pipeline", {}, *alternative_case_study_models)[1]
    optimal_conf_scada = \
        optimal_conf("SCADA_system", {}, *alternative_case_study_models)[1]
    optimal_conf_rtu = optimal_conf("RTU", {}, *alternative_case_study_models)[
        1]

    assert optimal_conf_environment == approx(2.56e-04)
    assert optimal_conf_pipeline == approx(6.67e-02)
    assert optimal_conf_scada == approx(5.79e-02)
    assert optimal_conf_rtu == approx(3.47)

    optimal_conf_environment_evidence = optimal_conf(
        "Environment", {"Allow_firmware_rollback": True},
        *alternative_case_study_models)[1]
    optimal_conf_pipeline_evidence = optimal_conf(
        "Pipeline", {"Allow_firmware_rollback": True},
        *alternative_case_study_models)[1]
    optimal_conf_scada_evidence = optimal_conf(
        "SCADA_system", {"Allow_firmware_rollback": False},
        *alternative_case_study_models)[1]
    optimal_conf_rtu_evidence = optimal_conf(
        "RTU", {"Allow_firmware_rollback": False},
        *alternative_case_study_models)[1]

    environment_risk_increase = relative_increase(optimal_conf_environment,
                                                  optimal_conf_environment_evidence) * 100
    print(f"Risk for Environment increased by {environment_risk_increase}%")
    assert environment_risk_increase == approx(1253.93, abs=1e-02)

    pipeline_risk_increase = relative_increase(optimal_conf_pipeline,
                                               optimal_conf_pipeline_evidence) * 100
    print(f"Risk for Pipeline increased by {pipeline_risk_increase}%")
    assert pipeline_risk_increase == approx(173.41, abs=1e-02)

    scada_risk_increase = relative_increase(optimal_conf_scada,
                                            optimal_conf_scada_evidence) * 100
    print(f"Risk for SCADA_system increased by {scada_risk_increase}%")
    assert scada_risk_increase == approx(808.32, abs=1e-02)

    rtu_risk_increase = relative_increase(optimal_conf_rtu,
                                          optimal_conf_rtu_evidence) * 100
    print(f"Risk for RTU increased by {rtu_risk_increase}%")
    assert rtu_risk_increase == approx(20.57, abs=1e-02)

    optimal_conf_acpo, optimal_risk_acpo = optimal_conf("ACPO", {}, *alternative_case_study_models)
    assert optimal_risk_acpo == approx(2.05e-04)
    assert len(optimal_conf_acpo) == 1
    assert 'RTU_CC_comm_encrypted' not in optimal_conf_acpo[0]
    assert optimal_conf_acpo[0]['Remote_CC_override_enabled'] == False
    assert optimal_conf_acpo[0]['Allow_firmware_rollback'] == False

    optimal_conf_apo, optimal_risk_apo = optimal_conf("APO", {}, *alternative_case_study_models)
    assert optimal_risk_apo == approx(2.98e-07)
    assert len(optimal_conf_apo) == 1
    assert optimal_conf_apo[0]['Remote_CC_override_enabled'] == True
    assert optimal_conf_apo[0]['Allow_firmware_rollback'] == True

    ######## Remote_CC_override_enabled = opposite
    _, optimal_risk_acpo_rem_cc = optimal_conf("ACPO", {"Remote_CC_override_enabled": True}, *alternative_case_study_models)
    acpo_remote_cc_risk_increase = relative_increase(optimal_risk_acpo, optimal_risk_acpo_rem_cc) * 100
    print(f"Risk for ACPO increased by {acpo_remote_cc_risk_increase}%")
    assert acpo_remote_cc_risk_increase == approx(882.14, abs=1e-02)

    _, optimal_risk_apo_rem_cc = optimal_conf("APO", {"Remote_CC_override_enabled": False}, *alternative_case_study_models)
    apo_remote_cc_risk_increase = relative_increase(optimal_risk_apo, optimal_risk_apo_rem_cc) * 100
    print(f"Risk for APO increased by {apo_remote_cc_risk_increase}%")
    assert apo_remote_cc_risk_increase == approx(0.72, abs=1e-02)

    ######## Allow_firmware_rollback = opposite
    _, optimal_risk_acpo_allow_fw = optimal_conf("ACPO", {"Allow_firmware_rollback": True}, *alternative_case_study_models)
    acpo_allow_fw_risk_increase = relative_increase(optimal_risk_acpo, optimal_risk_acpo_allow_fw) * 100
    print(f"Risk for ACPO increased by {acpo_allow_fw_risk_increase}%")
    assert acpo_allow_fw_risk_increase == approx(1588, abs=1)

    _, optimal_risk_apo_allow_fw = optimal_conf("APO", {"Allow_firmware_rollback": False}, *alternative_case_study_models)
    apo_allow_fw_risk_increase = relative_increase(optimal_risk_apo, optimal_risk_apo_allow_fw) * 100
    print(f"Risk for APO increased by {apo_allow_fw_risk_increase}%")
    assert apo_allow_fw_risk_increase == approx(16775, abs=1)
