ODF: Object-oriented Disruption Framework
==========================================

ODF is a Python implementation and extension of the concepts presented in the DODGE framework [1].
It provides a language for defining Object-oriented Disruption Graphs (ODGs) and implements the ODGLog logic for
analyzing them.

ODF provides a complete framework that includes:

1. A domain-specific language for specifying ODGs (consisting of attack trees, fault trees, and object graphs),
2. ASCII syntax for defining ODGLog formulas,
3. A Python implementation for checking ODGLog formulas,
4. A command-line interface for executing ODGLog formulas on ODGs.

This implementation uses Binary Decision Diagrams (BDDs) and Multi-Terminal Binary Decision Diagrams (MTBDDs) via
(a [fork](https://github.com/CazSaa/dd) of) the [`dd` library](https://pypi.org/project/dd/).

# Background

Familiarity with attack trees, fault trees, object graphs, and ODGLog (as described in the DODGE paper [1]) is assumed.
This README focuses on the specifics of this implementation.

## Key Concepts Recap

* **ODG (Object-oriented Disruption Graph):** Combines an attack tree, fault tree, and object graph to model system
  disruptions and their relation to system objects.
* **ODGLog:** A three-layered logic for reasoning about ODGs:
    * **Layer 1:** Disruption propagation (Boolean logic).
    * **Layer 2:** Probabilistic reasoning about disruption propagation probabilities.
    * **Layer 3:** Object-centric risk analysis (object risk exposure, optimal configurations).

# Installation

This project uses `uv` for dependency management and requires **Python 3.13** or higher.

1. Install `uv` by following the instructions in [their documentation](https://docs.astral.sh/uv/)
2. Install all necessary tools to compile `CUDD` (as part of `dd`), refer to your operating system's documentation for
   details:
    - `gcc`
    - `g++`
    - `make`
3. Clone the ODF repository and `cd` into it
4. Create a virtual environment and activate it:
    ```bash
    $ uv venv
    $ source .venv/bin/activate
    ```
5. Install dependencies using `uv`:
    ```bash
    $ uv sync --no-dev --group build --no-group compile
    $ DD_FETCH=1 DD_CUDD=1 DD_CUDD_ADD=1 uv sync --no-dev --all-groups
    ```
   The first command installs all project dependencies plus the dependencies required to build the `CUDD` extensions of
   the `dd` library.
   The second command installs the `dd` library and compiles the `CUDD` extensions.

# Usage

You can use ODF via its command-line interface.

From the root of this repository, with the virtual environment activated, run:

```bash
$ python -m odf <path/to/your/odf_file.odf>
```

Replace `<path/to/your/odf_file.odf>` with the path to your input file.

The application will parse the file, build the internal models, execute the specified ODGLog formulas, and print the
results to the console with structured, colored output.

# Input File Format (`.odf`)

An `.odf` file defines the Object-oriented Disruption Graph (ODG) and the ODGLog formulas to evaluate. It uses a
section-based format. All four sections are required but can appear in any order. Comments start with `//`. An example
of a complete `.odf` file can be found at [docs/odf-example.odf](docs/odf-example.odf).

## 1. Attack Tree (`[odg.attack_tree]`)

Defines the attack tree structure and node attributes.

* `toplevel NODE_NAME;`: (Required) Declares the root node of the attack tree. `NODE_NAME` must be a valid C-style
  identifier (i.e., it must start with a letter and can contain letters, digits, and underscores, regex:
  `^[a-zA-Z_][a-zA-Z0-9_]*$`).
* `IntermediateNode GATE ChildNode1 ChildNode2 ...;`: Defines an intermediate node (`IntermediateNode`) with a specified
  `GATE` (`and` or `or`) and its children (`ChildNode1`, `ChildNode2`, etc.). At least 1 child is required.
* `NodeName [attributes];`: Defines attributes for *any* node (`NodeName`), whether it's a basic node (leaf) or an
  intermediate node defined with a gate in a previous line. Attributes are optional and can be specified in any order.
    * `prob = PROB_VALUE`:
        * Probability associated with the node (decimal or integer between 0 and 1).
        * Typically used for basic events/attacks.
        * Required for layer 2/3 calculations involving this node if it's a basic event/attack.
    * `impact = IMPACT_VALUE`:
        * Impact value associated with the node (non-negative decimal or integer).
        * Required for layer 3 calculations involving this node.
    * `objects = [Object1, Object2, ...]`:
        * List of objects from the object graph that this node relates to.
        * Required if the node uses a `cond`.
        * Also used for layer 3 formulas.
    * `cond = (boolean_formula)`:
        * A boolean condition based on object properties that gates the node's activation.
        * The formula can use standard boolean operators (`!`, `&&`, `||`, `=>`, `==`, `!=`) with standard precedence
          and associativity rules, parentheses for grouping, and atoms being object property names (which must be
          declared in the object graph and belong to the listed `objects`).

**Example:**

```odf
[odg.attack_tree]
toplevel Attacker_breaks_in;
Attacker_breaks_in or EDLU FD;  // Intermediate node
FD or PL DD;                    // Intermediate node

// Nodes with attributes (can be basic or intermediate):
Attacker_breaks_in objects=[House,Inhabitant] impact=3.47;     // Intermediate node with attributes
EDLU prob=0.09 objects=[Door] impact=1;          // Basic node with attributes
PL prob=0.10 objects=[Lock] cond=(LP) impact=2.51;  // Basic node with attributes
DD prob=0.13 objects=[Door] cond=(DF) impact=1.81;  // Basic node with attributes
```

## 2. Fault Tree (`[odg.fault_tree]`)

Defines the fault tree structure and node attributes. The syntax is identical to the attack tree section, but defines
fault events instead of attacks.

* **`toplevel NODE_NAME;`**: (Required) Declares the root node of the fault tree.
* **`IntermediateNode GATE ChildNode1 ChildNode2 ...;`**: Defines an intermediate fault node.
* **`NodeName [attributes];`**: Defines attributes for *any* fault node (`NodeName`), identical to the attack tree. See
  the attribute descriptions in the Attack Tree section above.

**Example:**

```odf
[odg.fault_tree]
toplevel Fire_impossible_escape;
Fire_impossible_escape and FBO DGB;
DGB and LGJ DSL;

Fire_impossible_escape objects=[House] cond=(Inhab_in_House) impact=3.53;
FBO prob=0.21 objects=[House] cond=(!HS && IU) impact=1.09;
DGB objects=[Door] impact=1.67;
LGJ prob=0.70 objects=[Lock] cond=(LJ) impact=0.83;
DSL prob=0.20 objects=[Door] impact=1.31;
```

## 3. Object Graph (`[odg.object_graph]`)

Defines the objects, their relationships, and their properties.

* **`ParentObject has ChildObject1 ChildObject2 ...;`**: Defines a hierarchical relationship where `ParentObject` has
  *parts* `ChildObject1`, `ChildObject2`, etc. At least 1 child is required.
* **`ObjectName properties = [Prop1, Prop2, ...];`**: Declares the boolean properties associated with an `ObjectName`.
  These properties can be used in `cond` attributes in the attack and fault trees. An object can be defined with
  `properties` even if it's also a `ParentObject` in a `has` relationship.

Note: The object graph need not be connected. This means the object graph is a forest.

**Example:**

```odf
[odg.object_graph]
House has Door; // Relationship
Door has Lock;  // Relationship

House properties=[HS]; // Property declaration
Inhabitant properties=[IU, Inhab_in_House];
Door properties=[DF];
Lock properties=[LJ, LP];
```

## 4. Formulas (`[formulas]`)

Contains a list of ODGLog formulas to be evaluated, each ending with a semicolon.

Each formula belongs to one of the three layers (layer 1, layer 2, layer 3).

**General Syntax Elements:**

* **`NODE_NAME`**: A C-style identifier representing a node in the attack tree, fault tree, object graph, or an object
  property.
* **`PROB_VALUE`**: A decimal or integer number (typically between 0 and 1 for probabilities).
* **`TRUTH_VALUE`**: `0` (false) or `1` (true).
* **Boolean Operators:** `!` (negation), `&&` (and), `||` (or), `=>` (implies), `==` (equivalent), `!=` (not
  equivalent).
* **Configuration:** `{Prop1: TRUTH_VALUE, Prop2: TRUTH_VALUE, ...}` - Used in layer 1 and layer 2 to fix the state of
  nodes/properties.
* **Boolean Evidence:** `[Prop1: TRUTH_VALUE, Prop2: TRUTH_VALUE, ...]` - Used in layer 1 and layer 3 to fix the state
  of nodes/properties during evaluation.
* **Probability Evidence:** `[Node1=PROB_VALUE, Node2=PROB_VALUE, ...]` - Used in layer 2 to temporarily override node
  probabilities.

* **Syntax Tips:**
    * Required vs Optional: Configuration (which is always required for L1 and L2 formulas) uses `{...}`, Evidence uses
      `[...]`
    * Boolean vs Numeric: Boolean values use `:`, Probabilities use `=`

**(See the layer-specific sections below for more details on the syntax and semantics of each layer.)**

**Example:**

```odf
[formulas]
// Layer 1 Check
{LP:1, LJ:1, DF:1, PL:1, DD:1, EDLU:1, FBO:1, DSL:1, LGJ:1} FD && DGB;

// Layer 1 Compute All
{LP: 1, DF: 1} [[PL || DD]];

// Layer 2
{LP:1, DF:1} P(FD && DGB) >= 0.1 [DSL=0.9];

// Layer 3
MostRiskyA(Door);
OptimalConf(House) [HS: 0];
```

### Layer 1

Layer 1 has two types of queries that can be used in the `[formulas]` section:

1. **Check Query:** `{config} l1_formula`
    * Verifies if a boolean formula holds true under a given configuration
    * Example: `{LP: 1, LJ: 1, DF: 1, PL: 1, DD: 1, DSL: 1, LGJ: 1} FD && DGB`

2. **Compute All Query:** `{config} [[l1_formula]]`
    * Finds all minimal configurations of attack/fault nodes that satisfy a boolean formula
    * Example: `{LP: 1, DF: 1} [[PL || DD]]`

Both query types share these components:

* **Required Configuration** (`{config}`):
    * Set truth values for variables using `Name: TRUTH_VALUE` syntax
    * Must specify all required variables (error if missing)
    * For Check queries: need values for all variables in formula's BDD
    * For Compute All: need values for all object properties used in formula's BDD

* **Boolean Formula** (`l1_formula`):
    * **Atoms:**
        * Node names from attack/fault trees (representing their activation)
        * Object properties
        * The `MRS(l1_formula)` operator for minimal satisfying risk scenarios (implicitly used in Compute All queries)
    * **Boolean Operators:**
        * Negation: `!` or `\neg`
        * Conjunction: `&&` or `\land`
        * Disjunction: `||` or `\lor`
        * Implication: `=>` or `\implies`
        * Equivalence: `==` or `\equiv`
        * Non-equivalence: `!=` or `\nequiv`
    * **Parentheses:** `(...)` for grouping
    * Standard operator precedence: `!` > `==`/`!=` > `&&` > `||` > `=>`
    * **Evidence** (`[evidence]`):
        * Can be added to any boolean formula or subformula: `l1_formula [evidence]`
        * Has lowest precedence (binds to entire formula by default)
        * Can be scoped using parentheses: `otherformula && (subformula [evidence])`
        * Can be nested: `formula && (subformula [inner]) [outer]`
        * Example: `FD && (DGB [LJ:1, HS:1]) [HS:0]` - sets `HS=0` for whole formula, but `HS=1` for `DGB`

### Layer 2

Layer 2 formulas can combine multiple probability checks using boolean operators. They follow the same boolean operator
rules as Layer 1 formulas.

* **Basic Probability Check:** `P(l1_formula) <op> PROB_VALUE`
    * Calculates the probability of `l1_formula` holding true and compares it using `<op>` (`<`, `<=`, `==`, `>=`, `>`)
    * Example: `P(FD && DGB) >= 0.1`

* **Probability Evidence:**
    * Basic syntax: `[NodeName=PROB_VALUE, ...]`
    * Overrides probabilities of basic events/attacks in a formula for probability calculations

* **Complex Probability Checks:**
    * Multiple checks can be combined: `P(formula1) > 0.5 && P(formula2) < 0.3`
    * Evidence can be scoped to specific subformulas using parentheses:
      ```
      {config} (P(formula1) >= 0.5 [evidence1]) && (P(formula2) <= 0.3 [evidence2])
      ```
    * Evidence follows the same scoping and nesting rules as in Layer 1
    * Example: `{LP:1} (P(FD) >= 0.2 [PL=0.1]) && (P(DGB) < 0.3 [DSL=0.9])`
    * Example: `{LP:1, DF:1} P(FD && DGB) >= 0.1 [DSL=0.9]`

### Layer 3

Layer 3 provides various risk analysis queries for objects in the graph:

* **Risk Queries:** `QueryType(ObjectName) [evidence]`
    * **Common Elements:**
        * `ObjectName`: Name of the object to analyze
        * `[evidence]`: Optional boolean evidence to fix object property values during analysis
        * All queries require `impact` values to be defined for relevant nodes
    * **Query Types and Outputs:**
        * `MostRiskyA(Obj)`: Returns the attack node in which `Obj` participates that has the highest risk (
          probability * impact), considering the evidence.
        * `MostRiskyF(Obj)`: Same as `MostRiskyA` but for fault nodes.
        * `MaxTotalRisk(Obj)`: Returns the maximum possible total risk for `Obj`. Total risk means the sum of the risks
          of all attack and fault nodes in which `Obj` participates. Maximum refers to the maximum total risk value that
          can be achieved by any configuration of the object properties.
        * `MinTotalRisk(Obj)`: Same as `MaxTotalRisk` but returns the minimum possible total risk that can be achieved
          by any configuration of the object properties.
        * `OptimalConf(Obj)`: Returns the object property configuration(s) that minimize total risk, i.e., the one that
          results in the same risk as `MinTotalRisk(Obj)`.

# Development & Testing

* **Dependencies:** Install development dependencies with `uv sync --all-groups`.
* **Testing:** Run tests using `pytest`:
  ```bash
  $ pytest tests/
  ```
* **Code Structure:**
    * `odf/parser/`: Lark grammar and parser.
    * `odf/transformers/`: Converts parse trees to internal models.
    * `odf/models/`: Internal data structures (DisruptionTree, ObjectGraph).
    * `odf/checker/`: Logic for evaluating ODGLog formulas (layers 1, 2, 3).
    * `odf/core/`: Core types and constants.
    * `odf/utils/`: Helper functions (logging, formatting, BDD traversal).
    * `tests/`: Pytest tests mirroring the package structure.

# References

[1] S. M. Nicoletti, E. M. Hahn, M. Fumagalli, G. Guizzardi, and M. Stoelinga, “DODGE: Ontology-Aware Risk Assessment
via Object-Oriented Disruption Graphs,” Dec. 18, 2024, arXiv: arXiv:2412.13964. doi: 10.48550/arXiv.2412.13964.
