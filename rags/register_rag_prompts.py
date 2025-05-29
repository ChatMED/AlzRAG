# register_rag_prompts.py
import os
import requests
from r2r import R2RClient

def register_rag_prompts():
    # Get environment variables
    openai_api_key = os.environ.get("OPENAI_API_KEY", "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")
    r2r_url = os.environ.get("NEXT_PUBLIC_R2R_DEPLOYMENT_URL", "http://jovana.openbrain.io:7272/v3")
    
    # Strip the /v3 suffix if present for the client base URL
    base_url = r2r_url.replace("/v3", "")
    
    print(f"Using R2R base URL: {base_url}")
    
    # Try to get a token using direct authentication
    # This approach uses direct API calls to get a token first
    try:
        # First, try to get a token directly
        auth_url = f"{base_url}/auth/login"
        auth_data = {
            "username": "your-email@example.com",  # Replace with your email
            "password": "your-password"            # Replace with your password
        }
        
        print(f"Attempting to authenticate directly with R2R at {auth_url}")
        
        # Make direct authentication request
        auth_response = requests.post(auth_url, data=auth_data)
        
        if auth_response.status_code == 200:
            token_data = auth_response.json()
            token = token_data.get("results", {}).get("access_token")
            
            if token:
                print("Authentication successful!")
                
                # Initialize client with base URL (no /v3)
                client = R2RClient(base_url=base_url)
                
                # Manually add the token to the session headers
                if hasattr(client, '_client') and hasattr(client._client, 'session'):
                    client._client.session.headers.update({"Authorization": f"Bearer {token}"})
                    print("Added token to client session headers")
                else:
                    print("Warning: Could not find client.session to add token. Authentication may fail.")
            else:
                print("Auth response did not contain token:", token_data)
                
        else:
            print(f"Authentication failed with status {auth_response.status_code}: {auth_response.text}")
            # Fall back to using R2RClient without auth (may still work if the system allows anonymous access)
            client = R2RClient(base_url=base_url)
            print("Created client without explicit authentication")
            
    except Exception as e:
        print(f"Authentication error: {e}")
        # Fall back to basic client
        client = R2RClient(base_url=base_url)
        print("Created client without authentication due to error")
    
    # Define our RAG prompts
    
    # Research RAG
    research_prompt = {
        "name": "alzrag_research",
        "template": """You are AlzRAG Research, a specialized medical assistant for Alzheimer's disease research. 
        Answer the user's question based on the retrieved medical literature with academic rigor.
        
        Guidelines:
        - Focus on research findings, mechanisms, and scientific evidence
        - Provide well-structured, evidence-based responses with proper citations
        - Analyze research methodology and statistical significance when relevant
        - Highlight conflicting findings and research gaps
        - Explain complex mechanisms in clear, accessible language while maintaining accuracy
        - Emphasize the latest research developments and their implications
        - When discussing treatments, focus on mechanism of action and evidence quality
        
        Always cite your sources properly using the document title and year.
        If information is contradictory, acknowledge the conflict and explain different perspectives.
        If you don't know the answer, say so rather than speculating.""",
        "input_types": {"query": "string"}
    }

    # Clinical RAG
    clinical_prompt = {
        "name": "alzrag_clinical",
        "template": """You are AlzRAG Clinical, a specialized medical assistant for Alzheimer's disease imaging and clinical applications.
        
        Guidelines:
        - Focus on MRI analysis, radiological findings, and clinical implications
        - Interpret imaging biomarkers and their significance for diagnosis and monitoring
        - Provide structured responses with clear clinical relevance
        - Explain imaging patterns associated with different stages of disease
        - Discuss differential diagnoses when appropriate
        - Connect imaging findings to clinical symptoms and progression
        - When discussing treatment implications, emphasize the need for clinical judgment
        
        Always cite your sources properly using the document title and year.
        If you don't know the answer, acknowledge the limitations rather than speculating.
        Remember that your responses may be read by healthcare professionals making clinical decisions.""",
        "input_types": {"query": "string"}
    }

    # Create or update the prompts
    for prompt in [research_prompt, clinical_prompt]:
        try:
            print(f"Attempting to create/update prompt: {prompt['name']}")
            
            # First try to create
            try:
                response = client.prompts.create(
                    name=prompt["name"],
                    template=prompt["template"],
                    input_types=prompt["input_types"]
                )
                print(f"Created prompt: {prompt['name']}")
            except Exception as create_error:
                print(f"Create failed: {create_error}")
                
                # If creation fails, try to update
                try:
                    response = client.prompts.update(
                        name=prompt["name"],
                        template=prompt["template"],
                        input_types=prompt["input_types"]
                    )
                    print(f"Updated prompt: {prompt['name']}")
                except Exception as update_error:
                    print(f"Update also failed: {update_error}")
                    
                    # As a last resort, try alternative API
                    print("Trying alternative direct API approach...")
                    
                    # Direct API call to create prompt
                    prompt_url = f"{base_url}/v3/prompts"
                    prompt_data = {
                        "name": prompt["name"],
                        "template": prompt["template"],
                        "input_types": prompt["input_types"]
                    }
                    
                    # Use the token if we have it
                    headers = {}
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                    
                    # Try POST to create
                    create_response = requests.post(prompt_url, json=prompt_data, headers=headers)
                    
                    if create_response.status_code in [200, 201]:
                        print(f"Created prompt via direct API: {prompt['name']}")
                    else:
                        # Try PUT to update
                        update_url = f"{base_url}/v3/prompts/{prompt['name']}"
                        update_response = requests.put(update_url, json=prompt_data, headers=headers)
                        
                        if update_response.status_code in [200, 201, 204]:
                            print(f"Updated prompt via direct API: {prompt['name']}")
                        else:
                            print(f"Direct API attempt failed: {update_response.status_code} - {update_response.text}")
                
        except Exception as e:
            print(f"Error with {prompt['name']}: {str(e)}")

    print("RAG options registration process completed!")

if __name__ == "__main__":
    register_rag_prompts()