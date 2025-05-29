import requests

base_url = "http://jovana.openbrain.io:7272"

alzrag_prompt = {
    "name": "alzrag_test_single",
    "display_name": "AlzRAG Test Single",
    "description": "Test prompt for AlzRAG dropdown visibility.",
    "template": """You are AlzRAG Test Single, a specialized assistant for validating prompt visibility in the UI.

Guidelines:
- Respond briefly confirming you are the AlzRAG test prompt.
- This is for testing only.

If you see this in the dropdown, the prompt was created successfully.""",
    "input_types": {"query": "string"},
    "metadata": {
        "ui_display": True,
        "in_dropdown": True,
        "show_in_ui": True,
        "priority": 1
    }
}

# Remove existing prompt with same name (if exists)
requests.delete(f"{base_url}/v3/prompts/{alzrag_prompt['name']}")

# Create the new prompt
resp = requests.post(f"{base_url}/v3/prompts", json=alzrag_prompt)

print(f"Status: {resp.status_code}")
if resp.status_code in [200, 201, 204]:
    print("Prompt created successfully.")
else:
    print("Failed to create prompt.")
    print("Response:", resp.text)

# Optional: list all prompt names to verify
resp_list = requests.get(f"{base_url}/v3/prompts")
if resp_list.status_code == 200:
    all_names = [p.get('name') for p in resp_list.json().get('results', [])]
    print("All prompt names:", all_names)
else:
    print("Could not fetch prompt list.")
