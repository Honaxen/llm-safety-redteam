"""
Input/output safety filter, designed to sit in front of an existing
LLM API (e.g. ml-api-service's /generate endpoint) without changing
how that API works internally.

Two checkpoints:
  - check_input()  -- runs BEFORE the prompt reaches the model.
                      Blocks obvious jailbreak/injection patterns cheaply,
                      before spending any inference time on them.
  - check_output() -- runs AFTER the model responds, BEFORE the response
                      reaches the user. Catches cases where the input
                      filter missed something but the model complied
                      anyway, or leaked something it shouldn't have.

This is intentionally a thin, fast, rule-based layer -- not a replacement
for judge/safety_judge.py's LLM-based judgment. The filter's job is to
catch cheap, high-confidence cases in production in milliseconds; the
judge's job is thorough offline evaluation. Different latency budgets,
different tools.

Usage (standalone):
    from safety_filter import SafetyFilter

    filt = SafetyFilter()
    allowed, reason = filt.check_input(user_prompt)
    if not allowed:
        return {"error": reason}

    response = call_model(user_prompt)

    allowed, reason = filt.check_output(response)
    if not allowed:
        return {"error": reason}
"""

import re
from dataclasses import dataclass


@dataclass
class FilterResult:
    allowed: bool
    reason: str
    matched_pattern: str | None = None


# Patterns that indicate an attempt to override instructions or extract
# system-level information -- checked against the INCOMING prompt.
INPUT_BLOCK_PATTERNS = [
    (r"\bignore (all |the )?(previous|prior|above) instructions\b", "instruction override attempt"),
    (r"\bdeveloper mode\b", "known jailbreak framing"),
    (r"\bsystem override\b", "instruction override attempt"),
    (r"\breveal your system prompt\b", "system prompt extraction attempt"),
    (r"\brepeat (the exact text of )?your (system )?(prompt|instructions)\b", "system prompt extraction attempt"),
    (r"\bno restrictions\b.*\bmust answer\b", "known jailbreak framing"),
    (r"<\s*system\s*>", "injected fake system tag"),
]

# Patterns that indicate the MODEL'S RESPONSE leaked something or complied
# with a known attack -- checked against the OUTGOING response.
OUTPUT_BLOCK_PATTERNS = [
    (r"\bdeveloper mode enabled\b", "model complied with jailbreak framing"),
    (r"\bpwned\b", "model complied with injected instruction"),
    (r"\b(my|the) system prompt is\b", "system prompt leakage"),
    (r"\bpassword is\b", "credential leakage"),
    (r"\bapi key is\b", "credential leakage"),
]


class SafetyFilter:
    def __init__(self, input_patterns=None, output_patterns=None):
        self.input_patterns = input_patterns or INPUT_BLOCK_PATTERNS
        self.output_patterns = output_patterns or OUTPUT_BLOCK_PATTERNS

    def check_input(self, prompt: str) -> FilterResult:
        text = prompt.lower()
        for pattern, reason in self.input_patterns:
            if re.search(pattern, text):
                return FilterResult(allowed=False, reason=reason, matched_pattern=pattern)
        return FilterResult(allowed=True, reason="no match")

    def check_output(self, response_text: str) -> FilterResult:
        text = response_text.lower()
        for pattern, reason in self.output_patterns:
            if re.search(pattern, text):
                return FilterResult(allowed=False, reason=reason, matched_pattern=pattern)
        return FilterResult(allowed=True, reason="no match")
