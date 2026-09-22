---
name: jev-decision
description: Turn noisy state into a small typed, calibrated decision using TypeSafe Jev: a fixed choice, an ordered score, or a yes/no probability. Use for high-volume agent routing, classification, scoring, extraction validation, guardrails, and gates when deterministic code is too brittle but open-ended LLM generation is unnecessary. Do not use for long-form generation, extended multi-step reasoning, or decisions that can be made reliably with ordinary deterministic code.
---

# Jev Decision

Use TypeSafe Jev as a narrow decision component inside a larger agent. The goal is not to generate prose. The goal is to convert noisy state into a typed value plus calibrated uncertainty that code can consume.

## Core contract

Choose exactly one primitive for each atomic judgment:

- **Choice**: one value from a fixed, unordered set. Return the selected choice, the probability distribution, and confidence.
- **Score**: a position on an ordered rubric. Return the numeric score, the probability distribution across rubric levels, and confidence.
- **Probability**: a yes/no proposition. Implement this with TypeSafe **Noul** and return the probability that the answer is yes.

Prefer several atomic questions in one call over one overloaded question. Combine the resulting dimensions in code.

## When to use it

Good fits include:

- route a request to one handler or tool;
- classify an event into a known taxonomy;
- score severity, quality, priority, relevance, or risk against explicit ordered levels;
- verify or gate an extraction candidate;
- detect whether a condition is present before an agent acts;
- add a fuzzy guardrail around an otherwise deterministic workflow;
- rank candidates using probabilities when the decision is naturally yes/no per candidate.

Use a deterministic `if` when the boundary is explicit and stable. Use a stronger reasoning model when the task requires extended reasoning, synthesis, planning, or open-ended generation.

## Primitive selection

Use **Choice** when options are categories, routes, handlers, labels, tools, or known entities. Write option descriptions so neighboring options are clearly separated. Add `other` or `none` when the set is not exhaustive.

Use **Score** when the answer lies on an ordered spectrum. Define 2-10 concrete levels from low to high. Each level should describe observable evidence rather than vague adjectives.

Use **Probability / Noul** when the code needs the probability that one proposition is true. Phrase the proposition so a larger number always means “more likely yes.” Split compound propositions into separate questions and combine them in code.

## Atomic-question rule

Each question should be answerable as one quick judgment from the supplied state. If a question asks about independent dimensions, decompose it.

Bad: `Is this request urgent, abusive, and eligible for a refund?`

Better: ask three independent decisions, then combine them in application logic.

## Agent workflow

1. Identify the smallest fuzzy judgment the surrounding code needs.
2. Select Choice, Score, or Probability/Noul.
3. Define the answer space or yes/no boundary explicitly.
4. Send the noisy input as `state` and all independent questions together.
5. Preserve the raw probabilities and confidence in the returned data.
6. Apply thresholds in code according to the cost of a wrong action.
7. Route uncertain cases to review, clarification, or a stronger fallback rather than inventing certainty.

## Gating and safety

Confidence is a routing signal, not authorization. A high-confidence model output must not bypass deterministic access control, authentication, approval requirements, policy enforcement, or other hard safety checks.

For Choice and Score, gate on returned `confidence` only when the application supplies an explicit threshold. For Probability/Noul, use explicit `yes_at` and `no_at` thresholds. Values between them are uncertain and should follow the configured review/clarify/fallback path.

Do not claim universal threshold values. Thresholds depend on error cost and must be calibrated on representative data. For consequential actions, prefer stricter thresholds plus independent deterministic checks or explicit user approval.

## Extraction guidance

Jev is not a free-form text extractor. Use it for typed extraction when the candidate values are known, or to validate/gate a candidate produced by another parser or model. If the field is arbitrary open-ended text, use a structured extraction mechanism first, then use Jev to validate the result if useful.

## Normalized request format

The included `scripts/jev_decide.py` accepts this agent-friendly shape:

```json
{
  "state": "noisy input or a JSON-compatible object",
  "model": "jev-latest",
  "decisions": {
    "route": {
      "kind": "choice",
      "question": "Which handler should receive this request?",
      "options": {
        "billing": "Payments, invoices, refunds, or subscription charges",
        "technical": "Product bugs, failures, or integration problems",
        "other": "Does not fit the listed handlers"
      }
    },
    "severity": {
      "kind": "score",
      "question": "How severe is the operational impact?",
      "levels": [
        "No meaningful impact",
        "Minor degradation with workaround",
        "Major degradation or blocked workflow",
        "Critical outage or widespread failure"
      ]
    },
    "needs_review": {
      "kind": "probability",
      "question": "Does this case require human review?"
    }
  },
  "policy": {
    "route": {"min_confidence": 0.7, "on_uncertain": "review"},
    "severity": {"min_confidence": 0.7, "on_uncertain": "review"},
    "needs_review": {"yes_at": 0.85, "no_at": 0.15, "on_uncertain": "review"}
  }
}
```

Run with `TYPESAFE_API_KEY` set:

```bash
python scripts/jev_decide.py --input request.json
```

To inspect the exact TypeSafe request without making a network call:

```bash
python scripts/jev_decide.py --input request.json --dry-run
```

## Output expectations

Return JSON-like typed data to the caller, not narrative prose. Preserve:

- the chosen value or score;
- the complete probability distribution when TypeSafe provides one;
- confidence for Choice and Score;
- the raw yes probability for Probability/Noul;
- the gate status (`accept`, `review`, or `ungated`);
- the model identifier.

When the result is uncertain, say so in the typed status instead of silently forcing a decision.

## References

Read `references/typesafe.md` for the TypeSafe API mapping and primary documentation links.
