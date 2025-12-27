# ASPASIA: Protocol-Embedded Policy Engine

**A Deterministic "Policy-as-Code" Engine for Ex-Ante Transaction Screening**

ASPASIA is a lightweight, strict-liability compliance engine designed to enforce regulatory obligations (such as MiCA and FATF) directly within transaction flows. Unlike stochastic AI agents, ASPASIA utilizes a recursive **Abstract Syntax Tree (AST)** to compile regulatory text into machine-executable logic, ensuring 100% determinism and auditability for financial institutions.

**[Live Demo](https://aspasia-pilot.streamlit.app)**

---

## Architectural Highlights

This repository demonstrates the transition from manual "institutional sludge" to automated **Machine-Executable Regulation**. Key architectural decisions include:

### 1. Deterministic AST vs. Stochastic Agents
Financial regulation requires certainty, not probability. While LLM-based agents are powerful, they are prone to hallucination.
* **The Architecture:** ASPASIA implements a recursive `CompositeCondition` class. This constructs a traverseable Abstract Syntax Tree (AST) where complex rules are decomposed into atomic boolean predicates.
* **The Advantage:** This ensures that every decision is mathematically provable. The engine generates a JSON `trace` for every evaluation, providing a cryptographic-grade audit trail without stochastic variability.

### 2. Explicit Conflict Resolution Strategy
In production environments, regulatory rules often collide (e.g., a "VIP Allow" rule vs. a "Sanctions Block" rule).
* **The Logic:** The `PolicyEngine` enforces a strict precedence hierarchy defined in the `evaluate` method.
* **The Algorithm:** Conflicts are resolved via a tuple sort: `(ActionSeverity, RulePriority)`.
    * **Action Severity:** A `BLOCK` (Rank 2) strictly overrides a `FLAG` (Rank 1), regardless of priority. This guarantees that safety-critical "Strict Liability" rules cannot be bypassed by lower-severity business logic.
    * **Rule Priority:** Within the same severity tier, higher integer priority rules take precedence.

---

## Repository Structure

* **`app.py`** (formerly `aspasia_ui.py`):
    The **Pilot Core**. A Streamlit-based simulator that allows compliance officers to edit YAML rules, simulate transactions, and visualize the decision tree and AST execution trace in real-time.

* **`main.py`**:
    The **Intelligence Layer**. A headless FastAPI microservice designed for production integration. It exposes REST endpoints (`POST /enforce`) to accept transaction payloads and return millisecond-latency decisions.

* **`stress_test.py`**:
    A performance benchmarking script. It generates synthetic transaction traffic to measure system throughput and latency, validating the engine's capability for "Ex-Ante" (pre-settlement) enforcement.

---

## Getting Started

### Prerequisites
* Python 3.9+
* pip

### 1. Installation
Clone the repository and install the required dependencies:

```bash
pip install streamlit fastapi uvicorn pyyaml requests
