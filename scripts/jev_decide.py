#!/usr/bin/env python3
"""Compile agent-friendly typed decisions into TypeSafe Jev System One requests.

Input is JSON from --input FILE or stdin. By default this calls TypeSafe's
/v1/systemone endpoint and emits normalized JSON. --dry-run prints the compiled
TypeSafe request and does not require an API key.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
ALLOWED_UNCERTAIN = {"review", "clarify", "fallback"}


class InputError(ValueError):
    pass


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{field} must be a number")
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise InputError(f"{field} must be between 0 and 1")
    return value


def compile_request(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InputError("top-level input must be an object")
    if "state" not in payload:
        raise InputError("state is required")
    decisions = payload.get("decisions")
    if not isinstance(decisions, dict) or not decisions:
        raise InputError("decisions must be a non-empty object")

    questions: dict[str, Any] = {}
    for decision_id, spec in decisions.items():
        if not isinstance(decision_id, str) or not decision_id:
            raise InputError("decision ids must be non-empty strings")
        if not isinstance(spec, dict):
            raise InputError(f"decision {decision_id!r} must be an object")
        kind = spec.get("kind")
        question = spec.get("question")
        if not isinstance(question, (str, dict, list)):
            raise InputError(f"{decision_id}.question must be a string, object, or array")

        if kind == "choice":
            options = spec.get("options")
            if not isinstance(options, dict) or len(options) < 2:
                raise InputError(f"{decision_id}.options must contain at least two choices")
            if len(options) > 255:
                raise InputError(f"{decision_id}.options may contain at most 255 choices")
            questions[decision_id] = {
                "type": "choice",
                "instructions": question,
                "criteria": options,
            }
        elif kind == "score":
            levels = spec.get("levels")
            if not isinstance(levels, list) or not 2 <= len(levels) <= 10:
                raise InputError(f"{decision_id}.levels must contain 2 to 10 ordered levels")
            questions[decision_id] = {
                "type": "score",
                "instructions": question,
                "criteria": levels,
            }
        elif kind in {"probability", "noul"}:
            q: dict[str, Any] = {"type": "noul", "instructions": question}
            criteria = spec.get("criteria")
            if criteria is not None:
                if not isinstance(criteria, dict) or set(criteria) - {"true", "false"}:
                    raise InputError(f"{decision_id}.criteria may only contain true/false")
                q["criteria"] = criteria
            questions[decision_id] = q
        else:
            raise InputError(
                f"{decision_id}.kind must be one of: choice, score, probability"
            )

    model = payload.get("model", "jev-latest")
    if not isinstance(model, str) or not model:
        raise InputError("model must be a non-empty string")

    return {"state": payload["state"], "model": model, "questions": questions}


def validate_policy(payload: dict[str, Any]) -> dict[str, Any]:
    decisions = payload["decisions"]
    policy = payload.get("policy", {})
    if not isinstance(policy, dict):
        raise InputError("policy must be an object")

    normalized: dict[str, Any] = {}
    for decision_id, rule in policy.items():
        if decision_id not in decisions:
            raise InputError(f"policy references unknown decision {decision_id!r}")
        if not isinstance(rule, dict):
            raise InputError(f"policy.{decision_id} must be an object")
        on_uncertain = rule.get("on_uncertain", "review")
        if on_uncertain not in ALLOWED_UNCERTAIN:
            raise InputError(
                f"policy.{decision_id}.on_uncertain must be review, clarify, or fallback"
            )
        kind = decisions[decision_id]["kind"]
        item: dict[str, Any] = {"on_uncertain": on_uncertain}
        if kind in {"probability", "noul"}:
            has_yes = "yes_at" in rule
            has_no = "no_at" in rule
            if has_yes != has_no:
                raise InputError(
                    f"policy.{decision_id} must set both yes_at and no_at, or neither"
                )
            if has_yes:
                yes_at = _number(rule["yes_at"], f"policy.{decision_id}.yes_at")
                no_at = _number(rule["no_at"], f"policy.{decision_id}.no_at")
                if no_at >= yes_at:
                    raise InputError(
                        f"policy.{decision_id}.no_at must be lower than yes_at"
                    )
                item.update({"yes_at": yes_at, "no_at": no_at})
        else:
            if "min_confidence" in rule:
                item["min_confidence"] = _number(
                    rule["min_confidence"], f"policy.{decision_id}.min_confidence"
                )
        normalized[decision_id] = item
    return normalized


def call_typesafe(request_body: dict[str, Any], api_key: str, timeout: float) -> dict[str, Any]:
    body = json.dumps(request_body).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "jev-decision/0.1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"TypeSafe API HTTP {exc.code}: {detail[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"TypeSafe API request failed: {exc.reason}") from exc

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("TypeSafe API returned non-JSON data") from exc
    if not isinstance(result, dict):
        raise RuntimeError("TypeSafe API returned an unexpected response shape")
    return result


def _gate_choice_or_score(answer: dict[str, Any], rule: dict[str, Any] | None) -> tuple[str, str | None]:
    if not rule or "min_confidence" not in rule:
        return "ungated", None
    confidence = answer.get("confidence")
    if not isinstance(confidence, (int, float)):
        return "review", rule.get("on_uncertain", "review")
    if float(confidence) >= rule["min_confidence"]:
        return "accept", None
    return "review", rule.get("on_uncertain", "review")


def _gate_probability(value: float, rule: dict[str, Any] | None) -> tuple[str, bool | None, str | None]:
    if not rule or "yes_at" not in rule:
        return "ungated", None, None
    if value >= rule["yes_at"]:
        return "accept", True, None
    if value <= rule["no_at"]:
        return "accept", False, None
    return "review", None, rule.get("on_uncertain", "review")


def normalize_response(
    payload: dict[str, Any], response: dict[str, Any], policy: dict[str, Any]
) -> dict[str, Any]:
    answers = response.get("answers")
    if not isinstance(answers, dict):
        raise RuntimeError("TypeSafe API response is missing answers")

    out: dict[str, Any] = {
        "model": response.get("model", payload.get("model", "jev-latest")),
        "decisions": {},
    }
    if "usage" in response:
        out["usage"] = response["usage"]

    for decision_id, spec in payload["decisions"].items():
        answer = answers.get(decision_id)
        if not isinstance(answer, dict):
            raise RuntimeError(f"TypeSafe API response is missing answer {decision_id!r}")
        kind = spec["kind"]
        rule = policy.get(decision_id)

        if kind == "choice":
            status, uncertain_action = _gate_choice_or_score(answer, rule)
            item = {
                "kind": "choice",
                "value": answer.get("choice"),
                "probabilities": answer.get("probabilities"),
                "confidence": answer.get("confidence"),
                "status": status,
            }
        elif kind == "score":
            status, uncertain_action = _gate_choice_or_score(answer, rule)
            item = {
                "kind": "score",
                "value": answer.get("score"),
                "probabilities": answer.get("probabilities"),
                "confidence": answer.get("confidence"),
                "legend": answer.get("legend"),
                "status": status,
            }
        else:
            raw = answer.get("noul")
            if not isinstance(raw, (int, float)):
                raise RuntimeError(f"Noul answer {decision_id!r} has no numeric noul value")
            probability_yes = float(raw)
            status, bool_value, uncertain_action = _gate_probability(probability_yes, rule)
            item = {
                "kind": "probability",
                "probability_yes": probability_yes,
                "value": bool_value,
                "status": status,
            }

        if uncertain_action:
            item["on_uncertain"] = uncertain_action
        out["decisions"][decision_id] = item
    return out


def load_payload(path: str | None) -> dict[str, Any]:
    if path:
        text = Path(path).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise InputError("top-level JSON must be an object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="JSON input file; omit to read stdin")
    parser.add_argument("--dry-run", action="store_true", help="compile only; do not call TypeSafe")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    args = parser.parse_args()

    try:
        payload = load_payload(args.input)
        request_body = compile_request(payload)
        policy = validate_policy(payload)
        if args.dry_run:
            print(json.dumps({"request": request_body, "policy": policy}, indent=2, sort_keys=True))
            return 0

        api_key = os.environ.get("TYPESAFE_API_KEY")
        if not api_key:
            raise InputError("TYPESAFE_API_KEY is required unless --dry-run is used")
        response = call_typesafe(request_body, api_key=api_key, timeout=args.timeout)
        normalized = normalize_response(payload, response, policy)
        print(json.dumps(normalized, indent=2, sort_keys=True))
        return 0
    except (InputError, RuntimeError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
