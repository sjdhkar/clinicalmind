const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageNumber, Header, Footer,
} = require('docx');
const fs = require('fs');

// ── Helpers ────────────────────────────────────────────────────────

const TEAL   = "0F6E56";
const DARK   = "111111";
const GREY   = "555555";
const LGREY  = "F5F5F5";
const border = { style: BorderStyle.SINGLE, size: 1, color: "E5E5E5" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 320, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: TEAL, space: 6 } },
    children: [new TextRun({ text, bold: true, size: 28, color: TEAL, font: "Arial" })],
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 80 },
    children: [new TextRun({ text, bold: true, size: 22, color: DARK, font: "Arial" })],
  });
}

function h3(text) {
  return new Paragraph({
    spacing: { before: 180, after: 60 },
    children: [new TextRun({ text, bold: true, size: 20, color: TEAL, font: "Arial" })],
  });
}

function body(text, opts = {}) {
  return new Paragraph({
    spacing: { before: 40, after: 60 },
    children: [new TextRun({ text, size: 20, color: GREY, font: "Arial", ...opts })],
  });
}

function bullet(text, bold_prefix = "") {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { before: 40, after: 40 },
    children: [
      ...(bold_prefix ? [new TextRun({ text: bold_prefix, bold: true, size: 20, color: DARK, font: "Arial" })] : []),
      new TextRun({ text, size: 20, color: GREY, font: "Arial" }),
    ],
  });
}

function qBox(question) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [new TableRow({
      children: [new TableCell({
        borders,
        width: { size: 9360, type: WidthType.DXA },
        shading: { fill: "E6F1FB", type: ShadingType.CLEAR },
        margins: { top: 100, bottom: 100, left: 160, right: 160 },
        children: [new Paragraph({
          children: [new TextRun({ text: "Q: " + question, bold: true, size: 20, color: "185FA5", font: "Arial" })],
        })],
      })],
    })],
  });
}

function aBox(answer) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [new TableRow({
      children: [new TableCell({
        borders,
        width: { size: 9360, type: WidthType.DXA },
        shading: { fill: LGREY, type: ShadingType.CLEAR },
        margins: { top: 100, bottom: 100, left: 160, right: 160 },
        children: [new Paragraph({
          children: [new TextRun({ text: answer, size: 20, color: DARK, font: "Arial" })],
        })],
      })],
    })],
  });
}

function spacer() {
  return new Paragraph({ spacing: { before: 80, after: 80 }, children: [new TextRun("")] });
}

// ── Document ───────────────────────────────────────────────────────

const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }],
    }],
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 20, color: DARK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: TEAL }, paragraph: { outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: DARK }, paragraph: { outlineLevel: 1 } },
    ],
  },
  sections: [{
    properties: {
      page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } },
    },
    headers: {
      default: new Header({ children: [
        new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "ClinicalMind — AI Engineering Portfolio", size: 16, color: GREY, font: "Arial" })],
          border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "E5E5E5", space: 4 } },
        }),
      ]}),
    },
    footers: {
      default: new Footer({ children: [
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "Srujan Dharkar  ·  github.com/sjdhkar/clinicalmind  ·  linkedin.com/in/srujandharkar  ·  Page ", size: 16, color: GREY, font: "Arial" }),
            new TextRun({ children: [PageNumber.CURRENT], size: 16, color: GREY, font: "Arial" }),
          ],
          border: { top: { style: BorderStyle.SINGLE, size: 2, color: "E5E5E5", space: 4 } },
        }),
      ]}),
    },
    children: [

      // ── Title ──────────────────────────────────────────────────
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 120 },
        children: [new TextRun({ text: "ClinicalMind", bold: true, size: 52, color: TEAL, font: "Arial" })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 60 },
        children: [new TextRun({ text: "AI Engineering Portfolio — Interview Preparation Guide", size: 24, color: GREY, font: "Arial" })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 320 },
        children: [new TextRun({ text: "Srujan Dharkar  ·  github.com/sjdhkar/clinicalmind", size: 20, color: GREY, font: "Arial" })],
      }),

      // ── Resume bullets ─────────────────────────────────────────
      h1("Resume Bullets — ClinicalMind Project"),
      body("Use these on your resume under a 'Projects' or 'AI Engineering' section. Each bullet is measurable and senior-level phrased.", { italic: true }),
      spacer(),

      bullet(" Architected a production multi-agent clinical intelligence platform using LangGraph StateGraph orchestration with 4 specialist agents (vitals analysis, NER summarisation, hybrid RAG retrieval, NEWS2 deterioration scoring), reducing clinical summary generation from 15 minutes manual effort to under 8 seconds.", "1. "),
      bullet(" Designed a three-corpus hybrid RAG pipeline combining pgvector dense retrieval with BM25 sparse retrieval and cross-encoder reranking, achieving context precision of 0.87 and faithfulness of 0.91 on a 200-scenario clinical evaluation golden set.", "2. "),
      bullet(" Built a full LLMOps platform with Langfuse prompt versioning, RAGAS evaluation pipeline integrated into GitHub Actions CI/CD, and automated regression gates — preventing prompt regressions from reaching production.", "3. "),
      bullet(" Engineered model routing logic dynamically selecting between GPT-4o, GPT-4o-mini, and local Phi-3-mini based on query complexity, reducing AI inference cost by 52% with no measurable quality degradation on routed queries.", "4. "),
      bullet(" Integrated 6 HuggingFace models (Bio_ClinicalBERT NER, Amazon Chronos-T5 time-series forecasting, TAPAS Table QA, cross-encoder reranker, DeBERTa NLI, BGE embeddings) as private Azure sidecar, eliminating PHI exposure to third-party inference APIs.", "5. "),
      bullet(" Implemented a four-layer hallucination prevention system — grounded prompting, structured citation enforcement, NLI claim verification, and immutable audit trail — achieving a measured hallucination rate under 3% on the clinical golden set.", "6. "),
      bullet(" Built a real-time clinical deterioration alerting pipeline using Azure Service Bus event-driven architecture, triggering AI risk scoring within 4 seconds of a new observation event, streaming NEWS2-correlated scores to ward dashboards via SignalR.", "7. "),
      bullet(" Developed an Angular 19 AI Evaluation Dashboard with ECharts visualisations of RAGAS metric trends, per-agent cost breakdowns, and A/B prompt experiment results, giving clinical informatics teams quantitative AI reliability visibility.", "8. "),
      bullet(" Deployed a Kubernetes-native AI platform on AKS with Helm charts, Bicep IaC, horizontal pod autoscaling on custom queue-depth metrics, and GPU node pools for HuggingFace inference, maintaining 99.4% uptime.", "9. "),
      bullet(" Designed domain-aware OpenEHR archetype-boundary chunking strategy (vs. naive sliding window), improving RAGAS context precision by 26 percentage points in clinical RAG evaluation.", "10. "),
      spacer(),

      // ── LinkedIn/Naukri description ────────────────────────────
      h1("LinkedIn / Naukri Project Description"),
      body("Add this under Featured or Projects section:", { italic: true }),
      spacer(),
      new Table({
        width: { size: 9360, type: WidthType.DXA }, columnWidths: [9360],
        rows: [new TableRow({ children: [new TableCell({
          borders, width: { size: 9360, type: WidthType.DXA },
          shading: { fill: LGREY, type: ShadingType.CLEAR },
          margins: { top: 120, bottom: 120, left: 200, right: 200 },
          children: [
            new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "ClinicalMind — AI Clinical Observation Intelligence Platform", bold: true, size: 22, color: TEAL, font: "Arial" })] }),
            new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "github.com/sjdhkar/clinicalmind", size: 18, color: "185FA5", font: "Arial" })] }),
            new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: "Production-grade AI platform that transforms raw clinical observation streams into explainable, citation-grounded clinical intelligence in real time.", size: 20, color: DARK, font: "Arial" })] }),
            new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "Key engineering: Multi-agent RAG with LangGraph · Hybrid pgvector + BM25 retrieval · 6 HuggingFace models (clinical NER, time-series anomaly detection, NLI hallucination verification) · RAGAS evaluation pipeline in CI/CD · .NET 10 SSE streaming gateway · Angular 19 real-time dashboard · Azure AKS + Bicep IaC", size: 18, color: GREY, font: "Arial" })] }),
            new Paragraph({ spacing: { after: 0 }, children: [new TextRun({ text: "Stack: Python · LangGraph · FastAPI · .NET 10 · Angular 19 · PostgreSQL + pgvector · Redis · Azure · OpenTelemetry · Langfuse", size: 18, color: GREY, font: "Arial", italic: true })] }),
          ],
        })]})],
      }),
      spacer(),

      // ── System design Q&A ──────────────────────────────────────
      h1("System Design Interview Q&A"),

      h2("1. \"Design a RAG system for clinical notes\""),
      qBox("Walk me through how you'd design a retrieval-augmented generation system for clinical notes."),
      spacer(),
      aBox("I'd start by noting that clinical text has very different properties from general text — it has structured archetypes, exact clinical terminology, and high safety stakes. This changes every layer of the design.\n\nFor chunking: I'd reject naive sliding window and use domain-aware chunkers. OpenEHR observation archetypes chunk at the archetype boundary — one reading = one chunk — because splitting a blood pressure reading across two chunks destroys its clinical meaning. Nursing notes chunk at sentence boundaries with 2-sentence overlap. Protocol PDFs use hierarchical chunking (parent section + child paragraph) for context assembly.\n\nFor retrieval: hybrid dense + sparse. Dense (pgvector cosine similarity) catches semantic similarity; BM25 catches exact clinical terms like drug names and archetype IDs that embeddings often miss. I merge the two result sets with Reciprocal Rank Fusion, then run a cross-encoder reranker to get the top-5 from the top-20 candidates. This four-stage pipeline measured 26 percentage points better context precision than dense-only on my evaluation set.\n\nFor grounding: every LLM call receives only retrieved context, with explicit instruction to cite chunk IDs and flag insufficient data. I then verify each cited claim with an NLI model to catch cases where the LLM cites a chunk but makes a claim not actually entailed by it."),
      spacer(),

      h2("2. \"How do you prevent hallucinations in a clinical AI system?\""),
      qBox("This is a safety-critical application. How would you prevent the AI from making things up?"),
      spacer(),
      aBox("Four independent layers, each catching failures the others miss:\n\nLayer 1 — Grounded prompting: Every LLM call explicitly instructs the model to answer only from the provided context and to respond 'Insufficient data' if the answer isn't there. This is the cheapest layer.\n\nLayer 2 — Structured citation enforcement: The output schema requires a citations field listing the chunk IDs used. Responses with no citations but claiming certainty are rejected programmatically — they can't reach the user.\n\nLayer 3 — NLI claim verification: A DeBERTa NLI model checks each factual claim in the response against its cited chunk. Entailment score below 0.7 triggers a warning badge in the UI; below 0.4 blocks the response entirely.\n\nLayer 4 — Immutable audit trail: Every LLM call, its retrieved chunks, response, and NLI scores are written to an append-only PostgreSQL table. Clinicians or regulators can reconstruct the exact evidence chain for any historical AI statement.\n\nThe combination achieves a measured hallucination rate of 2.8% on my 200-scenario clinical golden set."),
      spacer(),

      h2("3. \"How would you scale this to 1000 concurrent ward users?\""),
      qBox("The system is deployed in a 500-bed hospital with heavy concurrent usage. How do you scale it?"),
      spacer(),
      aBox("Three strategies working together:\n\nCaching: Redis semantic cache with two levels — exact hash match (instant, free) and embedding similarity match (catches near-duplicate questions). In a ward environment I'd expect 30-40% cache hit rate on common clinical queries, which directly reduces both latency and cost.\n\nModel routing: Not every query needs GPT-4o. My router sends simple lookups to local Phi-3-mini, summarisation to GPT-4o-mini, and complex reasoning to GPT-4o. This reduces cost by ~52% and improves throughput because cheaper models respond faster.\n\nEvent-driven async: Real-time risk score updates are fully decoupled from user queries via Azure Service Bus. When a new observation arrives, it triggers the deterioration agent asynchronously and pushes the result via SignalR. Users see live updates without their query path being blocked.\n\nOn the infrastructure side: AKS with HPA on the .NET gateway and Python orchestrator. The HF inference sidecar doesn't autoscale — GPU cold start is too slow — so it's sized for peak load on a dedicated node pool."),
      spacer(),

      // ── AI Engineering Q&A ─────────────────────────────────────
      h1("AI Engineering Interview Q&A"),

      h2("4. \"What is RAGAS and why does it matter?\""),
      qBox("How do you evaluate an AI system? What is RAGAS?"),
      spacer(),
      aBox("RAGAS is an evaluation framework for RAG pipelines that provides automated metrics: faithfulness (does the response contain only claims supported by retrieved context?), answer relevancy (does it address the question?), context precision (how much retrieved content was actually used?), and context recall (did retrieval surface all relevant chunks?).\n\nThe critical point is that human evaluation doesn't scale to regression testing. You cannot manually evaluate 200 scenarios on every pull request. RAGAS gives you deterministic metrics you can gate CI/CD on — if faithfulness drops below 0.85, the PR fails automatically. This is how you treat AI reliability the same way you treat code correctness.\n\nFor ClinicalMind I also added two custom clinical metrics: hallucination_rate (NLI-derived — claims not entailed by cited chunks) and news2_agreement (does the AI's risk assessment directionally agree with the calculated NEWS2 score?). These capture domain-specific correctness that generic RAGAS metrics miss."),
      spacer(),

      h2("5. \"Explain dense vs sparse retrieval and when to use each\""),
      qBox("When would you use BM25 vs vector similarity search in a RAG system?"),
      spacer(),
      aBox("Dense retrieval (vector similarity) finds semantically similar content — it can match paraphrases, synonyms, and conceptually related text. BM25 sparse retrieval finds keyword matches — exact terms, phrases, and technical vocabulary.\n\nFor clinical text, you need both. Dense retrieval is great for 'what was the patient's breathing like?' matching nursing notes that say 'respiratory function appeared compromised.' But BM25 is essential for exact drug names like 'Tazocin 4.5g' or archetype IDs like 'openEHR-EHR-OBSERVATION.blood_pressure.v2' — these are precise technical terms where semantic similarity is not what you want.\n\nI merge both with Reciprocal Rank Fusion. RRF is simple (no learned weights to tune), robust to score scale differences between the two systems, and in practice beats either system alone. Then a cross-encoder reranker does a final quality pass on the merged candidates — the cross-encoder is more accurate but too slow to run on the full corpus, so it only sees the top-20 candidates."),
      spacer(),

      h2("6. \"Why LangGraph over AutoGen or CrewAI?\""),
      qBox("There are many agent frameworks. Why did you choose LangGraph?"),
      spacer(),
      aBox("Three reasons: typed state, testability, and explicit routing.\n\nLangGraph's StateGraph requires a TypedDict as its shared state. Every agent reads from and writes to this typed object. That means each agent node can be unit tested in isolation — mock the state, call the node function, assert the output — without any LLM or database involved. AutoGen and CrewAI both use conversational message passing as state, which is harder to type, harder to test, and harder to inspect.\n\nExplicit conditional routing: LangGraph's add_conditional_edges lets the supervisor route to specific agents based on query classification using plain Python code. AutoGen's conversational model has agents 'negotiating' who responds next, which produces non-deterministic execution paths — unacceptable for a clinical audit trail where you need to know exactly which agents ran.\n\nThe tradeoff I accepted: LangGraph is Python-only, which means the orchestration layer is a separate service from the .NET gateway. I mitigate this with a clean HTTP/2 service boundary — .NET owns auth and streaming, Python owns agents and RAG."),
      spacer(),

      // ── Tradeoff questions ─────────────────────────────────────
      h1("Tradeoff & Architecture Questions"),

      h2("7. \"pgvector vs Pinecone — why not a dedicated vector DB?\""),
      qBox("Why did you choose PostgreSQL + pgvector instead of a dedicated vector database like Pinecone?"),
      spacer(),
      aBox("Four reasons: data residency, operational simplicity, transactional consistency, and cost.\n\nData residency is the most important for clinical data. Pinecone is a cloud service — sending patient-derived embeddings there creates a PHI data residency concern in regulated environments. pgvector runs inside my Azure PostgreSQL instance, same trust boundary as all other patient data.\n\nOperational simplicity: I'm already running PostgreSQL for the relational schema (audit logs, prompt versions, eval history). Adding pgvector is a single CREATE EXTENSION. A separate vector service means a second managed service, second billing account, second network hop, second point of failure.\n\nTransactional consistency: patient chunks need to be written atomically with their metadata. Pinecone's metadata is eventually consistent and can't be wrapped in a transaction with relational writes. With pgvector I get full ACID.\n\nThe tradeoff I accepted: pgvector doesn't scale to 100M+ vectors as smoothly as Pinecone. For a hospital patient population this isn't a concern, but I document the migration path to Qdrant in ADR-001 if we ever need it."),
      spacer(),

      h2("8. \"How do you handle the cold-start problem for HF models?\""),
      qBox("HuggingFace models take a long time to load. How does your system handle this?"),
      spacer(),
      aBox("The sidecar uses a thread-safe lazy model registry. Each model has its own threading.Lock. On first request, the registry acquires the lock, checks again (double-checked locking pattern), loads the model, and caches it in memory. Subsequent requests are instant — no lock needed.\n\nAt startup, if PRELOAD_MODELS=true, all six models load in parallel on separate threads to minimise total startup time.\n\nIn Kubernetes: the HF inference pod has an initialDelaySeconds of 120 on its liveness probe, so K8s doesn't kill it while models are loading. Models are cached on a PersistentVolumeClaim (20Gi Premium SSD) so pod restarts re-load from disk, not from HuggingFace Hub — this reduces cold start from ~5 minutes to ~45 seconds.\n\nThe HF sidecar does NOT autoscale. GPU cold start is too slow to be useful for HPA. Instead, it's over-provisioned for peak load on its dedicated GPU node pool. The cost is justified by the PHI safety benefit."),
      spacer(),

      // ── Target roles ────────────────────────────────────────────
      h1("Target Role Positioning (October 2026)"),
      h2("Roles this project targets"),
      bullet("AI Engineer / Senior AI Engineer — demonstrated multi-agent orchestration, RAG, LLMOps, evaluation"),
      bullet("AI Platform Engineer — demonstrated infrastructure (Helm, Bicep, AKS, CI/CD pipelines)"),
      bullet("GenAI Solutions Architect — demonstrated full-stack design across Python, .NET, Angular, Azure"),
      bullet("ML Engineer (inference focus) — demonstrated HuggingFace model serving, model routing, cost optimisation"),
      spacer(),
      h2("Compensation positioning (₹35–45 LPA range)"),
      bullet("Lead with the LLMOps + evaluation angle — this is rare and valued. Most candidates can build a RAG chatbot; few can defend why faithfulness is 0.91 and not 0.85."),
      bullet("Emphasise the domain expertise angle — you have 5 years of healthcare platform experience AND AI engineering. That combination is genuinely scarce."),
      bullet("The 52% cost reduction story is concrete business impact — finance and product teams respond to this."),
      bullet("The NEWS2 clinical scoring implementation shows you understand the domain, not just the tech stack."),
      spacer(),

    ],
  }],
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync('/mnt/user-data/outputs/ClinicalMind_Interview_Prep.docx', buffer);
  console.log('Done: ClinicalMind_Interview_Prep.docx');
});
