# ASPASIA Pilot — Inspectable Transaction-Rule Simulation

This directory contains **Python prototype source** for evaluating illustrative financial transaction conditions and inspecting rule decisions. It is a demonstrator for research and pilot discussions, not a production service or a substitute for legal advice.

## Files and entry points

- `app.py`: Streamlit interface for experimenting with rules and sample transaction inputs.
- `api_server.py`: FastAPI application; the source exposes `/`, `/stats`, and `POST /enforce` routes.
- `stress_test.py`: a requests-based traffic generator for local experimentation; results should not be interpreted as proven production throughput.
- `demo.html`: a static demonstration asset.
- `requirements.txt`: dependencies needed for the visible demonstration and API scripts.

## Run locally (development only)

From `aspasia-pilot/`:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

To run the API in another terminal:

```bash
uvicorn api_server:app --reload
```

Review the source and generated traces before relying on any results. These commands are based on the checked-in entry points; execution and deployment were **not independently validated** during this documentation clean-up.

## What this prototype aims to demonstrate

1. Represent illustrative conditions as explicit, inspectable rule logic.
2. Evaluate sample transactions against those conditions.
3. Report the result and a decision trace suitable for human review.
4. Explore how changing rules or scenario inputs changes the outcome.

## Important boundaries

- Deterministic rule evaluation for a given input is **not** proof that the policy itself is legally correct, complete, or secure.
- A JSON decision trace is **not** a cryptographic integrity guarantee unless its provenance and tamper resistance are separately established.
- The presence of a `stress_test.py` script is **not** a verified latency, availability, security or throughput claim.
- Regulatory references are illustrative and require qualified legal validation before use in a real workflow.

Repository overview: [ASPASIA project root](../README.md).