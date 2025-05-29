# AlzRAG: A Specialized RAG System for Alzheimer's Research

## Overview

AlzRAG is a specialized Retrieval-Augmented Generation (RAG) system designed specifically for Alzheimer's disease research and clinical information. Built on top of the powerful R2R (Retrieval to Riches) framework, AlzRAG enhances the medical research experience by providing context-aware, evidence-based responses to complex queries about Alzheimer's disease, treatments, research findings, and clinical information.

## Features

- **Specialized Medical Knowledge Graph**: Optimized for Alzheimer's research with entity extraction focused on medical terminology, treatments, and research findings
- **Context-Enriched Chunks**: Enhanced document chunking with medical context preservation
- **Alzheimer's-Specific Hybrid Search**: Optimized vector and semantic search for medical terminology and concepts
- **Citation-Based Responses**: All generated content includes citations to original research papers and clinical guidelines
- **Multi-Modal Support**: Process and analyze text, images (MRIs, PET scans), and structured clinical data
- **Interactive Visualization**: Graph-based exploration of research connections and treatment pathways

## API Usage Examples

### Basic Health Query

Query the system for general medical advice:

```bash
curl -X POST "http://jovana.openbrain.io/v3/retrieval/agent" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {"role": "user", "content": "I have a fever of 102°F and headache. What should I do?"}, 
    "search_settings": {"use_semantic_search": true}
  }'
```

**Response Example:**
```json
{
  "results": {
    "messages": [{
      "role": "assistant",
      "content": "I'm not a doctor, but here are some general steps you can take if you have a fever and headache:\n\n1. **Stay Hydrated:** Drink plenty of fluids such as water, herbal teas, or clear broths to stay hydrated.\n\n2. **Rest:** Ensure you get plenty of rest to help your body fight off any infection.\n\n3. **Over-the-Counter Medication:** Consider taking over-the-counter medications like acetaminophen or ibuprofen to help reduce fever and alleviate headache pain. Follow the dosage instructions on the package.\n\n4. **Cool Compress:** Apply a cool, damp cloth to your forehead to help reduce fever.\n\n5. **Monitor Symptoms:** Keep an eye on your symptoms. If your fever persists for more than a couple of days, or if you experience severe symptoms, it's important to seek medical attention.\n\n6. **Consult a Healthcare Provider:** If you have any concerns or if your symptoms worsen, contact a healthcare provider for advice tailored to your specific situation.\n\nRemember, these are general suggestions, and it's always best to consult with a healthcare professional for medical advice."
    }],
    "conversation_id": "8ecb7a26-2783-4a94-b03e-584f536feae9"
  }
}
```

### EHR Patient Data Query

Query specific patient information from Electronic Health Records:

```bash
curl -X POST "http://jovana.openbrain.io/v3/retrieval/agent" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {"role": "user", "content": "patient P001"}, 
    "search_settings": {
      "filters": {"collection_id": {"$eq": "4086e0e7-4b95-45a8-9bf6-149a08b9f0ed"}}, 
      "use_semantic_search": true
    }, 
    "selectedAgent": "ehr_agent"
  }'
```

**Response Example:**
```json
{
  "results": {
    "messages": [{
      "role": "assistant",
      "content": "**Patient Demographics:**\n- Patient ID: P001\n- Age: Not specified\n- Gender: Not specified\n\n**Problems (Conditions):**\n- General Fatigue (2021)\n- Minor Injury (2019)\n- Flu Symptoms (2017)\n\n**Medications:**\n- Lisinopril: Dosage and frequency not specified\n- Ibuprofen: Dosage and frequency not specified\n- Metformin: Dosage and frequency not specified\n\n**Vital Signs:**\n- Systolic BP: Not specified\n- Diastolic BP: Not specified\n\n**Diagnostic Results:**\n- HbA1c: 7.8% (2022), 5.8% (2020)\n- Glucose: 8.3 mmol/L (2022), 5.5 mmol/L (2020)\n- Cholesterol: 6.0 mmol/L (2022), 5.4 mmol/L (2020)\n- CRP: 1.0 mg/L (2021)\n- WBC: 8.1 x 10^9/L (2021)\n\n**Plan of Care:**\n- Routine checkups with advice to maintain a healthy lifestyle\n- Sleep hygiene recommendations for fatigue\n- Wound care and tetanus status review for minor injuries\n\n**Note:**\n- No imaging ordered for any encounters\n- No data provided for Allergies and Intolerances, Immunizations, Procedures, Medical Devices, Social History, Functional Status"
    }],
    "conversation_id": "a4930a7a-cdfd-483a-93bf-640ab756278c"
  }
}
```

### Additional Query Examples

**Medication Interaction Check:**
```bash
curl -X POST "http://jovana.openbrain.io/v3/retrieval/agent" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {"role": "user", "content": "Can I take ibuprofen with my blood pressure medication?"}, 
    "search_settings": {"use_semantic_search": true}
  }'
```

**Emergency Situation Assessment:**
```bash
curl -X POST "http://jovana.openbrain.io/v3/retrieval/agent" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {"role": "user", "content": "Someone is having chest pain and difficulty breathing. Should I call 911?"}, 
    "search_settings": {"use_semantic_search": true}
  }'
```

**Alzheimer's Research Query:**
```bash
curl -X POST "http://jovana.openbrain.io/v3/retrieval/agent" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {"role": "user", "content": "What are the latest treatments for tau protein accumulation in Alzheimer's disease?"}, 
    "search_settings": {"use_semantic_search": true}
  }'
```
### Prerequisites

- Python 3.8+
- Docker
- 8GB RAM minimum (16GB recommended)
- OpenAI API key or compatible LLM provider

### Installation

```bash
# Clone the repository
git clone https://github.com/ChatMED/AlzRAG.git
cd AlzRAG

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# Start the server using standard R2R commands
r2r serve --docker
```

### Quick Usage

```python
from alzrag import AlzRAGClient

# Initialize client
client = AlzRAGClient("http://localhost:7272")

# Authenticate
client.login("your-username", "your-password")

# Perform RAG query
response = client.query(
    "What are the latest advancements in tau protein targeting therapies?",
    search_mode="advanced",
    include_citations=True
)

# Display response
print(response.answer)
print("\nCitations:")
for citation in response.citations:
    print(f"- {citation.source}: {citation.title} ({citation.year})")
```

## Key Components

### 1. Medical Knowledge Graph

The AlzRAG system builds specialized knowledge graphs that capture the complex relationships between:

- Medications and treatments
- Proteins and biomarkers
- Clinical symptoms and progression patterns
- Research findings and clinical trials
- Genetic factors and risk associations

### 2. Enhanced GraphRAG for Medical Literature

Our implementation extends the R2R GraphRAG capabilities with:

- Medical entity recognition and normalization
- Automated extraction of clinical evidence levels
- Treatment efficacy summarization
- Patient cohort characteristic analysis
- Temporal disease progression modeling

### 3. Medical Image Analysis Integration

AlzRAG can process and incorporate findings from:

- MRI brain scans
- PET amyloid and tau imaging
- Structural brain measurements
- Longitudinal imaging changes

## Use Cases

- **Clinical Decision Support**: Evidence-based treatment recommendations with recent research backing
- **Research Discovery**: Identify connection patterns across disparate research papers
- **Patient Education**: Generate accessible explanations of complex medical concepts
- **Clinical Trial Matching**: Connect research findings with ongoing clinical trials
- **Hypothesis Generation**: Discover potential research directions by analyzing knowledge graph patterns

## Documentation

For complete documentation, visit [https://alzrag.chatmed.ai/docs](https://example.com)

## Configuration

AlzRAG extends the standard R2R configuration with medical-specific settings. Configure your environment by modifying the standard R2R config files or using environment variables:

```bash
# Set up R2R with medical-specific models
export OPENAI_API_KEY=your-api-key
export R2R_EMBEDDING_MODEL=text-embedding-3-small
export R2R_COMPLETION_MODEL=gpt-4o

# Start with specialized configuration
r2r serve --docker --full
```

Example configuration settings you might adjust for medical applications:

- Enhanced chunk enrichment for medical terminology
- Medical entity extraction patterns
- Knowledge graph settings optimized for biomedical relationships
- Custom prompts for clinical information synthesis

## Contributing

We welcome contributions from researchers, developers, and healthcare professionals. Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and submission process.

## Acknowledgments

AlzRAG is built upon the excellent R2R (Retrieval to Riches) framework. We extend our sincere gratitude to the R2R community for developing such a powerful and flexible RAG platform that enabled us to create this specialized medical application. Special thanks to:

- The entire R2R development team for their innovative approach to knowledge graph extraction and advanced RAG techniques
- The open-source contributors who have enhanced R2R's capabilities
- The SciPhi team for their documentation and support

## Citation

If you use AlzRAG in your research, please cite:

```bibtex
@software{chatmed_alzrag_2025,
  author = {Dobreva, Jovana and ChatMED Team},
  title = {AlzRAG: A Specialized RAG System for Alzheimer's Research},
  url = {https://github.com/ChatMED/AlzRAG},
  version = {1.0.0},
  year = {2025}
}
```

