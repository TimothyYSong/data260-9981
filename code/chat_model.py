from src.model_client import ModelClient

model_client = ModelClient(
    model_name="qwen3:8b",
    temperature=0.0,
)


def generate_chat_reply(prompt: str, *, return_usage=False):
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    response = model_client.complete(prompt)
    reply = response.content

    if not isinstance(reply, str) or not reply.strip():
        raise ValueError("Ollama returned an empty response")

    reply = reply.strip()

    # LangChain/Ollama supplies actual model token counts.
    usage = getattr(response, "usage_metadata", None) or {}
    metadata = getattr(response, "response_metadata", None) or {}

    prompt_tokens = usage.get("input_tokens")
    completion_tokens = usage.get("output_tokens")

    if prompt_tokens is None:
        prompt_tokens = metadata.get("prompt_eval_count")

    if completion_tokens is None:
        completion_tokens = metadata.get("eval_count")

    if return_usage:
        return {
            "reply": reply,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }

    # Preserve the original function behavior.
    return reply