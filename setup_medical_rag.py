# setup_medical_rag.py
from r2r import R2RClient
import toml

def setup_medical_prompts():
    # Load prompts from the TOML file
    config = toml.load("py/r2r/medical_rag.toml")
    
    # Initialize the client
    client = R2RClient("http://localhost:7272")
    
    # Login if required
    client.users.login("admin@example.com", "change_me_immediately")
    
    # Add the medical_record_rag prompt
    rag_prompt = config["prompts"]["medical_record_rag"]["template"]
    client.prompts.create(
        name="medical_record_rag",
        template=rag_prompt,
        input_types={"query": "str", "context": "str"}
    )
    
    # Add the medical_record_agent prompt
    agent_prompt = config["prompts"]["medical_record_agent"]["template"]
    client.prompts.create(
        name="medical_record_agent",
        template=agent_prompt,
        input_types={"date": "str"}
    )
    
    # Add the medical_record_dynamic_agent prompt
    dynamic_agent_prompt = config["prompts"]["medical_record_dynamic_agent"]["template"]
    client.prompts.create(
        name="medical_record_dynamic_agent",
        template=dynamic_agent_prompt,
        input_types={}
    )
    
    print("Medical prompts added successfully!")

if __name__ == "__main__":
    setup_medical_prompts()