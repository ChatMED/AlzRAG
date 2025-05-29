# configure_r2r_interface.py
import requests
import json
import os

def configure_r2r_interface():
    # Base URL for R2R API
    base_url = "http://jovana.openbrain.io:7272"
    
    print(f"Configuring R2R interface at {base_url}")
    
    # Try to get current system settings to understand the format
    try:
        # First attempt to get settings to see what's supported
        settings_url = f"{base_url}/v3/system/settings"
        settings_response = requests.get(settings_url)
        
        if settings_response.status_code == 200:
            current_settings = settings_response.json()
            print("Successfully retrieved current settings")
            
            # Check if there's a UI configuration section
            if 'results' in current_settings and 'ui_config' in current_settings['results']:
                print("Found UI configuration section")
                ui_config = current_settings['results']['ui_config']
            else:
                print("No UI configuration found in settings, will create new")
                ui_config = {}
        else:
            print(f"Could not retrieve settings: {settings_response.status_code}")
            ui_config = {}
    except Exception as e:
        print(f"Error retrieving settings: {e}")
        ui_config = {}
    
    # Define the configuration for the RAG options in the interface
    rag_config = {
        "rag_options": [
            {
                "id": "alzrag_research",
                "name": "AlzRAG Research",
                "description": "General Alzheimer's research and literature analysis",
                "icon": "book",
                "color": "#4285F4",
                "category": "Research"
            },
            {
                "id": "alzrag_clinical",
                "name": "AlzRAG Clinical", 
                "description": "MRI analysis and clinical applications for Alzheimer's",
                "icon": "hospital",
                "color": "#34A853",
                "category": "Clinical"
            }
        ],
        "default_rag": "alzrag_research"
    }
    
    # Update the UI configuration
    if 'prompt_templates' in ui_config:
        # If prompt_templates exists, update it
        ui_config['prompt_templates'] = rag_config
    else:
        # Otherwise add it directly
        ui_config['prompt_templates'] = rag_config
    
    # Now try different approaches to update the interface configuration
    
    # Approach 1: Try direct API calls to update system settings
    try:
        print("Attempting to update system settings...")
        
        # Prepare the update payload
        update_payload = {
            "ui_config": ui_config
        }
        
        # Try to update system settings
        settings_update_url = f"{base_url}/v3/system/settings"
        update_response = requests.post(settings_update_url, json=update_payload)
        
        if update_response.status_code in [200, 201, 204]:
            print("✓ Successfully updated system settings!")
            return
        else:
            print(f"× Settings update failed: {update_response.status_code} - {update_response.text}")
            # Continue to try other approaches
    except Exception as e:
        print(f"× Error updating system settings: {e}")
    
    # Approach 2: Try updating through the prompts API
    try:
        print("Attempting to update prompts with display info...")
        
        for rag_option in rag_config["rag_options"]:
            # Try to update prompt with display metadata
            prompt_update_url = f"{base_url}/v3/prompts/{rag_option['id']}"
            
            update_data = {
                "display_name": rag_option["name"],
                "description": rag_option["description"],
                "metadata": {
                    "icon": rag_option["icon"],
                    "color": rag_option["color"],
                    "category": rag_option["category"]
                }
            }
            
            update_response = requests.put(prompt_update_url, json=update_data)
            
            if update_response.status_code in [200, 201, 204]:
                print(f"✓ Updated display info for {rag_option['id']}")
            else:
                print(f"× Could not update {rag_option['id']}: {update_response.status_code}")
    except Exception as e:
        print(f"× Error updating prompts: {e}")
    
    # Approach 3: Direct database configuration (if available)
    try:
        print("Checking for database configuration API...")
        
        # Some R2R instances have a direct database configuration endpoint
        db_config_url = f"{base_url}/v3/system/config"
        
        config_payload = {
            "key": "ui_prompt_templates",
            "value": json.dumps(rag_config)
        }
        
        config_response = requests.post(db_config_url, json=config_payload)
        
        if config_response.status_code in [200, 201, 204]:
            print("✓ Successfully updated system configuration via database API!")
        else:
            print(f"× Database configuration update failed: {config_response.status_code}")
    except Exception as e:
        print(f"× Error with database configuration: {e}")
    
    # Approach 4: Save configuration to a file for manual application
    try:
        print("Creating configuration file for manual application...")
        
        # Save the configuration to a file for manual application
        with open("rag_ui_config.json", "w") as f:
            json.dump(rag_config, f, indent=2)
        
        print("✓ Created rag_ui_config.json - you can manually apply this configuration")
        print("   through the admin interface if the automatic methods didn't work.")
    except Exception as e:
        print(f"× Error creating configuration file: {e}")
    
    print("\nConfiguration process completed. If automatic configuration wasn't successful,")
    print("you may need to manually configure the interface through the admin panel.")

if __name__ == "__main__":
    configure_r2r_interface()