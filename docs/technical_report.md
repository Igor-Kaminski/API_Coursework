# Technical Report

## 1. Introduction

This project is a RESTful web API for UK rail reliability and delay analysis, built around the coursework brief: *"A public transport reliability and delay analytics API using open UK transport datasets, providing CRUD for user-reported incidents and endpoints for route-level reliability scores, delay patterns, and temporal performance summaries."* The system ingests real operational data from the National Rail Data Portal, specifically from Darwin — a real-time feed used across Britain by every train operating company in England, Scotland, and Wales, powering departure boards at stations and widely-used services such as Trainline — and from the KnowledgeBase reference system, which provides accurate station and route naming.

The API serves two distinct purposes. First, it provides read access to reference and analytical data: stations, routes, route-level reliability scores, delay distributions, cancellation rates, and station-level disruption hotspots. Second, it provides full CRUD management for user-reported incidents, allowing operators and users to log and track service disruptions independently of the imported operational data. In summary, the imported Darwin and KnowledgeBase data is read-only and analytical, while the incident data supports full read and write access through the API.

## 2. Technology Choices and Rationale

The implementation uses `Python 3.11`, `FastAPI`, `PostgreSQL`, `SQLAlchemy 2.0`, `Pydantic v2`, `Alembic`, `pytest`, and `Uvicorn`.

`FastAPI` was chosen as it is the modern Python framework of choice for API development, supporting rapid development through its straightforward design while still encouraging good engineering practice. Automatic OpenAPI and Swagger documentation generation reduces manual documentation overhead, and strong request validation keeps the API predictable. `Pydantic` was useful for keeping input and output schemas explicit and consistent, improving both validation and the generated documentation.

`PostgreSQL` was selected as the database because the project is naturally relational. The core entities — stations, routes, journey records, and incidents — have clear foreign-key relationships and integrity constraints. A document database would have made these relationships harder to enforce and justify. `SQLAlchemy 2.0` and `Alembic` were used to keep the schema maintainable and versioned, which also improves deployment reproducibility.

The overall architecture was kept as a modular monolith rather than introducing microservices. For this coursework, a monolith is easier to test, easier to explain, and more realistic than splitting a relatively small system across multiple services. The project structure separates `models`, `schemas`, `routers`, `services`, and `core` configuration so the code remains organised without becoming over-engineered.

As an advanced extension, an `MCP` server was implemented over the same database and business logic. This was not required for the minimum coursework pass criteria, but it strengthens the originality of the submission by demonstrating how the same system can be exposed through both conventional HTTP endpoints and MCP-compatible tools.

## 3. Data Model and Ingestion Strategy

The database centres on four core entities: `Station`, `Route`, `JourneyRecord`, and `Incident`. `Station` stores location metadata and business identifiers such as station code, CRS code, and TIPLOC code — both CRS and TIPLOC are standard industry identifiers used to uniquely reference stations across National Rail systems. `Route` links origin and destination stations and stores route-level metadata such as operator name and approximate distance. `JourneyRecord` stores imported operational timing data, including scheduled and actual times, status, delay minutes, source, and external identifiers. `Incident` stores user-generated disruptions and service issues.

The data was sourced from the National Rail Data Portal [1], specifically the Darwin Push Port real-time feed and the KnowledgeBase reference API. The ingestion strategy was designed around an important principle: external feeds should be data sources, not runtime dependencies for public endpoints. The API does not call Darwin or KnowledgeBase during ordinary user requests. Instead, data is fetched and loaded by import scripts, normalised into the relational schema, and then queried locally through the API. This makes analytical endpoints faster, more consistent, and easier to demonstrate.

Darwin-derived data forms the main operational history source, while KnowledgeBase reference data improves station and route readability. In practice, this involved handling real-world data problems such as code aliases, incomplete location metadata, route duplication, and unresolved timing points, which led to additional merge and deduplication logic in the import process. At the time of writing, the local dataset contains approximately `2,993` stations, `2,899` routes, and `18,588` journey records, which is sufficient to support meaningful analytics and live demonstration.

## 4. API and Analytics Design

The API is versioned under `/api/v1` and grouped into stations, routes, incidents, and analytics. Public read access is available for all major resources. Write operations use a simple API-key model through the `X-API-Key` header. This is intentionally lightweight: `admin` can manage reference data and incidents, `operator` can manage incidents, `user` can create incidents, and unauthenticated users can access read-only endpoints. This model was chosen because it is straightforward to implement, proportionate for the coursework scope, and easy to justify in an oral examination.

Usability was further improved by exposing lookups through public-facing business identifiers rather than relying solely on numeric IDs. Stations can be filtered by code, name, city, CRS code, and TIPLOC code. Routes and some analytics can be addressed by route code as well as by internal ID. This makes the API more intuitive and better aligned with how a real user would search transport data.

The analytics were intentionally designed to be simple, transparent, and appropriate for the available dataset. Core endpoints calculate route reliability, average delay, station hotspots, incident frequency, and common delay reasons. During development, consideration was given to whether time-bucket analytics were defensible for a short data window. As a result, the emphasis shifted to stronger short-window measures such as cancellation rate, delay distribution, top delayed routes, top cancelled routes, and incident severity or status breakdowns. This reflects an important lesson from the project: analytics should match the quality and timespan of the available data, not just theoretical possibilities.

## 5. Error Handling, Security, Testing, and Deployment

To improve the consistency and professionalism of the API, error responses were standardised through a shared error model with explicit handling for `401`, `403`, `404`, `409`, `422`, `500`, and `503` cases. Delete operations for stations and routes were tightened to fail with clear conflict responses if related records still exist. These changes do not introduce new features, but they improve the predictability and robustness of the API.

Security is intentionally basic but not absent. The application includes API-key checks, rate limiting with `slowapi`, `CORS` middleware, database-aware health checks, and structured exception handling for database or unexpected server errors. This is far simpler than a production identity or secrets-management system, but it represents a reasonable level of security for the coursework scope.

Testing was carried out using `pytest` with isolated database fixtures and targeted API and service tests. The suite covers incident permissions, station and route lookup behaviour, analytics endpoints, security features, error handling, import services, Darwin snapshot parsing, and MCP functionality. Coverage reporting was added with `pytest-cov`, and the project currently reports roughly `81%` line coverage across the `app` package. This does not guarantee every path is correct, but it provides strong evidence that the most important behaviour is exercised automatically.

The project is deployed on Render using a `render.yaml` blueprint for both the web service and PostgreSQL database, and is accessible at `https://rail-api-coursework.onrender.com/`. One practical lesson from deployment is that schema creation and data population are separate concerns: migrations can initialise an empty hosted database, but imported operational data must still be copied or re-imported before live analytics become meaningful.

## 6. Reflection, Limitations, and Future Work

One of the first challenges encountered was sourcing a suitable dataset. Many datasets exist online, however finding one appropriate for this specific domain proved more difficult than anticipated. A significant portion of development effort went into cleaning identifiers, resolving station names, making routes human-readable — all routes were stored using internal code symbols that required resolution to operator and station names — and handling generally incomplete or inconsistent data throughout.

A further challenge was managing the scope of the project. The use of generative AI is fully permitted for this coursework, which significantly expands what is achievable, but the project still needed to remain explainable and presentable in an oral examination. A deliberate decision was made not to over-engineer the system. The monolithic architecture, lightweight authentication, and straightforward analytics all reflect this — the goal was a submission of higher quality and clarity rather than one of excessive complexity.

A significant limitation is that the dataset covers a relatively short time window, which prevents any meaningful long-term trend analysis. The data spans only a few days. While Darwin holds an extensive volume of operational data, a future improvement would be to sample across a wider date range to enable more robust temporal analysis. The authentication model is also basic by design and would require a full redesign before deployment as a public-facing service, as there are security considerations that were not fully addressed within the coursework scope.

## 7. Generative AI Declaration

Generative AI was used extensively throughout the project. After reading the project brief, the PDF was provided to ChatGPT to explore key decisions, such as why FastAPI was preferable to Django or why PostgreSQL was preferable to SQLite. The initial requirements and core architectural decisions were established through this process. A detailed prompt covering all aspects of the project was then constructed and provided to Cursor in planning mode in a new conversation to preserve context. Cursor, using GPT 5.4 Codex, built the project incrementally, requesting clarification where judgment or additional information was needed, and exploring alternative decisions and refinements along the way.

To manage context and token usage, the model was directed to delegate implementation tasks to sub-agents, acting itself as a coordinator with full project context while sub-agents handled discrete tasks. Generative AI wrote the majority of the project code, with decisions reviewed and approved throughout. The technical report and presentation were also produced collaboratively with generative AI, with a final pass to improve grammar, structure, and formality.

## Links

- **GitHub Repository:** https://github.com/Igor-Kaminski/API_Coursework
- **Live API:** https://rail-api-coursework.onrender.com/ *(hosted on Render's free tier — initial load may take up to 30 seconds if the service has spun down)*
- **API Documentation (PDF):** https://github.com/Igor-Kaminski/API_Coursework/blob/main/docs/api_documentation.pdf
- **API Documentation (source):** https://github.com/Igor-Kaminski/API_Coursework/blob/main/docs/api_documentation.md
- **MCP Server Documentation:** https://github.com/Igor-Kaminski/API_Coursework/blob/main/docs/mcp_server.md
- **Technical Report (source):** https://github.com/Igor-Kaminski/API_Coursework/blob/main/docs/technical_report.md
- **Presentation Slides:** https://github.com/Igor-Kaminski/API_Coursework/blob/main/docs/presentation.pptx

**GenAI Conversation Logs:**

- https://chatgpt.com/share/69bdc8a7-8cd0-8000-b258-d567d71e2848
- https://chatgpt.com/share/69bdc948-d6d4-8000-8890-2f85f2ad9fd2
- https://chatgpt.com/share/69bdc96a-4cdc-8000-828a-2d2bc0a3830a
- https://chatgpt.com/share/69bdc9e3-c428-8000-8953-bfda65a6537e
- https://chatgpt.com/share/69bdc9f4-7ae0-8000-b5d8-7664ea8c3511
- https://chatgpt.com/share/69bdca05-8e14-8000-8be6-41dce66715d5
- https://chatgpt.com/share/69bdca27-a94c-8000-98e9-e5d64dd7e7d7
- Cursor conversation exports: https://github.com/Igor-Kaminski/API_Coursework/tree/main/docs/conversations

## References

[1] National Rail Data Portal — https://datafeeds.nationalrail.co.uk/

[2] FastAPI — https://fastapi.tiangolo.com/

[3] SQLAlchemy 2.0 — https://docs.sqlalchemy.org/en/20/

[4] Pydantic v2 — https://docs.pydantic.dev/latest/

[5] Alembic — https://alembic.sqlalchemy.org/

[6] PostgreSQL — https://www.postgresql.org/

[7] slowapi — https://github.com/laurentS/slowapi

[8] Model Context Protocol (MCP) — https://modelcontextprotocol.io/