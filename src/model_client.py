from langchain_ollama import ChatOllama


class ModelClient:
    def __init__(
        self,
        model_name="qwen3:8b",
        temperature=0.0,
        format=None,
    ):
        self.model = ChatOllama(
            model=model_name,
            temperature=temperature,
            format=format,
        )

    def complete(
        self,
        messages,
        tools=None,
        max_output_tokens=None,
    ):
        model = self.model

        if tools:
            model = model.bind_tools(tools)

        if max_output_tokens is not None:
            if max_output_tokens < 1:
                raise ValueError(
                    "max_output_tokens must be positive"
                )
            model = model.bind(
                options={"num_predict": max_output_tokens}
            )

        return model.invoke(messages)
