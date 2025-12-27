# ASPASIA Compliance Engine v1.0

Welcome to the **ASPASIA Compliance Engine**. This repository contains a complete,
working prototype of a **policy‑as‑code engine** designed to enforce
financial regulations (MiCA, Basel III, FATF, etc.) across payment networks.
It includes a local command‑line interface, a REST API, and containerised
deployment to satisfy diverse stakeholder requirements.

## High‑Level Overview

The engine implements the full governance loop described in the project’s
research notes:

1. **Clause → Rule**: Regulatory clauses are encoded into JSON files.  A
   compiler reads these files and produces executable predicates rather than
   merely recording citations.  This policy‑as‑code approach borrows from the
   Open Policy Agent (OPA) pattern【737693085414947†L5-L13】 and ensures each
   obligation is deterministic, auditable and replayable.
2. **Rule → State‑Aware Limit**:  Each rule defines a transaction limit as
   a *function* of system state (e.g. network stress, institutional
   friction), not a fixed constant.  This turns governance into control
   theory: variables such as “sludge” (delay, data gaps, KYC gaps) modulate
   the permissible amount【737693085414947†L120-L133】.
3. **State‑Aware Limit → Network Throttle**:  A network monitor computes
   I/O centrality for each node and adjusts limits dynamically.  High‑risk
   nodes receive aggressive brakes during stress events, echoing the
   Hulten/Domar logic that prioritises stability over throughput【737693085414947†L41-L64】.
4. **Network Throttle → Natural‑Language Audit**:  Every evaluation
   generates a human‑readable audit log.  The log records rule triggers,
   state variables, and final decisions, fulfilling NIST AI‑RMF requirements
   for explainability and model cards【737693085414947†L120-L133】.

## What’s Included

This repository contains:

| Path                     | Purpose                                                |
|--------------------------|--------------------------------------------------------|
| `src/`                   | Source code for the engine (ESM/Node).                |
| `dist/`                  | Compiled JavaScript used by the runtime scripts.       |
| `policies/`              | JSON specifications of MiCA/Basel III/FATF clauses.    |
| `demo/`                  | Sample transactions used in the CLI demonstration.     |
| `package.json`           | Project metadata and NPM scripts.                      |
| `Dockerfile`             | Build instructions for containerising the engine.       |
| `README.md`              | This documentation.                                    |

The compiled files under `dist/` are functionally identical to the source in
`src/`.  You can view the source for educational purposes; the engine does not
require a TypeScript build step, making it easy to run anywhere.

## Quick Start

### Local CLI

To evaluate the included demo transactions locally:

```bash
git clone <this repo>
cd maat-engine
npm install
npm start
```

You should see a summary of compliance decisions for each sample transaction.

### REST API

If you want to expose the engine over HTTP:

```bash
npm run api
```

This will start an Express server on port 3000.  Send a `POST` request to
`/evaluate` with a JSON payload matching the transaction schema.  The
response will include the decision, friction score, violated rule IDs and
a natural‑language audit log.

### Docker

For containerised deployments, build and run the image:

```bash
docker build -t maat-engine .
docker run -it --rm -p 3000:3000 maat-engine
```

You can then call the API as described above.

## Architecture Summary

The core of ASPASIA consists of three modules:

1. **Policy Compiler** (`src/policyCompiler.js`) – Parses YAML files into
   executable rule objects.  Each rule encapsulates its own evaluation logic
   and returns a boolean, a friction score and an explanation.  The compiler
   supports multiple regulators and can be extended with new clause types.
2. **Network Throttle** (`src/networkThrottle.js`) – Computes dynamic
   transaction limits based on I/O centrality and system stress.  It uses
   the Hulten formula to assess the macro importance of a node and applies
   tighter limits when necessary【737693085414947†L41-L64】.
3. **Compliance Engine** (`src/complianceEngine.js`) – Orchestrates the
   governance loop.  It loads the compiled rules, applies them to each
   transaction, consults the throttle for dynamic limits, and produces a
   structured decision accompanied by a natural‑language audit trail.

We believe this repository demonstrates a pragmatic implementation of
protocol‑embedded policy.  It takes regulatory text and turns it into
actionable code that monitors transactions in real time while providing
transparent feedback – a cornerstone of trust for the financial industry.

## Sample Policies & Transactions

The `policies/` folder contains simplified examples of MiCA, FATF and Basel
clauses encoded as JSON.  They specify maximum transfer amounts, required
metadata fields and variable risk weights.  You can modify or extend these
JSON files to experiment with additional rules.

The `demo/` folder includes three JSON transactions that illustrate a
compliant transfer, a high‑value violation and an unhosted wallet scenario.
Run `npm start` to see how the engine reacts to each case.

## Contributing

Feedback and contributions are welcome.  Please file issues or submit pull
requests to refine the rule language, throttle logic or audit format.  We
also encourage forks for institution‑specific implementations.
