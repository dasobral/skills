#!/usr/bin/env python3
"""Derive SP 800-90B RCT and APT cutoffs from declared assumptions."""

from __future__ import annotations

import json
import math
import sys

from contract_utils import reject_credentials, validate_contract


FORMULA_VERSION = "NIST.SP.800-90B@2018:4.4.1-4.4.2/v1"


def _binomial_tail(window: int, cutoff: int, probability: float) -> float:
    terms = []
    for count in range(cutoff, window + 1):
        log_probability = (
            math.lgamma(window + 1)
            - math.lgamma(count + 1)
            - math.lgamma(window - count + 1)
            + count * math.log(probability)
            + (window - count) * math.log1p(-probability)
        )
        terms.append(math.exp(log_probability))
    return math.fsum(terms)


def derive(request: dict[str, object]) -> dict[str, object]:
    alpha = float(request["alpha"])
    alphabet_size = int(request["alphabet_size"])
    entropy = float(request["claimed_min_entropy_bits_per_sample"])
    if not 0 < alpha < 1:
        raise ValueError("alpha must satisfy 0 < alpha < 1")
    if alphabet_size < 2:
        raise ValueError("alphabet_size must be at least 2")
    if not 0 < entropy <= math.log2(alphabet_size):
        raise ValueError("claimed entropy must be within the alphabet bound")
    window = 1024 if alphabet_size == 2 else 512
    requested_window = request.get("adaptive_proportion_window")
    if requested_window is not None and int(requested_window) != window:
        raise ValueError(
            f"adaptive_proportion_window must be {window} for alphabet_size "
            f"{alphabet_size}"
        )
    probability = 2.0 ** (-entropy)
    repetition = 1 + math.ceil(-math.log2(alpha) / entropy)
    adaptive = None
    for cutoff in range(max(1, math.ceil(window * probability)), window + 1):
        if _binomial_tail(window, cutoff, probability) <= alpha:
            adaptive = cutoff
            break
    if adaptive is None:
        raise ValueError("no APT cutoff satisfies the declared parameters")
    result = {
        "formula_version": FORMULA_VERSION,
        "alphabet_size": alphabet_size,
        "claimed_min_entropy_bits_per_sample": entropy,
        "repetition_count_cutoff": repetition,
        "adaptive_proportion_window": window,
        "adaptive_proportion_cutoff": adaptive,
        "alpha": alpha,
    }
    validate_contract(result, "health-test-parameters.schema.json")
    return result


def main() -> None:
    try:
        request = json.load(sys.stdin)
        reject_credentials(request)
        result = derive(request)
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
