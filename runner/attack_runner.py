"""
Sends every prompt in the adversarial dataset to a target LLM (via Ollama)
and records the raw responses for the judge stage to classify.

This script deliberately does NOT decide what's safe or unsafe -- that's
judge/'s job. Keeping generation and classification separate means the
judge can be re-run against the same responses without re-hitting the
model every time, and the judge logic can be swapped without touching
how attacks are executed.

Usage:
    python attack_runner.py --model gemma3:12b --output ../reports/output/raw_responses.json
"""

import argparse
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3:12b"
PROMPTS_FILE = Path(__file__).parent.parent / "prompts" / "attack_prompts.json"


def load_prompts(path: Path) -> list:
    """Flatten the categorized prompt dataset into a single list, keeping
    the category attached to each prompt so results can be grouped later."""
    with open(path, "r") as f:
        data = json.load(f)

    flattened = []
    for category, content in data["categories"].items():
        for item in content["prompts"]:
            flattened.append({
                "id": item["id"],
                "category": category,
                "prompt": item["prompt"],
                "expected_behavior": item["expected_behavior"],
            })
    return flattened


def call_ollama(model: str, prompt: str, timeout: int = 60) -> dict:
    """
    Calls the local Ollama /api/generate endpoint.
    Local HTTP to localhost -- no SSL handling needed here, unlike
    external API calls to services like Wikipedia.
    """
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {
                "response_text": body.get("response", ""),
                "latency_ms": round(elapsed_ms, 2),
                "error": None,
            }
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        return {
            "response_text": "",
            "latency_ms": None,
            "error": str(e),
        }


def run_attacks(model: str, prompts: list) -> list:
    results = []
    total = len(prompts)

    for i, item in enumerate(prompts, start=1):
        print(f"[{i}/{total}] {item['id']} ({item['category']})...")
        outcome = call_ollama(model, item["prompt"])

        results.append({
            "id": item["id"],
            "category": item["category"],
            "prompt": item["prompt"],
            "expected_behavior": item["expected_behavior"],
            "model": model,
            "response_text": outcome["response_text"],
            "latency_ms": outcome["latency_ms"],
            "error": outcome["error"],
        })

        if outcome["error"]:
            print(f"    error: {outcome['error']}")

    return results


def main(args):
    prompts = load_prompts(PROMPTS_FILE)
    print(f"Loaded {len(prompts)} adversarial prompts across "
          f"{len(set(p['category'] for p in prompts))} categories.")

    results = run_attacks(args.model, prompts)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    error_count = sum(1 for r in results if r["error"])
    print(f"\nDone. {len(results) - error_count}/{len(results)} succeeded.")
    print(f"Raw responses saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run adversarial prompts against a target LLM")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--output", default="../reports/output/raw_responses.json")
    args = parser.parse_args()

    main(args)
