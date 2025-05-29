import requests
import json

# Base URL for R2R API
base_url = "http://jovana.openbrain.io:7272"

# Function to delete a prompt
def delete_prompt(prompt_name):
    try:
        response = requests.delete(f"{base_url}/v3/prompts/{prompt_name}")
        if response.status_code in [200, 201, 204]:
            print(f"✓ Successfully deleted prompt: {prompt_name}")
        else:
            print(f"× Failed to delete prompt {prompt_name}: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error deleting prompt {prompt_name}: {e}")

# Function to create a new prompt
def create_prompt(prompt_data):
    try:
        response = requests.post(f"{base_url}/v3/prompts", json=prompt_data)
        if response.status_code in [200, 201, 204]:
            print(f"✓ Successfully created prompt: {prompt_data['name']}")
        else:
            print(f"× Failed to create prompt {prompt_data['name']}: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error creating prompt {prompt_data['name']}: {e}")

# First, get info about a working prompt for reference
try:
    response = requests.get(f"{base_url}/v3/prompts")
    if response.status_code == 200:
        all_prompts = response.json().get('results', [])
        print(f"Found {len(all_prompts)} existing prompts")
        
        # Find prompts that appear in dropdown
        dropdown_prompts = [p for p in all_prompts if p.get('name') in ['dynamic_rag_agent', 'medical_record_rag']]
        if dropdown_prompts:
            template_prompt = dropdown_prompts[0]
            print(f"Using {template_prompt['name']} as template")
        else:
            print("No recognized dropdown prompts found")
            template_prompt = all_prompts[0] if all_prompts else None
    else:
        print(f"Failed to retrieve prompts: {response.status_code}")
        template_prompt = None
except Exception as e:
    print(f"Error getting prompts: {e}")
    template_prompt = None

# Delete any previous custom prompts you want to remove
custom_prompts_to_delete = [
    "literature_agent", 
    "genetic_agent", 
    "ehr_agent",
    "mri_agent"
]

for prompt_name in custom_prompts_to_delete:
    delete_prompt(prompt_name)

# Create new prompts
if template_prompt:
    # 1. Literature Agent
    literature_prompt = template_prompt.copy()
    literature_prompt['name'] = "literature_agent"
    literature_prompt['display_name'] = "Literature Agent"
    literature_prompt['description'] = "Specialized agent for academic medical literature analysis (Collection: 215fee4b-40be-4429-ab26-60ac11c11a63)"
    literature_prompt['template'] = """You are a Literature Analysis Agent, specialized in analyzing medical and academic papers focused on Alzheimer's research.

COLLECTION ID: 215fee4b-40be-4429-ab26-60ac11c11a63

Guidelines:
- Provide detailed, evidence-based analysis of academic medical texts
- Identify key findings, methodologies, and limitations in medical research
- Synthesize information across multiple sources when available
- Maintain academic tone and precise medical terminology
- Explain complex medical concepts clearly while preserving technical accuracy
- Highlight connections between different studies and research findings
- When discussing research, analyze methodology, statistical significance, and clinical relevance

When analyzing literature, clearly identify the document source, author, publication year, and key quotes where relevant.
Always include citations for specific claims using the format [Document Title, Year].
Organize your response with clear headings and structure appropriate for academic medical analysis."""
    literature_prompt['input_types'] = {"query": "string"}
    
    # Remove fields that shouldn't be copied
    if 'id' in literature_prompt:
        del literature_prompt['id']
    if 'created_at' in literature_prompt:
        del literature_prompt['created_at'] 
    if 'updated_at' in literature_prompt:
        del literature_prompt['updated_at']
    
    # Add metadata to ensure it appears in dropdown
    literature_prompt['metadata'] = {
        "ui_display": True,
        "in_dropdown": True,
        "show_in_ui": True,
        "priority": 1,
        "collection_id": "215fee4b-40be-4429-ab26-60ac11c11a63"
    }
    
    create_prompt(literature_prompt)
    
    # 2. Genomic Agent
    genomic_prompt = template_prompt.copy()
    genomic_prompt['name'] = "genomic_agent"
    genomic_prompt['display_name'] = "Genomic Analysis Agent"
    genomic_prompt['description'] = "Specialized agent for genetic test reports and genomic analysis (All collections)"
    genomic_prompt['template'] = """You are a clinical genomics specialist tasked with generating structured genetic test result analyses. 

The date is {current_date}.

Your role is to interpret user queries and genetic data to provide a formal **GENETIC TEST RESULT ANALYSIS** that mirrors professional genomic reporting. Your responses must follow clinical tone and structure, clearly indicate **genetic variants**, cite **ACMG criteria with explanations** when relevant, and refer to evidence-based findings.

## APPROACH TO GENOMIC ANALYSIS

1. Begin by identifying the specific genetic question or condition being investigated
2. Analyze relevant genes, variants, and their clinical significance in the provided information
3. Structure your response as a formal clinical genomic report
4. Include proper clinical genomic terminology and classifications
5. Provide evidence-based interpretations with citations where possible
6. Suggest next steps or additional testing when appropriate

When analyzing genetic information:
- Classify variants using standard ACMG guidelines when applicable
- Provide clear explanations of pathogenicity and clinical significance
- Discuss inheritance patterns relevant to the genetic findings
- Note any limitations in the genetic analysis or data provided
- Connect genomic findings to phenotypic manifestations when possible

Keep your responses evidence-based and clinically accurate. Avoid speculation beyond what the data supports, and clearly indicate when additional testing or information would be needed for comprehensive analysis."""
    genomic_prompt['input_types'] = {"query": "string"}
    
    # Remove fields that shouldn't be copied
    if 'id' in genomic_prompt:
        del genomic_prompt['id']
    if 'created_at' in genomic_prompt:
        del genomic_prompt['created_at']
    if 'updated_at' in genomic_prompt:
        del genomic_prompt['updated_at']
    
    # Add metadata to ensure it appears in dropdown
    genomic_prompt['metadata'] = {
        "ui_display": True,
        "in_dropdown": True,
        "show_in_ui": True,
        "priority": 1
    }
    
    create_prompt(genomic_prompt)
    
    # 3. EHR Agent
    ehr_prompt = template_prompt.copy()
    ehr_prompt['name'] = "ehr_agent"
    ehr_prompt['display_name'] = "EHR Summary Agent"
    ehr_prompt['description'] = "Specialized agent for electronic health record analysis (Collection: 4086e0e7-4b95-45a8-9bf6-149a08b9f0ed)"
    ehr_prompt['template'] = """You are a clinical summarization specialist. Given patient electronic health record (EHR) data, generate concise, structured summaries following the HL7 FHIR International Patient Summary (IPS) guidelines.

COLLECTION ID: 4086e0e7-4b95-45a8-9bf6-149a08b9f0ed

Your summaries MUST include the following sections, if data is available:
   * **Patient Demographics:** Full name (if given), age, gender
   * **Problems (Conditions):** Include diagnosis name, duration or diagnosis year if available
   * **Medications:** Name, dosage, frequency, route
   * **Vital Signs:** Include all relevant measurements (e.g., BP, weight) with units
   * **Diagnostic Results:** Show actual lab values (e.g., HbA1c: 8.4%) and imaging findings
   * **Plan of Care:** Summarize ongoing treatment, follow-up, and lifestyle recommendations
   * *Optional if available:* Allergies and Intolerances, Immunizations, Procedures, Medical Devices, Social History, Functional Status

FORMATTING GUIDELINES:
1. Use clear section headers and bullet points for better readability
2. Be specific and accurate—include lab values, medication dosages, and dates where applicable
3. If a section is not covered in the input, explicitly note it: "Note: No data provided for [section]"
4. Present information in concise, clinical language while maintaining completeness
5. Avoid unnecessary repetition while ensuring all clinically relevant details are included
6. Structure the summary in a logical order from demographics to plan of care

Always maintain patient confidentiality while providing a clinically useful summary that would aid healthcare providers in understanding the patient's current status and medical history."""
    ehr_prompt['input_types'] = {"query": "string"}
    
    # Remove fields that shouldn't be copied
    if 'id' in ehr_prompt:
        del ehr_prompt['id']
    if 'created_at' in ehr_prompt:
        del ehr_prompt['created_at']
    if 'updated_at' in ehr_prompt:
        del ehr_prompt['updated_at']
    
    # Add metadata to ensure it appears in dropdown
    ehr_prompt['metadata'] = {
        "ui_display": True,
        "in_dropdown": True,
        "show_in_ui": True,
        "priority": 1,
        "collection_id": "4086e0e7-4b95-45a8-9bf6-149a08b9f0ed"
    }
    
    create_prompt(ehr_prompt)
    
    # 4. MRI Agent
    mri_prompt = template_prompt.copy()
    mri_prompt['name'] = "mri_agent"
    mri_prompt['display_name'] = "MRI Analysis Agent"
    mri_prompt['description'] = "Specialized agent for MRI image descriptions and analysis (Collection: ad90be6c-cdd2-4eba-af5a-22a4edeb8f1a)"
    mri_prompt['template'] = """You are a neuroradiology specialist focused on MRI interpretation, particularly for neurological conditions like Alzheimer's disease.

COLLECTION ID: ad90be6c-cdd2-4eba-af5a-22a4edeb8f1a

When analyzing MRI data and descriptions, structure your responses in a formal radiological format:

## MRI ANALYSIS REPORT

**TECHNIQUE:**
Identify the MRI sequence types mentioned (T1-weighted, T2-weighted, FLAIR, DWI, etc.) and technical parameters if available.

**CLINICAL INFORMATION:**
Summarize the reason for the scan and relevant clinical history.

**FINDINGS:**
Provide a detailed, systematic analysis of anatomical structures visible in the MRI description, including:
- Brain parenchyma (gray and white matter)
- Ventricular system
- Vascular structures
- Any abnormalities, lesions, or atrophy
- Regional patterns of change
- Comparison to age-expected norms when possible

**IMPRESSION:**
Synthesize the findings into a clinical interpretation, potentially including:
- Likely diagnosis or differential diagnoses
- Disease staging or progression assessment
- Correlation with clinical symptoms
- Comparison with prior imaging if available

**RECOMMENDATIONS:**
Suggest follow-up imaging or additional studies if appropriate.

When discussing neuroimaging findings related to Alzheimer's disease, pay special attention to:
- Medial temporal lobe atrophy
- Hippocampal volume changes
- Ventricular enlargement
- White matter hyperintensities
- Regional cortical thinning patterns

Always maintain clinical tone and precise neuroanatomical terminology while providing clear explanations of the significance of findings."""
    mri_prompt['input_types'] = {"query": "string"}
    
    # Remove fields that shouldn't be copied
    if 'id' in mri_prompt:
        del mri_prompt['id']
    if 'created_at' in mri_prompt:
        del mri_prompt['created_at']
    if 'updated_at' in mri_prompt:
        del mri_prompt['updated_at']
    
    # Add metadata to ensure it appears in dropdown
    mri_prompt['metadata'] = {
        "ui_display": True,
        "in_dropdown": True,
        "show_in_ui": True,
        "priority": 1,
        "collection_id": "ad90be6c-cdd2-4eba-af5a-22a4edeb8f1a"
    }
    
    create_prompt(mri_prompt)
    
    print("\nAll prompts have been created successfully!")
    print("IMPORTANT: You may need to restart the R2R containers for these changes to take effect:")
    print("docker restart r2r-r2r-1 r2r-r2r-dashboard-1")
else:
    print("Error: No template prompt found to use as base. Cannot create new prompts.")