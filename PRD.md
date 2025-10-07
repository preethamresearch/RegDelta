RegDelta (Local) — Product Requirements Document (PRD)

1. Vision & Outcome

Turn incoming regulatory updates (RBI/SEBI/PCI/ISO/SOC2/GDPR, etc.) into a reviewable impact plan in < 30 minutes, fully local (no external LLM/API).
Outcome: A vetted list of obligations mapped to internal controls with owner-ready actions and evidence cadence, plus an audit trail.

2. Scope (MVP)

In scope

Document Ingestion & Baselines

Upload PDFs or drop into watched folders.

Tag by Scenario (e.g., “PCI 4.0 → 4.0.1”, “RBI KYC 2024 → 2025”).

Maintain baseline vs. new version.

Diff & Sectioning

Paragraph/section segmentation with stable section IDs.

Diff ops: equal / insert / delete / replace, with summary counts.

Obligation Extraction (Deterministic)

Rule/lexicon-based detection of obligations (modal verbs: must/shall/required/prohibited/etc.).

Severity heuristic (High/Medium/Low) via keywords and deadline patterns.

Output: {section_id, text, severity, citations[]}.

Control Mapping (Local Intelligence)

Local embeddings (SentenceTransformers) + FAISS index over control catalog.

Blended score: 0.7 _ cosine + 0.3 _ fuzzy_token_ratio.

Reviewer can accept/override/reject matches; store reviewer + comments.

Action & Evidence Planning

From accepted mappings & gaps, generate actions (summary, owner, due).

Define evidence cadence (cron-like) with artefact hints and next run date.

Auditability & Exports

Append-only JSONL audit with SHA-256 hash chain (tamper-evident).

Export Obligations, Mappings, Plan as CSV/JSON.

One-click Scenario Report (summary + tables).

Dataset Ops

YAML-driven fetcher (download public PDFs to scenario folders).

Folder watcher to auto-refresh the app.

UI Scenario filter.

Out of scope (for MVP): SSO/RBAC, OCR for image-only PDFs, external LLMs, complex generative writing, enterprise ticketing beyond simple webhooks.

3. Success Metrics

Time-to-Impact Plan: < 30 min per new circular.

Mapping Top-1 Precision: ≥ 0.8 on a human-validated golden set.

Coverage: ≥ 90% obligations mapped or flagged for review.

Audit Completeness: 100% state changes recorded.

4. Users & Jobs-to-Be-Done

GRC/Compliance Lead: Understand what changed; approve mappings & actions.

Control Owner: Receive precise, scoped tasks and evidence schedule.

Internal Auditor: Verify traceability (regulation → obligation → control → evidence).

5. Agentic Operating Model (Local, No Cloud LLMs)

Planner Agent: Orchestrates stages: ingest → diff → extract → map → plan → export; logs every step.

Extractor Agent: Applies rules/lexicon; outputs obligations deterministically.

Mapper Agent: Builds/loads vector index; returns top-k with blended scores.

Verifier Agent: Applies thresholds, enforces reviewer acknowledgement, writes audit.

Planner/Actions Agent: Converts diffs & mappings into actions and evidence cadences.

Agents are lightweight Python services/functions with clear tool interfaces (see §10).

6. Functional Requirements (FR)
   FR-1 Document & Data Handling

FR-1.1 Ingest PDFs; extract text (PyMuPDF preferred; fallback pdfplumber).

FR-1.2 Segment into paragraphs/sections; preserve numbering & headings.

FR-1.3 Group artifacts under Scenario; baseline/new buckets.

FR-2 Diff

FR-2.1 Compute paragraph-level diff (opcodes: equal/insert/delete/replace).

FR-2.2 Show summary counts and section-aware navigation.

FR-3 Obligation Extraction

FR-3.1 Rule-based detection using lexicon (configurable YAML).

FR-3.2 Severity heuristic via keywords (e.g., “prohibited”, “within N days”, “penalty”).

FR-3.3 Output includes {section_id, text, severity, citations[]}.

FR-4 Control Mapping

FR-4.1 Local embeddings (CPU) and FAISS index; no remote calls.

FR-4.2 Score blend: 0.7*cosine + 0.3*fuzzy_token_ratio.

FR-4.3 Threshold gates: auto ≥ T_high, review if T_low–T_high.

FR-4.4 Accept/override/reject with reviewer name, comment, timestamp.

FR-5 Action & Evidence Planning

FR-5.1 Suggest actions for changed/unmapped obligations.

FR-5.2 Evidence schedule fields: artefact, owner, cadence_cron, next_run_at.

FR-5.3 Optional webhooks (Slack/email) for reminders.

FR-6 Audit & Export

FR-6.1 Append-only JSONL audit with SHA-256 hash chain.

FR-6.2 Export obligations, mappings, actions/evidence as CSV/JSON.

FR-6.3 Downloadable Scenario Report.

FR-7 Dataset Ops

FR-7.1 YAML scenarios[] with PDF URLs → saved to folders.

FR-7.2 Folder watcher touchfile triggers UI refresh.

FR-7.3 Scenario filter limits visible baselines/new docs.

7. Non-Functional Requirements (NFR)

Privacy: 100% local; no external LLM/API.

Performance: For 200–300 paragraphs: diff < 2s; mapping < 5s on CPU after warmup.

Portability: Windows/macOS/Linux; Python ≥ 3.10 (PyMuPDF optional).

Resilience: Automatic extraction fallback; clear error banners.

Observability: In-app logs for fetch/diff/map; audit export.

Extensibility: Pluggable lexicons, control catalogs, scenario sources.

8. Data Model (Logical)

Documents
{ id, scenario, bucket(baseline|new), title, path, sha256, created_at }

Sections
{ id, document_id, section_id, text, text_hash }

Obligations
{ id, document_id, section_id, text, severity(H/M/L), citations[] }

Controls
{ control_id, domain, title, description, evidence_examples[], owner }

Mappings
{ id, obligation_id, control_id, score, status(accepted|review|rejected), reviewer, comment, ts }

Actions
{ id, mapping_id, summary, owner, due, system, external_ref }

EvidenceRuns
{ id, control_id, artefact, owner, cadence_cron, next_run_at, status }

Audit
{ ts, actor, action, payload_json, sha256, prev_sha256 }

9. Configurability

Lexicon YAML: modal phrases, severity keywords, stop-phrases.

Controls YAML: one or more catalogs (PCI/ISO/SOC2/GDPR/RBI/SEBI).

Thresholds: T_high, T_low for auto/needs-review gates.

Scenario YAML: scenario name + list of document URLs (baseline/new).

Policy YAML (later): default action templates & evidence artefact hints.

10. Tool Interfaces (for Agent Orchestration)

extract_text(pdf_path) -> str

paragraphize(text) -> List[str]

diff(old_paras, new_paras) -> List[{op, old_span, new_span}]

extract_obligations(section_text, section_id, lexicon) -> List[Obligation]

build_control_index(ids, texts) -> IndexHandle

search_controls(index, query_text, k) -> List[(control_id, cosine_score)]

blend_score(cosine, query_text, control_text) -> float

generate_actions(obligations, mappings, policy) -> List[Action]

schedule_evidence(runs[]) -> None

audit_log(actor, action, payload) -> None

export_csv(rows, schema, path) -> str

Keep signatures small and deterministic so agentic builders can compose them reliably.

11. UI/UX (Baseline)

Global: Dark theme; three metric tiles (Baseline PDFs | New PDFs | Controls).
Sidebar: Fetch real circulars (from YAML), Reload data, Scenario picker, helper text.
Main CTA: Run Diff • Extract • Map

Diff Summary: table of opcodes + section navigation.

Obligations: sortable table (severity filter), link to section snippet.

Control Mapping: top-k with scores; actions Accept / Override / Reject.

(Optional tab) Action & Evidence plan preview.

Exports: buttons for CSV/JSON report.

12. Milestones (PoC → Alpha → Beta → v1)

PoC (2–3 days): Ingest, diff, obligations, mapping (top-k), exports, dark UI, scenario picker.

Alpha (Week 2): Accept/override UI; action generator; evidence cadence; audit log; fetcher + watcher.

Beta (Weeks 3–4): Webhooks; scenario report; multi-catalog controls; golden-set metrics dashboard.

v1 (Month 2): SQLite storage; OCR fallback; catalog importers; optional Jira/GitHub issues (toggle & dry-run).

13. Risks & Mitigations

PDF variability: dual extractor; OCR phase later.

Extraction noise: tune lexicon; stop-phrases; reviewer checkpoints.

Mapping errors: conservative thresholds, low-confidence queue.

Windows installs: rely on pdfplumber fallback; document Py3.12 tip for PyMuPDF.

14. Acceptance Criteria (Stage Gates)

PoC: Runs offline; produces obligations & top-k mappings on 2–3 scenarios; CSV exports; ≤10s end-to-end on typical doc.

Alpha: Review actions saved; evidence cadence persisted; audit log verifiable.

Beta: Golden-set top-1 ≥ 0.8; scenario report downloadable; webhooks functional.

v1: SQLite, OCR fallback, catalog importers, optional issue creation.

15. Glossary

Scenario: Named comparison set (e.g., PCI 4.0 → 4.0.1).

Obligation: Requirement sentence containing a modal duty.

Control: Internal safeguard/policy/practice satisfying an obligation.

Evidence: Artefact proving control operation (logs, configs, screenshots).
