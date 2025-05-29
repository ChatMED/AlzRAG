window.__RUNTIME_CONFIG__ = {
  NEXT_PUBLIC_R2R_DEPLOYMENT_URL: 'http://jovana.openbrain.io:7272/v3',
  R2R_DASHBOARD_DISABLE_TELEMETRY: '',
  SUPABASE_URL: '',
  SUPABASE_ANON_KEY: '',
  NEXT_PUBLIC_HATCHET_DASHBOARD_URL: '',
  NEXT_PUBLIC_UI_CONFIG: JSON.stringify({
    prompt_templates: {
      rag_options: [
        {
          id: "alzrag_research",
          name: "AlzRAG Research",
          description: "General Alzheimer's research and literature analysis",
          icon: "book",
          color: "#4285F4",
          category: "Research"
        },
        {
          id: "alzrag_clinical",
          name: "AlzRAG Clinical",
          description: "MRI analysis and clinical applications for Alzheimer's",
          icon: "hospital",
          color: "#34A853",
          category: "Clinical"
        }
      ],
      default_rag: "alzrag_research"
    }
  }),
};
