"""Tests for the case study formulas."""
import math
import os
import re
import subprocess
from fractions import Fraction

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


def format_value_for_latex(value, precision=4):
    """Formats a numeric value for LaTeX, handling potential None or non-numeric types.
    
    Uses scientific notation for numbers outside the range [0.01, 100000].
    """
    if isinstance(value, (int, float, Fraction)):
        if (0.01 <= abs(value) < 100000) or value == 0:
            # Standard decimal format
            return f"{{:.{precision}f}}".format(value)
        else:
            # Scientific notation
            return f"{{:.{precision}e}}".format(value)
    return str(value)  # Fallback for non-numeric or unexpected types


@pytest.fixture
def case_study_configuration_str():
    """Common configuration for case study tests."""
    return """{
        Strong_material: 0,
        Reflex_action_enabled: 1,
        Allow_firmware_rollback: 0,
        Redundant_sensors: 0,
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
    assert pipeline_max_total_risk == approx(13.2365, abs=1e-04)
    pipeline_min_total_risk = min_total_risk("Pipeline", case_study_models)
    assert pipeline_min_total_risk == approx(13.2305, abs=1e-04)

    pipeline_relative_inc = relative_increase(pipeline_min_total_risk,
                                              pipeline_max_total_risk) * 100
    print(f"Relative increase in total risk: {pipeline_relative_inc}%")

    environment_max_total_risk = max_total_risk("Environment",
                                                case_study_models)
    assert environment_max_total_risk == approx(3.48e-3)
    environment_min_total_risk = min_total_risk("Environment",
                                                case_study_models)
    assert environment_min_total_risk == approx(2.56e-4)
    environment_relative_inc = relative_increase(environment_min_total_risk,
                                                 environment_max_total_risk)
    print(f"Relative increase in total risk: {environment_relative_inc * 100}%")
    factor_increase = environment_max_total_risk / environment_min_total_risk
    assert factor_increase == approx(13.5986, abs=1e-04)
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

    # Store original model values before they are potentially overwritten
    orig_pipeline_max_total_risk = pipeline_max_total_risk
    orig_pipeline_min_total_risk = pipeline_min_total_risk
    orig_pipeline_relative_inc = pipeline_relative_inc

    orig_environment_max_total_risk = environment_max_total_risk
    orig_environment_min_total_risk = environment_min_total_risk
    orig_environment_factor_increase = orig_environment_max_total_risk / orig_environment_min_total_risk

    orig_waterhammer_attack_impact = waterhammer_attack_impact
    orig_waterhammer_attack_prob = waterhammer_attack_prob
    orig_waterhammer_attack_risk = waterhammer_attack_risk
    orig_waterhammer_contrib_min_risk_percent = waterhammer_contribution_to_min_risk
    orig_waterhammer_contrib_max_risk_percent = waterhammer_contribution_to_max_risk

    print(
        "\n\n=================== Switching to alternative case study models ===================\n")

    pipeline_max_total_risk = max_total_risk("Pipeline",
                                             alternative_case_study_models)
    assert pipeline_max_total_risk == approx(7.42e-03)
    pipeline_min_total_risk = min_total_risk("Pipeline",
                                             alternative_case_study_models)
    assert pipeline_min_total_risk == approx(6.04e-04)
    relative_inc = relative_increase(pipeline_min_total_risk,
                                     pipeline_max_total_risk)
    print(f"Relative increase in total risk: {relative_inc * 100}%")
    factor_increase = pipeline_max_total_risk / pipeline_min_total_risk
    assert factor_increase == approx(12.29, abs=1e-02)
    print(f"Factor increase in total risk: {factor_increase}")

    environment_max_total_risk = max_total_risk("Environment",
                                                alternative_case_study_models)
    assert environment_max_total_risk == approx(3.48e-3)
    assert environment_max_total_risk == orig_environment_max_total_risk
    environment_min_total_risk = min_total_risk("Environment",
                                                alternative_case_study_models)
    assert environment_min_total_risk == approx(2.56e-4)
    assert environment_min_total_risk == orig_environment_min_total_risk
    relative_inc = relative_increase(environment_min_total_risk,
                                     environment_max_total_risk)
    print(f"Relative increase in total risk: {relative_inc * 100}%")
    factor_increase = environment_max_total_risk / environment_min_total_risk
    assert factor_increase == approx(13.5986, abs=1e-04)
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
    assert wao_max_risk == approx(9.36e-04)
    wao_min_risk = min_total_risk("WAO", alternative_case_study_models)
    assert wao_min_risk == approx(5.55e-05)
    wao_div_pipeline_max = wao_max_risk / pipeline_max_total_risk
    assert wao_div_pipeline_max == approx(0.1261, abs=1e-04)
    print(
        f"WAO max risk / pipeline max risk: {wao_div_pipeline_max * 100}%")
    wao_div_pipeline_min = wao_min_risk / pipeline_min_total_risk
    assert wao_div_pipeline_min == approx(0.0919, abs=1e-04)
    print(
        f"WAO min risk / pipeline min risk: {wao_div_pipeline_min * 100}%")

    optimal_conf_environment, optimal_risk_environment = \
        optimal_conf("Environment", {}, *alternative_case_study_models)
    optimal_conf_pipeline, optimal_risk_pipeline = \
        optimal_conf("Pipeline", {}, *alternative_case_study_models)
    optimal_conf_scada, optimal_risk_scada = \
        optimal_conf("SCADA_system", {}, *alternative_case_study_models)
    optimal_conf_rtu, optimal_risk_rtu = (
        optimal_conf("RTU", {}, *alternative_case_study_models))

    assert optimal_risk_environment == approx(2.56e-04)
    assert len(optimal_conf_environment) == 1
    assert optimal_conf_environment[0] == {
        'Allow_firmware_rollback': False, 'Remote_CC_override_enabled': False,
        'Reflex_action_enabled': True, 'Wireless_RTU_RTU_link': False,
        'Redundant_sensors': True, 'Strong_material': True,
    }

    assert optimal_risk_pipeline == approx(6.04e-04)
    assert len(optimal_conf_pipeline) == 1
    assert optimal_conf_pipeline[0] == {
        'Allow_firmware_rollback': False, 'Remote_CC_override_enabled': False,
        'Reflex_action_enabled': True, 'Wireless_RTU_RTU_link': False,
        'Redundant_sensors': True, 'Strong_material': True,
    }

    assert optimal_risk_scada == approx(5.79e-02)
    assert len(optimal_conf_scada) == 1
    assert optimal_conf_scada[0] == {
        'Reflex_action_enabled': True,
        'Redundant_sensors': True, 'Allow_firmware_rollback': True,
        'Wireless_RTU_RTU_link': False
    }

    assert optimal_risk_rtu == approx(3.47)
    assert len(optimal_conf_rtu) == 1
    assert optimal_conf_rtu[0] == {
        'Wireless_RTU_RTU_link': False, 'Allow_firmware_rollback': True,
        'Remote_CC_override_enabled': False, 'Reflex_action_enabled': True,
        'Redundant_sensors': True, 'RTU_CC_comm_encrypted': False
    }

    optimal_conf_environment_evidence, optimal_risk_environment_evidence = optimal_conf(
        "Environment", {"Allow_firmware_rollback": True},
        *alternative_case_study_models)
    optimal_conf_pipeline_evidence, optimal_risk_pipeline_evidence = optimal_conf(
        "Pipeline", {"Allow_firmware_rollback": True},
        *alternative_case_study_models)
    optimal_conf_scada_evidence, optimal_risk_scada_evidence = optimal_conf(
        "SCADA_system", {"Allow_firmware_rollback": False},
        *alternative_case_study_models)
    optimal_conf_rtu_evidence, optimal_risk_rtu_evidence = optimal_conf(
        "RTU", {"Allow_firmware_rollback": False},
        *alternative_case_study_models)

    assert len(optimal_conf_environment_evidence) == 1
    assert optimal_conf_environment_evidence[0] == {
        'Remote_CC_override_enabled': True, 'Reflex_action_enabled': True,
        'Redundant_sensors': True, 'Strong_material': True,
        'Wireless_RTU_RTU_link': False
    }

    assert len(optimal_conf_pipeline_evidence) == 1
    assert optimal_conf_pipeline_evidence[0] == {
        'Remote_CC_override_enabled': True, 'Reflex_action_enabled': True,
        'Redundant_sensors': True, 'Strong_material': True,
         'Wireless_RTU_RTU_link': False
    }

    assert len(optimal_conf_scada_evidence) == 1
    assert optimal_conf_scada_evidence[0] == {
        'Reflex_action_enabled': True, 'Redundant_sensors': True,
        'Remote_CC_override_enabled': False,
        'Wireless_RTU_RTU_link': False
    }

    assert len(optimal_conf_rtu_evidence) == 1
    assert optimal_conf_rtu_evidence[0] == {
        'Remote_CC_override_enabled': False, 'Reflex_action_enabled': True,
        'Redundant_sensors': True, 'RTU_CC_comm_encrypted': False,
        'Wireless_RTU_RTU_link': False
    }

    environment_risk_increase = relative_increase(optimal_risk_environment,
                                                  optimal_risk_environment_evidence) * 100
    print(f"Risk for Environment increased by {environment_risk_increase}%")
    assert environment_risk_increase == approx(1253.87, abs=1e-02)

    pipeline_risk_increase = relative_increase(optimal_risk_pipeline,
                                               optimal_risk_pipeline_evidence) * 100
    print(f"Risk for Pipeline increased by {pipeline_risk_increase}%")
    assert pipeline_risk_increase == approx(677.43, abs=1e-02)

    scada_risk_increase = relative_increase(optimal_risk_scada,
                                            optimal_risk_scada_evidence) * 100
    print(f"Risk for SCADA_system increased by {scada_risk_increase}%")
    assert scada_risk_increase == approx(806.92, abs=1e-02)

    rtu_risk_increase = relative_increase(optimal_risk_rtu,
                                          optimal_risk_rtu_evidence) * 100
    print(f"Risk for RTU increased by {rtu_risk_increase}%")
    assert rtu_risk_increase == approx(20.58, abs=1e-02)

    optimal_conf_acpo, optimal_risk_acpo = optimal_conf("ACPO", {},
                                                        *alternative_case_study_models)
    assert optimal_risk_acpo == approx(2.05e-04)
    assert len(optimal_conf_acpo) == 1
    assert 'RTU_CC_comm_encrypted' not in optimal_conf_acpo[0]
    assert optimal_conf_acpo[0]['Remote_CC_override_enabled'] == False
    assert optimal_conf_acpo[0]['Allow_firmware_rollback'] == False
    assert optimal_conf_acpo[0] == {
        'Allow_firmware_rollback': False, 'Reflex_action_enabled': True,
        'Remote_CC_override_enabled': False, 'Wireless_RTU_RTU_link': False,
    }

    optimal_conf_apo, optimal_risk_apo = optimal_conf("APO", {},
                                                      *alternative_case_study_models)
    assert optimal_risk_apo == approx(3.08e-07)
    assert len(optimal_conf_apo) == 1
    assert optimal_conf_apo[0] == {
        'Allow_firmware_rollback': True, 'Remote_CC_override_enabled': True,
        'Reflex_action_enabled': True, 'Wireless_RTU_RTU_link': False,
        'Redundant_sensors': True, 'Strong_material': True,
    }

    ######## Remote_CC_override_enabled = opposite
    optimal_conf_acpo_rem_cc, optimal_risk_acpo_rem_cc = optimal_conf("ACPO", {
        "Remote_CC_override_enabled": True}, *alternative_case_study_models)
    acpo_remote_cc_risk_increase = relative_increase(optimal_risk_acpo,
                                                     optimal_risk_acpo_rem_cc) * 100
    print(f"Risk for ACPO increased by {acpo_remote_cc_risk_increase}%")
    assert acpo_remote_cc_risk_increase == approx(882.14, abs=1e-02)
    assert len(optimal_conf_acpo_rem_cc) == 1
    assert optimal_conf_acpo_rem_cc[0] == {
        'Allow_firmware_rollback': False, 'Reflex_action_enabled': True
    }

    optimal_conf_apo_rem_cc, optimal_risk_apo_rem_cc = optimal_conf("APO", {
        "Remote_CC_override_enabled": False}, *alternative_case_study_models)
    apo_remote_cc_risk_increase = relative_increase(optimal_risk_apo,
                                                    optimal_risk_apo_rem_cc) * 100
    print(f"Risk for APO increased by {apo_remote_cc_risk_increase}%")
    assert apo_remote_cc_risk_increase == approx(0.72, abs=1e-02)
    assert len(optimal_conf_apo_rem_cc) == 1
    assert optimal_conf_apo_rem_cc[0] == {
        'Reflex_action_enabled': True, 'Strong_material': True,
         'Redundant_sensors': True,
        'Allow_firmware_rollback': True, 'Wireless_RTU_RTU_link': False
    }

    ######## Allow_firmware_rollback = opposite
    optimal_conf_acpo_allow_fw, optimal_risk_acpo_allow_fw = optimal_conf(
        "ACPO", {"Allow_firmware_rollback": True},
        *alternative_case_study_models)
    acpo_allow_fw_risk_increase = relative_increase(optimal_risk_acpo,
                                                    optimal_risk_acpo_allow_fw) * 100
    print(f"Risk for ACPO increased by {acpo_allow_fw_risk_increase}%")
    assert acpo_allow_fw_risk_increase == approx(1588, abs=1)
    assert len(optimal_conf_acpo_allow_fw) == 1
    assert optimal_conf_acpo_allow_fw[0] == {}

    optimal_conf_apo_allow_fw, optimal_risk_apo_allow_fw = optimal_conf("APO", {
        "Allow_firmware_rollback": False}, *alternative_case_study_models)
    apo_allow_fw_risk_increase = relative_increase(optimal_risk_apo,
                                                   optimal_risk_apo_allow_fw) * 100
    print(f"Risk for APO increased by {apo_allow_fw_risk_increase}%")
    assert apo_allow_fw_risk_increase == approx(16230, abs=1)
    assert len(optimal_conf_apo_allow_fw) == 1
    assert optimal_conf_apo_allow_fw[0] == {
        'Remote_CC_override_enabled': True, 'Reflex_action_enabled': True,
        'Redundant_sensors': True, 'Strong_material': True,
         'Wireless_RTU_RTU_link': False
    }

    # --- Generate LaTeX commands file ---
    latex_commands = []

    def add_cmd(name, value, precision=4):
        latex_commands.append(
            f"\\newcommand{{\\{name}}}{{{format_value_for_latex(value, precision)}}}")

    # Add original model values
    add_cmd("PipelineMaxTotalRisk", orig_pipeline_max_total_risk)
    add_cmd("PipelineMinTotalRisk", orig_pipeline_min_total_risk)
    add_cmd("PipelineRelativeIncrease", orig_pipeline_relative_inc,
            precision=2)  # Example: 44.90% -> 44.90

    add_cmd("EnvironmentMaxTotalRisk", orig_environment_max_total_risk)
    add_cmd("EnvironmentMinTotalRisk", orig_environment_min_total_risk)
    add_cmd("EnvironmentFactorIncrease", orig_environment_factor_increase,
            precision=2)

    add_cmd("WaterhammerAttackImpact", orig_waterhammer_attack_impact,
            precision=0)
    add_cmd("WaterhammerAttackProbability", orig_waterhammer_attack_prob,
            precision=2)
    add_cmd("WaterhammerAttackRisk", orig_waterhammer_attack_risk, precision=2)
    add_cmd("WaterhammerPipelineMinRiskPercentage",
            orig_waterhammer_contrib_min_risk_percent)
    add_cmd("WaterhammerPipelineMaxRiskPercentage",
            orig_waterhammer_contrib_max_risk_percent)

    # Add adapted model values (variables are now holding these after reassignment)
    adapt_pipeline_max_total_risk = pipeline_max_total_risk  # This is the adapted value from L167
    adapt_pipeline_min_total_risk = pipeline_min_total_risk  # This is the adapted value from L170

    add_cmd("PipelineMaxTotalRiskAdapt", adapt_pipeline_max_total_risk)
    add_cmd("PipelineMinTotalRiskAdapt", adapt_pipeline_min_total_risk)

    adapt_pipeline_risk_percentage_increase = relative_increase(
        adapt_pipeline_min_total_risk,
        adapt_pipeline_max_total_risk) * 100  # from L177-179
    add_cmd("PipelineRiskPercentageIncreaseAdapt",
            adapt_pipeline_risk_percentage_increase, precision=2)

    if adapt_pipeline_max_total_risk != 0:
        adapt_wa_max_risk_fraction = (
                                             wao_max_risk / adapt_pipeline_max_total_risk) * 100  # from L223
    else:
        adapt_wa_max_risk_fraction = float('inf')
    add_cmd("WaterhammerAttackMaxRiskFractionAdapt", adapt_wa_max_risk_fraction,
            precision=2)

    if adapt_pipeline_min_total_risk != 0:
        adapt_wa_min_risk_fraction = (
                                             wao_min_risk / adapt_pipeline_min_total_risk) * 100  # from L227
    else:
        adapt_wa_min_risk_fraction = float('inf')
    add_cmd("WaterhammerAttackMinRiskFractionAdapt", adapt_wa_min_risk_fraction,
            precision=2)

    # These variables (environment_risk_increase, etc.) were calculated using alternative_case_study_models
    add_cmd("EnvironmentFactorIncreaseAdapt", environment_risk_increase,
            precision=2)  # L259
    add_cmd("PipelineFactorIncreaseAdapt", pipeline_risk_increase,
            precision=2)  # L264
    add_cmd("SCADARiskFactorIncreaseAdapt", scada_risk_increase,
            precision=2)  # L269
    add_cmd("RTURiskFactorIncreaseAdapt", rtu_risk_increase,
            precision=2)  # L274

    add_cmd("ACPORemoteCCRiskIncreaseAdapt", acpo_remote_cc_risk_increase,
            precision=2)  # L294
    add_cmd("APORemoteCCRiskIncreaseAdapt", apo_remote_cc_risk_increase,
            precision=2)  # L299

    add_cmd("ACPOAllowFirmwareRiskIncreaseAdapt", acpo_allow_fw_risk_increase,
            precision=0)  # L305
    add_cmd("APOAllowFirmwareRiskIncreaseAdapt", apo_allow_fw_risk_increase,
            precision=0)  # L310

    # Determine output path
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    # Path should be ../../report/chapters/case-study/ relative to tests/ directory
    output_dir = os.path.join(current_script_dir, "..", "..", "report",
                              "chapters", "case-study")

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    output_file_path = os.path.join(output_dir,
                                    "case_study_generated_values.tex")

    with open(output_file_path, "w") as f:
        f.write("% Auto-generated LaTeX commands for case study values\n")
        f.write(f"% Generated from {os.path.basename(__file__)}\n\n")
        for cmd_string in latex_commands:
            f.write(cmd_string + "\n")

    print(f"\nLaTeX commands for case study written to: {output_file_path}")

    # --- Generate LaTeX for CLI output ---
    print("\nStarting generation of LaTeX for CLI output...")
    generate_cli_output_latex()


# --- Functions for CLI Output to LaTeX ---

CLI_COMMAND_TEMPLATE = "python -m odf {}"
ODF_FILES_INFO = [
    {"path": "docs/case-study.odf", "prefix": "genFormulaOutput"},
    {"path": "docs/case-study-adapt.odf", "prefix": "genFormulaOutputAdapt"},
]
# Path relative to this script (tests/test_case_study.py) for the subdirectory
CLI_OUTPUT_FILES_SUBDIR = "../../report/chapters/case-study/cli_outputs/"


def run_cli_for_latex(odf_file_path_relative_to_project_root):
    """Runs the ODF CLI tool and captures its output for LaTeX generation."""
    command = CLI_COMMAND_TEMPLATE.format(
        odf_file_path_relative_to_project_root)
    try:
        # project_root is one level up from the 'tests' directory where this script resides
        project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..")
        print(
            f"Running CLI: {command} in {project_root} for ODF file: {odf_file_path_relative_to_project_root}")
        # Ensure the ODF file path is correctly joined if it's not already project root relative
        # For this setup, ODF_FILES_INFO paths are already relative to project root.

        env = os.environ.copy()
        env["COLUMNS"] = "75"  # Set desired terminal width

        result = subprocess.run(
            command,
            shell=True,  # Using shell=True for convenience with `python -m`
            capture_output=True,
            text=True,
            cwd=project_root,
            check=True,
            encoding='utf-8',  # Explicitly set encoding
            env=env
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(
            f"Error running CLI for {odf_file_path_relative_to_project_root}: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return None
    except FileNotFoundError:
        # This error means 'python' itself (or the first part of the command) wasn't found.
        print(
            f"Error: The command '{command.split()[0]}' was not found. Ensure Python is in PATH and the virtual environment (if any) is active.")
        return None
    except Exception as e:
        print(
            f"An unexpected error occurred while running CLI for {odf_file_path_relative_to_project_root}: {e}")
        return None


def parse_cli_output_for_latex(raw_output):
    """
    Parses the raw CLI output to extract blocks for each formula.
    Returns a dictionary: {formula_number_str: raw_block_string}
    """
    formula_blocks = {}
    # Regex to capture the formula number and the entire block associated with it.
    # It captures from "---" above "Processing Formula X" up to just before the next "---"
    # or "Processing Complete."
    # Using re.DOTALL so '.' matches newlines via (?s)
    # Adjusted to handle the exact ANSI sequence from the sample.
    pattern = re.compile(
        r"(?s)(---------------------------------------------------------------------------\s*\x1b\[90mProcessing Formula (\d+):\x1b\[0m.*?)(?=\n---------------------------------------------------------------------------\s*\x1b\[90mProcessing Formula|\nProcessing Complete\.)"
    )

    for match in pattern.finditer(raw_output):
        full_block_content = match.group(
            1).strip()  # group(1) is the entire block
        formula_number = match.group(2)  # group(2) is the formula number
        formula_blocks[formula_number] = full_block_content

    return formula_blocks


def generate_cli_output_listing_files(all_formula_outputs_data):
    """
    Generates individual .tex files for each formula's CLI output.
    Each file contains a lstlisting environment with the raw ANSI output.
    all_formula_outputs_data is a list of dicts:
        [{"prefix": "genFormulaOutput", "blocks": {num_str: block_str}}]
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # CLI_OUTPUT_FILES_SUBDIR is relative to this script's location (tests/)
    # So, os.path.join(script_dir, CLI_OUTPUT_FILES_SUBDIR) gives the absolute path to the target subdir
    output_subdir_abs_path = os.path.abspath(
        os.path.join(script_dir, CLI_OUTPUT_FILES_SUBDIR))

    try:
        os.makedirs(output_subdir_abs_path, exist_ok=True)
        print(
            f"Ensured CLI output subdirectory exists: {output_subdir_abs_path}")
    except OSError as e:
        print(
            f"Error creating CLI output subdirectory '{output_subdir_abs_path}': {e}")
        return  # Cannot proceed if directory creation fails

    files_generated_count = 0
    for item_data in all_formula_outputs_data:
        # prefix will be like "genFormulaOutput" or "genFormulaOutputAdapt"
        # We want filenames like "cli_formula_one.tex" or "cli_formula_adapt_one.tex"
        # So, we'll derive a file prefix from item_data["prefix"]
        file_prefix_base = "cli_formula_"
        if "Adapt" in item_data["prefix"]:
            file_prefix_base = "cli_formula_adapt_"

        blocks = item_data["blocks"]
        if not blocks:
            print(
                f"Note: No formula blocks found for ODF file associated with prefix '{item_data['prefix']}'. No .tex files generated for this set.")
            continue

        for number_str, raw_block_str in blocks.items():
            try:
                filename = f"{file_prefix_base}{number_str}.tex"
                file_abs_path = os.path.join(output_subdir_abs_path, filename)

                # Content for the individual .tex file
                # The lstlisting environment uses options defined globally via \lstset in helpers/commands.tex
                file_content = f"% Auto-generated CLI output for formula {number_str} from {item_data['path']}\n"
                file_content += f"% Source ODF: {item_data['path']}, Formula No: {number_str}\n"
                file_content += "\\begin{lstlisting}[breaklines=true, basicstyle=\\ttfamily\\footnotesize]\n"
                file_content += f"{raw_block_str}\n"
                file_content += "\\end{lstlisting}\n"

                with open(file_abs_path, "w", encoding='utf-8') as f:
                    f.write(file_content)
                # print(f"Generated: {file_abs_path}")
                files_generated_count += 1
            except ValueError:
                print(
                    f"Error: Formula number '{number_str}' is not a valid integer. Skipping file generation for this formula under {item_data['prefix']}.")
                continue
            except IOError as e:
                print(f"Error writing CLI output file '{file_abs_path}': {e}")
            except Exception as e:
                print(
                    f"An unexpected error occurred while generating file for formula {number_str} ('{item_data['prefix']}'): {e}")

    if files_generated_count > 0:
        print(
            f"\nSuccessfully generated {files_generated_count} individual .tex files for CLI outputs in: {output_subdir_abs_path}")
    else:
        print(
            f"\nNo individual .tex files for CLI outputs were generated (or all attempts failed) into: {output_subdir_abs_path}")


def generate_cli_output_latex():
    """Orchestrates running CLI, parsing, and generating individual .tex files for CLI outputs."""
    all_parsed_data_for_latex = []

    for odf_file_item in ODF_FILES_INFO:  # ODF_FILES_INFO contains 'path' and 'prefix'
        print(
            f"Processing ODF file for LaTeX CLI output: {odf_file_item['path']}")
        raw_cli_output = run_cli_for_latex(odf_file_item['path'])

        current_file_blocks = {}
        if raw_cli_output:
            parsed_blocks = parse_cli_output_for_latex(raw_cli_output)
            if parsed_blocks:
                current_file_blocks = parsed_blocks
                print(
                    f"Successfully parsed {len(parsed_blocks)} formula blocks from {odf_file_item['path']}.")
            else:
                print(
                    f"Warning: No formula blocks parsed from the output of {odf_file_item['path']}.")
        else:
            print(
                f"Failed to get CLI output for {odf_file_item['path']}. No .tex files will be generated from this ODF.")

        all_parsed_data_for_latex.append({
            "prefix": odf_file_item["prefix"],
            # Used to determine if it's "adapt" or not for filename
            "path": odf_file_item["path"],
            # For comments in the generated files
            "blocks": current_file_blocks
        })

    if any(item["blocks"] for item in all_parsed_data_for_latex):
        generate_cli_output_listing_files(all_parsed_data_for_latex)
    else:
        print(
            "No CLI output was successfully parsed from any ODF file. No individual .tex listing files generated.")
