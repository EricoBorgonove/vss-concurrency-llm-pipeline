"""Cliente minimo para chamada de LLM via API HTTP."""

import json
import os
import urllib.error
import urllib.request


DEFAULT_MODEL = "gpt-4.1-mini"
RESPONSES_URL = "https://api.openai.com/v1/responses"


class LlmClientError(RuntimeError):
    """Erro de chamada ou resposta invalida da LLM."""


def configured_model():
    return os.environ.get("VSS_LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def api_key():
    return os.environ.get("OPENAI_API_KEY", "").strip()


def is_configured():
    return bool(api_key())


def extract_output_text(payload):
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]

    chunks = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks).strip()


def create_text_response(prompt, system_prompt="", model=None, timeout=90):
    key = api_key()
    if not key:
        raise LlmClientError("OPENAI_API_KEY nao configurada")

    request_payload = {
        "model": model or configured_model(),
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": system_prompt or "Responda de forma objetiva.",
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            },
        ],
    }
    data = json.dumps(request_payload).encode("utf-8")
    request = urllib.request.Request(
        RESPONSES_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise LlmClientError(f"erro HTTP da LLM ({exc.code}): {body}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise LlmClientError(f"erro ao chamar LLM: {exc}") from exc

    text = extract_output_text(payload)
    if not text:
        raise LlmClientError("resposta da LLM sem texto")
    return text
