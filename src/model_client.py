from langchain_ollama import ChatOllama
class ModelClient:
    def __init__(
        self,
        model_name="qwen3:8b",
        temperature=0.0,
        format=None
    ):
        self.model = ChatOllama(
            model=model_name,
            temperature=temperature,
            format=format
        )
    def complete(self, messages, tools=None):
        response = self.model.invoke(messages)
        return response