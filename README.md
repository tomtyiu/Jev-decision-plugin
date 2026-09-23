# Jev-decision

A Codex plugin and marketplace package for building AI-powered software with TypeSafe System One and Jev.

The plugin turns natural language and application state into small, typed, calibrated judgments that code can compose. It supports patterns such as routing, ranking, extraction, verification, scoring, guardrails, gating, and interactive agent decisions.

## Source of truth

The root skill is the canonical skill definition:

- `skills/jev-decision/SKILL.md`

The marketplace package mirrors that file at:

- `plugins/jev-decision/skills/jev-decision/SKILL.md`

CI verifies that both copies stay identical.

## Included

- `.agents/plugins/marketplace.json` — Codex marketplace catalog.
- `.codex-plugin/plugin.json` — standalone plugin manifest.
- `skills/jev-decision/SKILL.md` — canonical TypeSafe skill.
- `plugins/jev-decision/` — installable marketplace copy.
- `scripts/jev_decide.py` — dependency-free Python wrapper for TypeSafe's System One HTTP API.
- `examples/` — routing and guardrail-gating request examples.
- `tests/` — offline tests for request compilation and gating behavior.
- `.github/workflows/test-plugin.yml` — CI validation and sync checks.

## Requirements

- Python 3.10+
- `TYPESAFE_API_KEY` for live API calls

No third-party Python package is required by the wrapper.

## Test locally

```bash
python -m unittest discover -s plugins/jev-decision/tests -v
python plugins/jev-decision/scripts/jev_decide.py --input plugins/jev-decision/examples/router.json --dry-run
```

## Marketplace

Marketplace name:

```text
jev-decision-marketplace
```

Plugin name:

```text
jev-decision
```

The marketplace entry points to:

```text
./plugins/jev-decision
```

## TypeSafe documentation

The skill intentionally treats the live TypeSafe documentation as the source of truth.

Start with:

- https://docs.typesafe.ai/llms.txt
- https://docs.typesafe.ai/concepts/system-one.md
- https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md
- https://docs.typesafe.ai/api.md


#Thanks
Thanks to Typesafe.ai

# Contribution

Please provide create **new issue** for any bugs and suggestions with the jev plugin.
