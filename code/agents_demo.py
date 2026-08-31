import json
from src.model_client import ModelClient
def pipeline(title, content, temperature):
    client = ModelClient(
        model_name="qwen3:8b",
        temperature=temperature,
        format="json"
    )
    planner_prompt = f"""
    You are the Planner agent, so please analyze the title and content.
    Title: {title}
    Content: {content}
    Please give me three tags and a one sentence summary up to twenty five words.
    Return only valid JSON in exactly this format:
    {{
        "tags": ["tag1", "tag2", "tag3"],
        "summary": "summary here"
    }}
    """
    response = client.complete(planner_prompt)
    planner_output = json.loads(response.content)
    print("Planner Output")
    print(json.dumps(planner_output, indent=2))
    reviewer_prompt = f"""
    You are the Reviewer agent, so please review the Planner output.
    Title: {title}
    Content: {content}
    Planner output: {json.dumps(planner_output)}
    Verify that there are 3 tags that are relevant to the title and content. 
    Also please make sure that the summary is correct and does not exceed twenty five words.
    If there is anything wrong, please fix it.
    Return only valid JSON in exactly this format:
    {{
        "tags": ["tag1", "tag2", "tag3"],
        "summary": "summary"
    }}
    """
    reviewer_response = client.complete(reviewer_prompt)
    reviewer_output = json.loads(reviewer_response.content)
    print("Reviewer Output")
    print(json.dumps(reviewer_output, indent=2))
    final_output = {
        "tags": reviewer_output["tags"][:3],
        "summary": " ".join(reviewer_output["summary"].split()[:25])
    }
    print("Finalized Output")
    print(json.dumps(final_output, indent=2))
    return final_output
if __name__ == "__main__":
    title = input("Please enter a title... ")
    content = input("Please enter the content... ")
    pipeline(title, content, 0.0)