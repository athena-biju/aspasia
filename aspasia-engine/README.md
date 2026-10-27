# ASPASIA / MAAT Node Engine — Public Scaffold

**Status: incomplete public scaffold, not a runnable release.**

This folder currently contains a `package.json`, `Dockerfile`, and illustrative transactions under `demo/`. Earlier documentation described a complete policy compiler, API and container deployment, but the `src/`, `dist/` and `policies/` directories referenced by those descriptions are **not present in this public snapshot**.

## What can be inspected

- `package.json` declares the intended Node entry points (`dist/index.js` and `dist/api.js`).
- `Dockerfile` describes an intended container build that copies `dist/` and `policies/`.
- `demo/` contains sample JSON transactions for conceptual evaluation.

## What is not currently supported here

Running `npm start`, `npm run api`, or building the Dockerfile from this public folder alone is not expected to work without the missing sources and assets. The included design ideas should not be interpreted as implemented or tested production features.

For **available Python demonstration source**, go to [`../aspasia-pilot/`](../aspasia-pilot/) and its [README](../aspasia-pilot/README.md).

## Concept under exploration

The broader architecture explores an explicit rule compiler, state-aware limits, controlled conflict handling, and human-readable evaluation evidence. Whether such components meet a real institution's legal, operational, latency and security needs remains an empirical question for a bounded pilot.