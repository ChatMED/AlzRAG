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

## Getting Started

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

