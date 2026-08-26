# A Governance-Centred, Persian-First Architecture for Enterprise Knowledge Capture and Retrieval-Augmented Generation

**Author:** Mohammad Mirashe  
**Affiliation:** Independent Researcher  
**Correspondence:** Please use the repository's GitHub Issues page  
**Article type:** Design-science research article / technical research manuscript  
**Artifact version:** Enterprise Knowledge Platform v0.9.0

## Abstract

Enterprise knowledge-management systems frequently fail at the boundary between human experience and computational retrieval. Conventional repositories privilege documents over situated expertise, while contemporary generative artificial intelligence systems can produce fluent responses without preserving provenance, review status, organizational ownership, or access constraints. These limitations are amplified in Persian-language environments, where right-to-left interaction, heterogeneous document formats, multilingual technical terminology, and comparatively limited language resources complicate both knowledge capture and semantic retrieval. This article presents the design of a governance-centred, Persian-first enterprise knowledge platform that integrates structured knowledge elicitation, document ingestion, human review, versioning, lightweight knowledge-graph construction, multilingual dense retrieval, and retrieval-augmented generation (RAG). The artifact operationalizes knowledge as a governed lifecycle rather than an undifferentiated corpus: knowledge is captured, evaluated across completeness, quality, evidence, and confidence dimensions, submitted for review, published, indexed, retrieved, and periodically reconsidered. A design-science methodology is used to articulate the problem, derive design requirements, instantiate the artifact, and define an evaluation programme. The implemented prototype uses FastAPI, Streamlit, SQLite, multilingual sentence embeddings, and FAISS, while maintaining a modular boundary around the language-model provider. Fourteen automated tests verify core extraction, persistence, graph, publication, API, demo, and Persian PDF behaviours; these tests establish technical consistency but do not constitute evidence of organizational effectiveness. Accordingly, the article specifies a rigorous future evaluation combining retrieval benchmarks, grounded-answer assessment, controlled user studies, governance audits, and longitudinal measures of knowledge reuse. The central contribution is a socio-technical design proposition: enterprise RAG becomes more trustworthy when retrieval eligibility is treated as the downstream consequence of explicit knowledge governance, rather than as a property of document availability alone.

**Keywords:** enterprise knowledge management; retrieval-augmented generation; Persian natural language processing; knowledge governance; tacit knowledge; semantic retrieval; design science; human-in-the-loop artificial intelligence

## 1. Introduction

Organizations do not suffer merely from an absence of information. They suffer from the inability to transform distributed, contextual, and partially tacit experience into knowledge that is discoverable, reviewable, attributable, and reusable. Technical reports, lessons learned, policies, decisions, maintenance records, and procedural explanations are often distributed across personal archives and operational systems. Even where a document repository exists, retrieval commonly depends on filenames, inconsistent metadata, or the memory of experienced personnel. The problem is therefore not reducible to storage. It concerns the conversion of situated experience into an organizational object whose meaning, authority, provenance, and lifecycle remain intelligible.

The problem has acquired new urgency with the diffusion of large language models (LLMs). Retrieval-augmented generation combines parametric generation with non-parametric external memory, enabling a model to condition its answer on retrieved sources rather than relying exclusively on learned parameters (Lewis et al., 2020). Yet an enterprise RAG system inherits the epistemic quality and governance defects of its corpus. If drafts, obsolete procedures, unreviewed claims, or confidential material are indiscriminately indexed, retrieval can amplify rather than resolve organizational risk. A semantically relevant passage is not necessarily an authorized, current, or sufficiently evidenced passage.

Persian-language organizations encounter additional constraints. Their records may contain Persian prose, English acronyms, Latin equipment identifiers, Persian and Arabic character variants, scanned images, and right-to-left layouts within a single knowledge object. A system designed around English-only assumptions may preserve the bytes of such documents while degrading their searchability, presentation, and organizational usability. Research on Persian language models has likewise demonstrated that language-specific modelling can outperform generic multilingual baselines on Persian understanding tasks, reinforcing the importance of treating language as an architectural concern rather than a cosmetic interface feature (Farahani et al., 2020).

This article describes and theorizes an implemented artifact, the Enterprise Knowledge Platform v0.9.0, whose purpose is to connect knowledge capture with governed semantic retrieval. The article asks how a lightweight platform can support the transition from heterogeneous human and documentary input to reviewed organizational knowledge and, subsequently, to grounded generative assistance. It makes three contributions. First, it develops a lifecycle architecture in which capture, evaluation, review, publication, indexing, and retrieval are explicitly coupled. Second, it proposes an interpretable multidimensional assessment model that separates completeness, content quality, evidential support, and extraction confidence. Third, it defines an evaluation agenda suitable for Persian enterprise RAG, distinguishing software verification from retrieval validity, generative faithfulness, governance effectiveness, and organizational impact.

## 2. Theoretical Background

### 2.1 Organizational knowledge as conversion and lifecycle

Nonaka's theory of organizational knowledge creation conceptualizes knowledge creation as a continuing interaction between tacit and explicit knowledge, rather than as the passive accumulation of information (Nonaka, 1994). This distinction is consequential for system design. Tacit knowledge is embedded in experience, judgement, context, and action; explicit knowledge can be articulated, combined, reviewed, and circulated. A capture system that requests only a title and an uploaded file may archive an object without adequately externalizing the reasoning that made it useful.

Alavi and Leidner (2001) similarly frame knowledge-management systems in relation to processes such as creation, storage and retrieval, transfer, and application. Their analysis implies that a repository is only one component of a broader organizational knowledge process. ISO 30401:2018 further treats knowledge management as a management system that must be established, implemented, maintained, reviewed, and improved, rather than as a one-time technology deployment. Together, these perspectives motivate a lifecycle model in which a knowledge item has an owner, a status, a version, an evidential basis, a review history, and a future review date.

### 2.2 Retrieval-augmented generation and non-parametric memory

RAG systems retrieve passages relevant to a query and provide those passages as context to a generative model. The foundational RAG formulation demonstrated that combining parametric and non-parametric memory can improve performance on knowledge-intensive natural-language tasks (Lewis et al., 2020). In enterprise settings, the practical attraction of RAG is not merely improved answer generation. Retrieval can expose source, page, document identity, and similarity information, thereby making an answer more inspectable than one produced solely from model parameters.

Dense retrieval requires semantically meaningful vector representations. Sentence-BERT introduced a siamese architecture that produces sentence embeddings suitable for efficient comparison using cosine similarity (Reimers & Gurevych, 2019). FAISS provides efficient primitives for similarity search over high-dimensional vectors (Johnson et al., 2017). These technologies make local semantic search feasible, but neither establishes whether the indexed content should be retrievable. Governance remains an orthogonal requirement.

### 2.3 Trustworthiness as a system property

Trustworthiness cannot be delegated to prompt wording. The NIST AI Risk Management Framework characterizes AI risk management as a continuous organizational activity and structures it around governance, mapping, measurement, and management (Tabassi, 2023). Its generative-AI profile extends this logic to risks associated with generative systems, including confabulation, information security, privacy, and human over-reliance (Autio et al., 2024). For enterprise RAG, these concerns imply at least four distinct controls: corpus admission, identity and access enforcement, grounded-output evaluation, and accountable human oversight.

The present artifact addresses parts of the first and fourth controls through review and publication states. Authentication, role-based access control, retrieval-time sensitivity filtering, and hardened file handling remain explicitly outside the validated scope of version 0.9.0. This disclosure is methodologically important: a prototype may instantiate a research design without satisfying all conditions required for operational trustworthiness.

## 3. Research Problem and Questions

The design problem can be stated as follows:

> How can an enterprise knowledge platform transform Persian or mixed-language descriptions and documents into structured, governed, semantically retrievable knowledge while preserving human accountability and exposing uncertainty?

This problem is decomposed into four research questions:

- **RQ1 — Capture:** How can heterogeneous narrative and documentary inputs be converted into a reusable knowledge schema without imposing a domain-specific interview on every contributor?
- **RQ2 — Governance:** How can quality, evidence, ownership, review, versioning, and publication be represented as executable workflow constraints rather than informal policy?
- **RQ3 — Retrieval:** How can multilingual dense retrieval support Persian-first organizational questions while retaining source-level provenance and abstaining under inadequate evidence?
- **RQ4 — Evaluation:** Which technical, epistemic, governance, and organizational measures are necessary to evaluate such a platform without conflating software correctness with knowledge effectiveness?

## 4. Research Method

The study follows a design-science orientation. Design science seeks knowledge through the construction and evaluation of artifacts that extend human or organizational capabilities (Hevner et al., 2004). The artifact is not treated as a neutral implementation of predetermined requirements; it is a material hypothesis about how enterprise knowledge capture and retrieval should be organized.

The research cycle comprises five activities:

1. **Problem identification:** Analyse the fragmentation of organizational knowledge, the limitations of document-only repositories, and the governance risks of unconstrained RAG.
2. **Requirement derivation:** Translate theoretical and operational concerns into requirements for capture, review, provenance, multilingual processing, retrieval, and auditability.
3. **Artifact construction:** Implement a modular prototype with a web interface, API, persistence layer, ingestion pipeline, knowledge graph, vector store, and language-model adapter.
4. **Technical verification:** Use automated tests and static checks to verify deterministic behaviours and prevent regressions in core workflows.
5. **Empirical evaluation:** Evaluate retrieval, grounded generation, usability, governance conformance, and organizational value using the protocol proposed in Section 9.

Only the first four activities have been instantiated in the present artifact. The fifth is specified as future empirical work. Consequently, the manuscript reports a design and verification study, not a completed organizational impact trial.

## 5. Design Requirements

The theoretical framing and operational problem yield the following design requirements.

| ID | Requirement | Rationale |
|---|---|---|
| DR1 | Accept narrative text, documents, or both | Knowledge exists in heterogeneous forms and contribution must remain low-friction. |
| DR2 | Use a domain-general knowledge schema | The platform must serve technical, human-resource, legal, financial, project, and managerial domains. |
| DR3 | Preserve human editability and review | Automated extraction is fallible and cannot confer organizational authority. |
| DR4 | Separate completeness, quality, evidence, and confidence | A complete form may be weakly evidenced; a confident extraction may still be low-value knowledge. |
| DR5 | Make publication an explicit state transition | Retrieval eligibility should follow governance rather than mere file availability. |
| DR6 | Preserve provenance, versions, and audit events | Users must be able to inspect origin, ownership, revision, and approval. |
| DR7 | Support Persian-first and mixed-script content | Language, typography, OCR, and technical identifiers affect functional correctness. |
| DR8 | Ground answers in retrieved sources and abstain when evidence is weak | Fluent unsupported generation is unacceptable in enterprise decision support. |
| DR9 | Degrade transparently when optional AI components fail | Loss of embedding or LLM services should not silently destroy captured knowledge. |
| DR10 | Permit migration from prototype to hardened deployment | Storage, identity, processing, and retrieval boundaries must remain replaceable. |

## 6. Artifact Architecture

### 6.1 Layered structure

The artifact separates interaction, application, persistence, ingestion, indexing, and generation concerns. A Streamlit interface supports Persian right-to-left workflows. A FastAPI application exposes capture sessions, knowledge items, reviews, attachments, documents, dashboards, knowledge maps, and chat. SQLite stores relational and JSON-encoded structured data. File extractors handle PDF, images, text, Markdown, Word, and Excel, with OCR as a conditional path. A multilingual sentence-transformer produces normalized embeddings, and FAISS stores searchable vectors. An OpenAI-compatible client provides the generative stage.

| Layer | Primary responsibility | Prototype implementation |
|---|---|---|
| Interaction | Persian-first contribution, review, navigation, and chat | Streamlit |
| Application API | Workflow orchestration and validation | FastAPI and Pydantic |
| Capture intelligence | Heuristic/optional-LLM extraction and scoring | Python rules plus model adapter |
| Persistence | Knowledge, sessions, versions, reviews, graph, audit | SQLite |
| Document processing | Text extraction and OCR | PyMuPDF, Tesseract, python-docx, openpyxl |
| Semantic retrieval | Chunking, embedding, nearest-neighbour search | LangChain components, sentence-transformers, FAISS |
| Generation | Context-grounded answers | OpenAI-compatible chat model |
| Export | Searchable Persian knowledge records | PyMuPDF Story and embedded fonts |

The modularity is deliberate. SQLite can be replaced by PostgreSQL, local files by object storage, synchronous processing by a worker queue, and the language-model endpoint by an approved organizational provider without redefining the conceptual lifecycle.

### 6.2 Capture as progressive externalization

A capture session begins with an optional description, one or more documents, or both. The system extracts candidate fields including knowledge type, title, summary, topic or need, principal method, steps, investigation, hypotheses, root cause, result, lessons, limitations, evidence, tags, organizational unit, owner, and sensitivity. The schema is domain-general: fields are populated when semantically appropriate rather than forcing all contributions into a maintenance-event template.

Automation remains subordinate to contributor agency. Existing explicit edits are preserved when documents are subsequently processed. Internal confidence metadata records the estimated reliability of extracted fields. When evidence conflicts, the session can enter a clarification state. When OCR or semantic extraction is unavailable, the original attachment remains connected to the workflow and the system records transparent placeholders rather than pretending that its content was understood.

This process operationalizes externalization: a contributor's account is transformed into an editable structure, but not yet into authoritative organizational knowledge. The distinction between extraction and authorization is foundational.

### 6.3 Governance lifecycle

The intended state sequence is:

```text
new → collecting → draft-ready → draft → pending-review
                                      ├→ needs-changes → revised draft
                                      ├→ rejected
                                      └→ published → indexed → periodically reviewed
```

Each knowledge item stores structured content, display content, ownership, sensitivity, quality indicators, review due date, status, and timestamps. Updates generate new snapshots in a version table. Reviews record the decision, reviewer, general comment, and field-level comments. Publication materializes graph entities and relations and triggers indexing. If the vector service is unavailable, publication remains recorded while the generated document receives an `index_failed` status. This failure policy prioritizes preservation and observability over silent rollback.

The current prototype does not yet strictly enforce every state transition and includes an administrative document-ingestion route that can bypass publication. These are implementation limitations, not desired design properties. A production implementation must make the lifecycle a server-enforced finite-state machine and require authorization for exceptional ingestion.

### 6.4 Lightweight knowledge graph

Structured fields are also projected into a lightweight graph. Nodes may represent the knowledge object, organizational unit, knowledge type, topic, hypothesis, cause, method, result, project, or asset. Relations express semantics such as `BELONGS_TO_UNIT`, `COVERS_TOPIC`, `EXPLAINED_BY`, `DESCRIBES`, and `PRODUCES`. The graph is not presented as a complete ontology. Its function is to expose interpretable organizational relationships that are difficult to recover from vector similarity alone.

This dual representation supports complementary questions. Dense retrieval addresses semantic resemblance; the graph addresses explicit relation and aggregation. Future research should examine graph-constrained retrieval, entity-level authorization, and temporal relations between versions.

### 6.5 Retrieval and grounded generation

Published text is cleaned, divided into overlapping chunks, embedded, and appended to a FAISS index. Let the normalized embedding of query (q) be \(\mathbf{e}_q\) and the embedding of chunk (d_i) be \(\mathbf{e}_i\). Because embeddings are unit-normalized, cosine similarity is:

\[
s(q,d_i)=\mathbf{e}_q^\top\mathbf{e}_i.
\]

The prototype converts the FAISS squared Euclidean distance of normalized vectors into an approximate cosine score:

\[
\hat{s}(q,d_i)=1-\frac{\lVert\mathbf{e}_q-\mathbf{e}_i\rVert_2^2}{2}.
\]

Candidates below a configured relevance threshold are discarded; accepted chunks are ranked and truncated to the final context size. The prompt instructs the model to answer in the question's language, cite retrieved sources, avoid invented numbers or specifications, distinguish general knowledge from document-grounded knowledge, and disclose insufficient context. When no document passes the threshold, the question can be registered as a knowledge gap rather than answered speculatively.

Thresholding is a useful control but not a calibrated guarantee. A similarity score estimates semantic proximity, not truth, authority, or answer sufficiency. Production retrieval must additionally filter by publication state, sensitivity, tenant, user entitlements, validity period, and superseded version.

## 7. Interpretable Knowledge Assessment

The artifact distinguishes four assessment dimensions.

### 7.1 Weighted completeness

Let \(R\) denote required fields, \(w_j\) the governance weight of field \(j\), and \(I_j\) an indicator that the field is meaningfully present. Completeness is:

\[
C=100\times\frac{\sum_{j\in R}w_jI_j}{\sum_{j\in R}w_j}.
\]

Unlike a raw field count, this formulation recognizes that omission of the knowledge topic or principal method is more consequential than omission of optional enrichment.

### 7.2 Content quality

Quality is a weighted composite:

\[
Q=20T+35U+15M+10O+10X+10E,
\]

where \(T\) is topic clarity, \(U\) content usefulness, \(M\) methodological structure, \(O\) outcome or application specificity, \(X\) transferability, and \(E\) evidence-and-limitations quality. Each component is normalized to \([0,1]\) using interpretable specificity heuristics, including meaningful length and, where relevant, numeric detail.

This score is a triage instrument, not an epistemic truth metric. It identifies records that appear more actionable or structured; it cannot determine whether a causal claim is scientifically valid.

### 7.3 Evidence score

Evidence scoring separately rewards attached sources, explicit evidence descriptions, verification procedures, reported outcomes, and confirmed causal analysis. The separation prevents a rhetorically detailed narrative from receiving the same evidential interpretation as a documented and verified account.

### 7.4 Extraction confidence

Extraction confidence is computed from field-level confidence values where available. It describes the system's confidence in the mapping from input to schema, not confidence that the underlying organizational claim is correct. This distinction addresses a common category error in AI-assisted knowledge capture: extraction certainty and knowledge validity concern different inferential objects.

## 8. Technical Verification

The repository contains fourteen automated tests. They verify:

- extraction of structured knowledge from rich Persian narratives;
- separation of hypothesis, investigation, action, and outcome;
- bounded quick-capture questioning;
- persistence of sessions and structured records;
- creation of general knowledge without equipment dependence;
- exclusion of unpublished knowledge from the public map;
- document registration following approval;
- graph relation generation;
- rebuildability of knowledge records and PDFs;
- searchable Persian PDF output, including mixed-script technical identifiers;
- correct handling of structured relevance output in the chat endpoint.

Static critical-error linting and deterministic formatting also pass. These results establish implementation consistency for the tested behaviours. They do **not** establish retrieval accuracy, answer faithfulness, user acceptance, causal knowledge quality, scalability, security, or business value. Reporting this boundary avoids converting a software test count into an unsupported claim of system effectiveness.

## 9. Proposed Empirical Evaluation

A defensible doctoral-level evaluation should combine four layers.

### 9.1 Retrieval evaluation

Construct a de-identified Persian enterprise benchmark containing realistic questions, expert-annotated relevant knowledge items, relevant chunks, and hard negatives from adjacent domains. Report Precision@\(k\), Recall@\(k\), mean reciprocal rank, normalized discounted cumulative gain, and abstention accuracy. Stratify results by document type, knowledge domain, query length, Persian/English code-switching, OCR quality, and sensitivity level.

Comparisons should include lexical BM25, the current multilingual dense retriever, a Persian-specific embedding model, and hybrid retrieval with reranking. Bootstrap confidence intervals and paired significance tests should accompany aggregate metrics.

### 9.2 Generative evaluation

For a held-out question set, assess context relevance, answer relevance, faithfulness, citation correctness, and unsupported-claim rate. RAGAS identifies retrieval relevance, faithful use of context, and answer quality as separable dimensions (Es et al., 2024). Automated evaluation should be calibrated against blinded human judgements by at least two domain experts, with inter-rater reliability reported.

Safety-critical or policy questions require error-severity weighting. A numerically small hallucination rate may remain unacceptable if errors concern legal obligations, operational safety, or access-controlled data.

### 9.3 Human and organizational evaluation

A controlled study should compare the platform with the organization's incumbent repository or document-sharing process. Participants should include knowledge contributors, reviewers, and consumers across multiple units. Candidate outcomes include:

- time required to create a reviewable knowledge item;
- correction rate for automatically extracted fields;
- reviewer time and disagreement rate;
- task completion time for finding and applying knowledge;
- perceived usefulness, trust calibration, and cognitive load;
- proportion of retrieved knowledge reused in documented decisions;
- contribution and reuse inequality across organizational units.

A longitudinal phase should measure whether initial participation persists, whether stale knowledge is reviewed on schedule, and whether knowledge gaps are resolved. Qualitative interviews should investigate invisible work, perceived surveillance, incentives to contribute, and the organizational politics of defining authoritative knowledge.

### 9.4 Governance and security evaluation

Governance evaluation should use adversarial scenarios: unauthorized attachment access, attempted approval by an unprivileged actor, retrieval of confidential records, stale-version leakage, malicious document uploads, prompt injection embedded in documents, tampered vector metadata, and repeated publication. Each scenario should have an explicit expected control and auditable outcome.

The following hypotheses can guide empirical work:

- **H1:** Structured assisted capture reduces median time-to-review without lowering expert-rated knowledge quality.
- **H2:** Governance-filtered hybrid retrieval improves Recall@5 over lexical retrieval while maintaining zero unauthorized retrieval in the test suite.
- **H3:** Source-grounded generation reduces unsupported-claim rate relative to the same model without retrieval.
- **H4:** Separating completeness, evidence, and confidence improves reviewer calibration compared with a single aggregate quality score.
- **H5:** Persian-specific or domain-adapted embeddings improve retrieval for Persian-only queries, while multilingual embeddings remain superior for mixed-script queries.

## 10. Security, Privacy, and Ethical Considerations

Enterprise knowledge systems can expose personal data, trade secrets, legal analysis, safety procedures, and tacit assessments of employees or organizational failures. The harm model therefore extends beyond conventional model hallucination.

First, identity must be authoritative. User and reviewer identifiers must derive from authenticated claims, not request payloads. Second, authorization must be enforced consistently across knowledge records, attachments, maps, audit logs, vector retrieval, and generated excerpts. Third, upload processing requires content validation, size limits, malware scanning, decompression controls, and asynchronous isolation. Fourth, the vector index must be treated as sensitive derived data; embeddings and serialized metadata may reveal corpus membership or become an execution risk if unsafe deserialization is permitted. Fifth, audit records must be tamper-evident and subject to a defined retention policy.

Human factors are equally important. A confidence score can induce automation bias if its meaning is unclear. Reviewers should see source evidence, extraction uncertainty, and changes between versions. Contributors must understand how their knowledge will be attributed, shared, and potentially used to evaluate work. Sensitive lessons learned require a culture in which reporting failure does not automatically produce punitive visibility.

The appropriate production posture is therefore defence in depth: authenticated identity, least privilege, corpus-level and chunk-level access control, encrypted storage and transport, secret management, observable model calls, incident response, red-team testing, and periodic governance review. These controls align with the lifecycle orientation of the NIST AI RMF and its generative-AI profile.

## 11. Discussion

### 11.1 Theoretical contribution

The artifact reframes enterprise RAG as the terminal stage of a knowledge-governance process. Most technical descriptions begin with an available corpus and optimize chunking, embeddings, ranking, or prompting. The present design begins earlier: with externalization, ownership, evidence, review, and publication. Its central proposition is:

> The epistemic reliability of enterprise RAG is bounded not only by retrieval and generation performance, but by the governance process that determines corpus membership.

This proposition connects organizational knowledge theory with contemporary language-model architecture. Human review is not a peripheral compliance step; it is part of the construction of non-parametric organizational memory.

### 11.2 Design contribution

The multidimensional assessment model is intentionally interpretable. Completeness, quality, evidence, and confidence are not collapsed because they answer different questions: Is the record sufficiently populated? Is it actionable and well-structured? Is it supported? Was it extracted reliably? This decomposition enables targeted intervention and more calibrated reviewer judgement.

The design also demonstrates graceful degradation. Knowledge capture can survive temporary absence of the embedding model or language-model service. In enterprise systems, preserving a transparent failure state is often more valuable than maintaining the appearance of seamless intelligence.

### 11.3 Practical contribution

The prototype provides a migration path from a local MVP to a production architecture. Its modular components can be replaced incrementally, while the underlying lifecycle and schema remain stable. This is particularly relevant to organizations that require data residency, local OCR, Persian interfaces, or vendor-neutral language-model integration.

## 12. Limitations and Threats to Validity

The present work has several limitations.

1. **No field deployment:** The artifact has not yet been evaluated with organizational users or real decision outcomes.
2. **No gold-standard retrieval benchmark:** Configured similarity thresholds are engineering defaults, not empirically calibrated decision boundaries.
3. **Heuristic quality measures:** Specificity and evidence scores require validation against expert assessments and may privilege verbosity.
4. **Prototype persistence:** SQLite and local files are unsuitable for multi-tenant, high-concurrency, or strongly regulated deployment.
5. **Incomplete authorization:** The prototype does not yet implement authentication, role-based access control, or retrieval-time entitlement filtering.
6. **Index lifecycle limitations:** Repeated publication can create duplicate or superseded vectors unless version-aware deletion is added.
7. **Language-model dependence:** Extraction and generation quality vary with provider, model version, prompt, and service availability.
8. **Persian heterogeneity:** Character normalization, dialect, OCR noise, mixed scripts, and domain abbreviations require broader evaluation.
9. **Graph simplicity:** The lightweight graph is not a validated enterprise ontology and does not yet support temporal or probabilistic relations.
10. **External validity:** Findings from one organizational and linguistic context may not generalize to other governance regimes or knowledge cultures.

These limitations define the next research programme rather than invalidating the artifact's design contribution.

## 13. Conclusion

This article presented a governance-centred, Persian-first architecture for enterprise knowledge capture and retrieval-augmented generation. The platform treats organizational knowledge not as raw content awaiting embedding, but as a versioned, evidenced, owned, reviewed, and lifecycle-managed object. Its architecture combines low-friction capture, document processing, structured evaluation, human review, lightweight graph representation, multilingual dense retrieval, and grounded generation.

The implemented prototype demonstrates technical feasibility and passes fourteen automated tests, but technical verification is only the first layer of evidence. A credible claim of organizational value requires benchmarked retrieval, calibrated grounded-generation evaluation, controlled user research, governance auditing, and longitudinal study. The broader lesson is that enterprise RAG should be designed from governance outward. Retrieval quality matters, but the organizational legitimacy of what may be retrieved matters first.

## Data and Artifact Availability

The software artifact is maintained in the accompanying repository. Runtime databases, uploaded organizational documents, API credentials, and generated vector indexes are intentionally excluded from version control. No human-subject dataset is included in this release. Any future empirical dataset should be de-identified, access-controlled, and released only under an approved governance and ethics protocol.

## References

Alavi, M., & Leidner, D. E. (2001). Review: Knowledge management and knowledge management systems: Conceptual foundations and research issues. *MIS Quarterly, 25*(1), 107–136. [AIS Electronic Library](https://aisel.aisnet.org/misq/vol25/iss1/6/)

Autio, C., Schwartz, R., Dunietz, J., Jain, S., Stanley, M., Tabassi, E., Hall, P., & Roberts, K. (2024). *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile* (NIST AI 600-1). National Institute of Standards and Technology. [https://doi.org/10.6028/NIST.AI.600-1](https://doi.org/10.6028/NIST.AI.600-1)

Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2024). RAGAS: Automated evaluation of retrieval augmented generation. In *Proceedings of the 18th Conference of the European Chapter of the Association for Computational Linguistics: System Demonstrations*. [ACL Anthology](https://aclanthology.org/2024.eacl-demo.16/)

Farahani, M., Gharachorloo, M., Farahani, M., & Manthouri, M. (2020). ParsBERT: Transformer-based model for Persian language understanding. [arXiv:2005.12515](https://arxiv.org/abs/2005.12515)

Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). Design science in information systems research. *MIS Quarterly, 28*(1), 75–105. [https://doi.org/10.2307/25148625](https://doi.org/10.2307/25148625)

International Organization for Standardization. (2018). *ISO 30401:2018 Knowledge management systems—Requirements*. [ISO standard page](https://www.iso.org/standard/68683.html)

Johnson, J., Douze, M., & Jégou, H. (2017). Billion-scale similarity search with GPUs. [arXiv:1702.08734](https://arxiv.org/abs/1702.08734)

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. In *Advances in Neural Information Processing Systems 33*. [NeurIPS paper](https://papers.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html)

Nonaka, I. (1994). A dynamic theory of organizational knowledge creation. *Organization Science, 5*(1), 14–37. [https://doi.org/10.1287/orsc.5.1.14](https://doi.org/10.1287/orsc.5.1.14)

Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. In *Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing*. [ACL Anthology](https://aclanthology.org/D19-1410/)

Tabassi, E. (2023). *Artificial Intelligence Risk Management Framework (AI RMF 1.0)* (NIST AI 100-1). National Institute of Standards and Technology. [https://doi.org/10.6028/NIST.AI.100-1](https://doi.org/10.6028/NIST.AI.100-1)
