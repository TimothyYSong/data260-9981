import json
from src.model_client import ModelClient
client = ModelClient()
with open("AGENT.md", "r") as file:
    agent_instructions = file.read()
history = [
    {
        "role": "system",
        "content": agent_instructions
    }
]
turn_count = 0
cumulative_input_tokens = 0
cumulative_output_tokens = 0
while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        print("\nSession totals")
        print(f"Turns: {turn_count}")
        print(f"Input tokens: {cumulative_input_tokens}")
        print(f"Output tokens: {cumulative_output_tokens}")
        break
    if user_input == "/stats":
        history_length = len(
            json.dumps(history)
        )
        print("\nStats")
        print(f"Turns: {turn_count}")
        print(f"Input tokens: {cumulative_input_tokens}")
        print(f"Output tokens: {cumulative_output_tokens}")
        print(f"History length: {history_length}")
        continue
    history.append({
        "role": "user",
        "content": user_input
    })
    response = client.complete(history)
    input_tokens = response.usage_metadata["input_tokens"]
    output_tokens = response.usage_metadata["output_tokens"]
    total_tokens = response.usage_metadata["total_tokens"]
    turn_count += 1
    cumulative_input_tokens += input_tokens
    cumulative_output_tokens += output_tokens
    print(f"\nAssistant: {response.content}")
    print(f"Input tokens: {input_tokens}")
    print(f"Output tokens: {output_tokens}")
    print(f"Total tokens: {total_tokens}")
    history.append({
        "role": "assistant",
        "content": response.content
    })