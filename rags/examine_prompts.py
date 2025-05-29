import requests
import json

def examine_prompts():
    # Base URL for R2R API
    base_url = "http://jovana.openbrain.io:7272"
    
    print("Fetching all prompts...")
    try:
        response = requests.get(f"{base_url}/v3/prompts")
        if response.status_code == 200:
            prompts_data = response.json()
            if 'results' in prompts_data:
                all_prompts = prompts_data['results']
                print(f"Found {len(all_prompts)} total prompts")
                
                # Find our AlzRAG prompts
                alz_prompts = [p for p in all_prompts if p['name'].startswith('alzrag_')]
                print(f"\nFound {len(alz_prompts)} AlzRAG prompts:")
                
                # Examine each AlzRAG prompt in detail
                for p in alz_prompts:
                    print(f"\nExamining prompt: {p['name']}")
                    # Print each field to see what's actually present
                    for key, value in p.items():
                        if key not in ['template']:  # Skip template since it's long
                            if isinstance(value, dict) or isinstance(value, list):
                                print(f"- {key}: {json.dumps(value)}")
                            else:
                                print(f"- {key}: {value}")
                
                # Look for prompts that do appear in dropdown to compare
                print("\nLooking for prompts that should appear in dropdown:")
                dropdown_prompts = []
                for p in all_prompts:
                    # Check if any of these common prompts exist
                    if p['name'] in ['rag', 'medical_record_rag', 'static_rag_agent', 'dynamic_rag_agent']:
                        dropdown_prompts.append(p)
                
                if dropdown_prompts:
                    for dp in dropdown_prompts:
                        print(f"\nExamining reference prompt: {dp['name']}")
                        # Print fields that might be relevant to dropdown appearance
                        for key in ['name', 'display_name', 'description', 'metadata']:
                            if key in dp:
                                if isinstance(dp[key], dict) or isinstance(dp[key], list):
                                    print(f"- {key}: {json.dumps(dp[key])}")
                                else:
                                    print(f"- {key}: {dp[key]}")
                else:
                    print("No reference prompts found for comparison")
            else:
                print("No 'results' key in response")
        else:
            print(f"Failed to retrieve prompts: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error examining prompts: {e}")
    
    # Now let's try a more direct approach to fix display names
    print("\nTrying to update display names directly...")
    display_names = {
        "alzrag_research": "AlzRAG Research",
        "alzrag_clinical": "AlzRAG Clinical",
        "alzrag_patient": "AlzRAG Patient Education",
        "alzrag_treatment": "AlzRAG Treatment",
        "alzrag_synthesis": "AlzRAG Research Synthesis"
    }
    
    # Try to update using the POST method with just the display name
    for name, display in display_names.items():
        print(f"Updating {name} with display name '{display}'...")
        try:
            # Try a simple approach with just the fields we absolutely need
            payload = {
                "name": name,
                "display_name": display
            }
            response = requests.post(f"{base_url}/v3/prompts", json=payload)
            if response.status_code in [200, 201, 204]:
                print(f"✓ Updated {name} with simple payload")
            else:
                print(f"× Failed with simple payload: {response.status_code}")
                # Try with a wrapper
                response = requests.post(f"{base_url}/v3/prompts", 
                                        json={"prompt": {"name": name, "display_name": display}})
                if response.status_code in [200, 201, 204]:
                    print(f"✓ Updated {name} with wrapped payload")
                else:
                    print(f"× Failed with wrapped payload: {response.status_code}")
        except Exception as e:
            print(f"× Error updating {name}: {e}")
    
    print("\nInspection and update completed.")
    print("Restart the R2R containers:")
    print("docker restart r2r-r2r-1 r2r-r2r-dashboard-1")

if __name__ == "__main__":
    examine_prompts()