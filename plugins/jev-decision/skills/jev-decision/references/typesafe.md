# TypeSafe Jev reference

Primary documentation:

- Introduction: https://docs.typesafe.ai/introduction
- Quick start: https://docs.typesafe.ai/introduction/quickstart
- Choice: https://docs.typesafe.ai/primitives/choice
- Score: https://docs.typesafe.ai/primitives/score
- Noul: https://docs.typesafe.ai/primitives/noul
- Confidence: https://docs.typesafe.ai/confidence
- Patterns: https://docs.typesafe.ai/patterns
- Agent skill: https://docs.typesafe.ai/agent-skill

## API mapping

Endpoint: `POST https://api.typesafe.ai/v1/systemone`

Authentication: `Authorization: Bearer $TYPESAFE_API_KEY`

Top-level request fields:

- `state`: content or structured state to evaluate;
- `model`: normally `jev-latest` unless the application pins a version;
- `questions`: map of question IDs to typed question objects.

Question mapping used by this plugin:

- normalized `kind: choice` -> TypeSafe `type: choice`, `instructions`, `criteria` map;
- normalized `kind: score` -> TypeSafe `type: score`, `instructions`, ordered `criteria` array;
- normalized `kind: probability` -> TypeSafe `type: noul`, `instructions`, optional `criteria.true` / `criteria.false`.

Choice and Score return full probability distributions plus confidence. Noul returns a single 0-1 probability that the proposition is true and has no separate confidence field.

Questions in one request are evaluated independently against the same state. Prefer atomic questions and compose them in code.
