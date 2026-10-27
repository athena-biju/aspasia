# ASPASIA — Policy-as-Code Demonstrators

ASPASIA is an **exploratory financial-policy and transaction-evaluation project**. It investigates how explicit rules, decision traces and scenario testing can make financial controls easier to inspect. This public repository contains prototypes and design material, **not a validated production compliance product**.

## Browse the actual project

| Directory | Public materials | Status / boundary |
| --- | --- | --- |
| [`aspasia-pilot/`](./aspasia-pilot/) | Streamlit demonstration (`app.py`), FastAPI service (`api_server.py`), illustrative transactions and a stress-test script | Source is present; no claim of independently verified production performance or regulatory compliance |
| [`aspasia-engine/`](./aspasia-engine/) | Node package manifest, Dockerfile and sample JSON transactions | **Scaffold / design material** in this public snapshot: referenced `src/`, `dist/` and `policies/` directories are not present, so the documented Node service cannot be run from this directory alone |
| [`aspasia-site/`](./aspasia-site/) | Static HTML presentation | Project-facing presentation, not proof of deployed integrations |

## Research questions

- Can proposed transaction policies be encoded as inspectable predicates rather than opaque decisions?
- How can a user inspect which inputs and conditions produced an evaluation result?
- How do rule conflicts, thresholds and simulated stress cases affect the result?
- What additional legal, security, integration and governance controls would be needed before an institution could consider a pilot?

## Running the available Python demonstration

See [`aspasia-pilot/README.md`](./aspasia-pilot/README.md) for dependency installation and the actual Streamlit and API entry points. The Python prototype is separate from the incomplete Node scaffold.

## Limitations

The example rules and transactions are illustrative; they are **not legal interpretations of MiCA, Basel III or FATF requirements**. No claim is made here that the demonstrator has been deployed into a regulated institution, independently audited, proven tamper-proof, or validated for production use. Benchmarks, where presented, require reproduction in a stated environment.

**Research focus:** financial controls, regulatory interpretation, model governance, decision traceability and operational risk.