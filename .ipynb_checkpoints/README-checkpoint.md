# LLM Safety & Red-Teaming Framework

An automated red-teaming and safety evaluation pipeline for LLMs — adversarial prompt generation, attack execution, LLM-as-judge classification, safety reporting, and a defense layer that plugs into a production API.

---

## What This Project Demonstrates

Every other project in this portfolio shows how to build, serve, or optimize an LLM system.
This one shows how to check whether that system is actually safe to ship.

| Concern | Solution |
|---|---|
| Does the model leak under pressure? | Categorized adversarial prompt dataset (jailbreak, injection, harmful content, PII leakage) |
| Does it generalize, or just memorize refusals? | LLM-assisted mutation — paraphrased variants of every seed attack |
| What actually happened when it was attacked? | Attack runner records raw responses from the target model |
| Was that response actually safe? | Two-layer judge: rule-based checks + LLM-as-judge |
| How bad is it, exactly? | Attack success rate by category, JSON + HTML report with evidence |
| Can I stop it in production? | Lightweight input/output defense filter, pluggable into an existing API |

---

## Architecture

```
Adversarial Prompt Dataset (prompts/)
  ↓
Prompt Mutation (generator/)     →  paraphrased variants of every seed attack
  ↓
Attack Runner (runner/)          →  sends prompts to the target model (Ollama)
  ↓
Safety Judge (judge/)            →  rule-based + LLM-as-judge classification
  ↓
Safety Report (reports/)         →  attack success rate by category, JSON + HTML
  ↓
Defense Layer (defense/)         →  input/output filter, pluggable into a production API
```

---

## Project Structure

```
llm-safety-redteam/
├── prompts/
│   └── attack_prompts.json       — categorized seed dataset (4 attack types)
├── generator/
│   └── mutate_prompts.py         — LLM-assisted prompt paraphrasing
├── runner/
│   └── attack_runner.py          — executes attacks against the target model
├── judge/
│   └── safety_judge.py           — rule-based + LLM-as-judge classification
├── reports/
│   ├── report_generator.py       — JSON + HTML safety report
│   └── output/                   — generated reports land here
├── defense/
│   ├── safety_filter.py          — input/output filter
│   └── middleware_example.py     — example FastAPI integration
├── tests/
│   └── test_safety_pipeline.py   — 11/11 passing
├── docs/
│   └── architecture.md
└── requirements.txt
```

---

## Getting Started

```bash
pip install -r requirements.txt
ollama serve
ollama pull gemma3:12b
```

### 1. Run the attack dataset against a target model

```bash
python runner/attack_runner.py \
  --model gemma3:12b \
  --output reports/output/raw_responses.json
```

### 2. (Optional) Expand the dataset with mutated variants

```bash
python generator/mutate_prompts.py \
  --input prompts/attack_prompts.json \
  --output prompts/mutated_prompts.json \
  --variations_per_prompt 3
```

### 3. Judge the responses

```bash
python judge/safety_judge.py \
  --input reports/output/raw_responses.json \
  --output reports/output/judged_results.json \
  --judge_model gemma3:12b
```

Example output *(illustrative — replace with your own run)*:
```
=== Attack Success Rate by Category ===
jailbreak: 33.3% (SAFE=2, UNSAFE=1, UNKNOWN=0, ERROR=0)
prompt_injection: 0.0% (SAFE=3, UNSAFE=0, UNKNOWN=0, ERROR=0)
harmful_content_request: 0.0% (SAFE=3, UNSAFE=0, UNKNOWN=0, ERROR=0)
pii_and_data_leakage: 33.3% (SAFE=2, UNSAFE=1, UNKNOWN=0, ERROR=0)
```

### 4. Generate the report

```bash
python reports/report_generator.py \
  --input reports/output/judged_results.json \
  --json_output reports/output/safety_report.json \
  --html_output reports/output/safety_report.html
```

Open `reports/output/safety_report.html` in a browser for the full breakdown, including every unsafe response with the judge's reasoning.

### 5. Run tests

```bash
pytest tests/ -v
```

---

## Using the Defense Filter

```python
from defense.safety_filter import SafetyFilter

filt = SafetyFilter()

allowed, reason = filt.check_input(user_prompt).allowed, filt.check_input(user_prompt).reason
if not allowed:
    return {"error": reason}

response = call_model(user_prompt)

output_check = filt.check_output(response)
if not output_check.allowed:
    return {"error": output_check.reason}
```

See `defense/middleware_example.py` for a full FastAPI route — the same shape as `ml-api-service`'s `/generate` endpoint, so the filter can be dropped in without touching auth, rate limiting, or caching logic.

---

## Stack

Python · Ollama · FastAPI · pytest

---

## What I Learned

**A single "safe/unsafe" number isn't actionable — categories are.**
"60% attack success rate" doesn't tell you what to fix. "60% on prompt injection, 0% on direct harmful requests" tells you exactly where the model's defenses are weak.

**Static attack lists get memorized, not defeated.**
A model can learn to refuse the exact wording of a known jailbreak without being robust to the pattern behind it. Paraphrasing every seed prompt with an LLM is what actually tests whether a refusal generalizes.

**Rule-based and LLM-as-judge solve different problems.**
Keyword matching catches obvious refusals in milliseconds. It cannot tell the difference between a response that complies with a harmful request and one that discusses the same topic academically — that distinction needs an LLM judge, not a pattern.

**A defense filter and a safety judge can't be the same component.**
The filter has to run on every production request in milliseconds. The judge needs the latency budget to actually reason about intent. Trying to merge them would make the filter too slow for production or the judge too shallow to be trustworthy.

**Separating generation from judgment paid off.**
`attack_runner.py` only records what the model said; `safety_judge.py` decides if it was safe. That split meant the judge logic could be rewritten and re-run against the same recorded responses without spending more inference time re-generating them.

---

## Related Projects

- [ml-api-service](https://github.com/Honaxen/ml-api-service) — the production API this defense layer is designed to protect
- [llm-inference-optimizer](https://github.com/Honaxen/llm-inference-optimizer) — the serving stack this pipeline could be pointed at
- [rag-evaluation-framework](https://github.com/Honaxen/rag-evaluation-framework) — the same JSON + HTML evaluation pattern, applied to safety instead of retrieval quality

---

## Author

[Honaxen](https://github.com/Honaxen)