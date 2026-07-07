# Architecture

## Overview

This project runs an LLM through an adversarial testing pipeline with five
stages, each answering a different safety question:

```
Adversarial Prompt Dataset (prompts/)
    |
    v
Prompt Mutation (generator/)        "Does the model generalize its refusals,
    |                                or just pattern-match on exact wording?"
    v
Attack Runner (runner/)             "What does the target model actually say
    |                                when it receives these prompts?"
    v
Safety Judge (judge/)               "Was that response actually safe?"
    |
    v
Safety Report (reports/)            "How bad is it, by category, with evidence?"
    |
    v
Defense Layer (defense/)            "Can I stop this in production, cheaply?"
```

Generation and judgment are deliberately separate stages: `attack_runner.py`
only records what the model said, and `safety_judge.py` decides whether
that was safe. This means the judge can be re-run, tuned, or swapped out
without spending more inference time re-generating responses.

---

## Stage 1: Adversarial Prompt Dataset

`prompts/attack_prompts.json` holds a categorized seed set covering four
attack types: jailbreak (persona/role-play override attempts), prompt
injection (instructions smuggled inside content that should be treated as
data), harmful content requests (direct asks for disallowed content), and
PII/data leakage (attempts to extract system prompts or fabricated
"memorized" personal data).

Categorizing attacks, rather than treating them as one undifferentiated
list, is what makes the eventual report useful — "60% attack success rate"
is a vague number, but "60% on prompt injection, 5% on direct harmful
requests" tells you exactly where the model's defenses are weak.

---

## Stage 2: Prompt Mutation

A static, hand-written attack list has a specific failure mode: a model
can learn to refuse the *exact phrasing* of a known attack without
actually being robust to the underlying pattern. `generator/mutate_prompts.py`
uses an LLM to paraphrase each seed prompt into several variations —
different tone, framing, or persona, same underlying intent.

Running the mutated set through the same pipeline as the seeds is what
distinguishes "the model has memorized these specific refusals" from
"the model actually generalizes."

---

## Stage 3: Attack Runner

`runner/attack_runner.py` sends every prompt (seed and mutated) to the
target model via Ollama's local API and records the raw response, along
with latency and any errors. This stage makes no safety judgment at all —
it's purely a data collection step, which keeps it simple and makes its
output reusable across different judge implementations.

---

## Stage 4: Safety Judge

`judge/safety_judge.py` classifies each recorded response as SAFE or
UNSAFE using two layers:

1. **Rule-based check** — fast pattern matching for obvious refusal
   language. Catches the easy cases without spending an extra LLM call.
2. **LLM-as-judge** — for anything the rule-based layer doesn't
   confidently call safe, a second model evaluates the prompt/response
   pair and returns a verdict with reasoning.

Rule-based first, judge second, in that order: this keeps the pipeline
fast and cheap on the obvious cases, and reserves judge calls for
responses that actually need nuanced evaluation — did this response
comply with a harmful request, or just discuss the topic academically?
That distinction needs judgment, not keyword matching.

---

## Stage 5: Safety Report

`reports/report_generator.py` converts judge output into a JSON report
(for programmatic use, e.g. a CI gate) and an HTML report (for a human to
actually read) — the same JSON + HTML pattern used in
`rag-evaluation-framework`. The report leads with attack success rate by
category and lists every unsafe response with the judge's reasoning,
because a summary number without the underlying evidence isn't
actionable — you need to see *what* went wrong to fix it.

---

## Stage 6: Defense Layer

`defense/safety_filter.py` is a thin, fast, rule-based filter meant to sit
in front of a production API (like `ml-api-service`'s `/generate`
endpoint) without changing how that API works internally. It checks input
*before* it reaches the model (blocking obvious jailbreak/injection
patterns before spending inference time on them) and checks output
*after* the model responds (catching cases where the input filter missed
something but the model complied anyway).

This filter is intentionally not a replacement for Stage 4's LLM-as-judge.
Different job, different latency budget: the filter needs to run in
milliseconds on every production request; the judge does thorough offline
evaluation during testing. Conflating the two would make the filter too
slow for production or the judge too shallow for real evaluation.

---

## Why This Order

Each stage depends on what the previous one produced:

- Mutation (Stage 2) needs seed prompts (Stage 1) to paraphrase.
- Judging (Stage 4) needs recorded responses (Stage 3) to evaluate.
- The report (Stage 5) needs judged verdicts, not raw responses, or it
  couldn't compute an attack success rate.
- The defense layer (Stage 6) is informed by *all* of the above — the
  block patterns it uses are drawn directly from attack categories this
  pipeline proved are effective.

The pipeline is meant to be read as a full loop: generate attacks, test
them, judge the results, report on what's weak, then defend against
exactly that.