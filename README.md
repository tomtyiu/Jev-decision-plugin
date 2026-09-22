# Jev-decision

A Codex plugin that turns messy input into small, typed, calibrated decisions using TypeSafe Jev.

It is designed for the high-volume judgments inside agents that are too fuzzy for a brittle handwritten `if`, but too small to justify open-ended frontier-model generation: routing, classification, scoring, extraction validation, guardrails, and gates.

## Included

- `.codex-plugin/plugin.json` — Codex plugin manifest.
- `skills/jev-decision/SKILL.md` — agent skill and decision architecture.
- `scripts/jev_decide.py` — dependency-free Python wrapper for TypeSafe's System One HTTP API.
- `examples/` — routing and guardrail-gating request examples.
- `tests/` — offline tests for request compilation and gating behavior.

## Requirements

- Python 3.10+
- `TYPESAFE_API_KEY` for live API calls

No third-party Python package is required by the wrapper.

## Test locally

```bash
python -m unittest discover -s tests -v
python scripts/jev_decide.py --input examples/router.json --dry-run
```

## Install as a local Codex plugin

Place the plugin folder at a location Codex can load, such as a personal plugin directory, then add it to the appropriate Codex plugin marketplace configuration if needed by your environment.

The canonical plugin folder name is `jev-decision`; the user-facing display name is `Jev-decision`.

## TypeSafe references

- https://docs.typesafe.ai/introduction
- https://docs.typesafe.ai/introduction/quickstart
- https://docs.typesafe.ai/agent-skill
