"""
Example of wiring SafetyFilter into a FastAPI /generate endpoint.

This mirrors the shape of ml-api-service's route -- copy this pattern
into that project's routes/generate.py to add a defense layer without
touching its auth, rate limiting, or caching logic.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from safety_filter import SafetyFilter

app = FastAPI()
safety_filter = SafetyFilter()


class GenerateRequest(BaseModel):
    prompt: str


def call_model(prompt: str) -> str:
    """Placeholder -- replace with the real model call (e.g. Ollama, vLLM)."""
    return f"[model response to: {prompt}]"


@app.post("/generate")
def generate(req: GenerateRequest):
    input_check = safety_filter.check_input(req.prompt)
    if not input_check.allowed:
        raise HTTPException(status_code=400, detail=f"Request blocked: {input_check.reason}")

    response_text = call_model(req.prompt)

    output_check = safety_filter.check_output(response_text)
    if not output_check.allowed:
        raise HTTPException(status_code=500, detail=f"Response blocked: {output_check.reason}")

    return {"response": response_text}
