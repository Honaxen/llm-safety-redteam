# LLM Safety & Red-Teaming Framework

Work in progress -- this README is a placeholder and will be replaced once the project is complete.

An automated red-teaming and safety evaluation pipeline for LLMs -- adversarial prompt generation, attack execution, LLM-as-judge classification, safety reporting, and a defense layer that plugs into a production API.

---

## What This Project Will Demonstrate

Every other project in this portfolio shows how to build, serve, or optimize an LLM system.
This one shows how to make sure that system is actually safe to ship.

Concern -> Solution (planned)
- Does the model leak under pressure?      -> Adversarial prompt dataset (jailbreak, injection, harmful content, PII leakage)
- How do I know if a response is unsafe?   -> LLM-as-judge + rule-based classifier
- How bad is it, exactly?                  -> Attack success rate by category, JSON + HTML report
- Can I actually stop it?                  -> Input/output defense layer, pluggable into ml-api-service

---

## Planned Architecture

Adversarial Prompt Dataset (prompts/)
  -> Prompt Generator (generator/)          expands/mutates attack prompts with an LLM
  -> Attack Runner (runner/)                sends prompts to the target model (Ollama)
  -> Judge (judge/)                         classifies each response: safe / unsafe / category
  -> Safety Report (reports/)               attack success rate by category, JSON + HTML
  -> Defense Layer (defense/)               input/output filter, measured before/after on ml-api-service

---

## Project Structure

llm-safety-redteam/
  prompts/           - categorized adversarial prompt dataset
  generator/         - LLM-assisted prompt generation/mutation
  runner/            - executes attacks against the target model
  judge/             - safe/unsafe classification (LLM-as-judge + rules)
  defense/           - input/output filtering layer
  reports/           - JSON + HTML safety reports
  tests/
  docs/

---

## Stack

Python - Ollama - FastAPI (defense layer) - pytest

---

## Status

- [ ] Adversarial prompt dataset (4 categories)
- [ ] Prompt generator/mutator
- [ ] Attack runner against Ollama
- [ ] LLM-as-judge classifier
- [ ] Safety report (JSON + HTML)
- [ ] Defense layer + before/after evaluation on ml-api-service

---

## Related Projects

- [ml-api-service](https://github.com/Honaxen/ml-api-service) -- the production API this defense layer is designed to protect
- [rag-evaluation-framework](https://github.com/Honaxen/rag-evaluation-framework) -- similar evaluation/reporting pattern, applied to safety instead of retrieval quality

---

## Author

[Honaxen](https://github.com/Honaxen)
