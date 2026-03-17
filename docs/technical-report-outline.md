# Technical Report Outline

## 1. Project Overview

- Problem domain: transport reliability and delay analytics
- Why this problem is realistic and suitable for a web services API
- High-level summary of the final system

## 2. Requirements And Scope

- CRUD requirement and how `Incident` satisfies full CRUD
- Additional reference entities: `Station` and `Route`
- Scope boundaries and deliberately excluded features

## 3. Technology Stack And Justification

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Pydantic
- Alembic
- pytest

For each item, explain why it was chosen and which alternative was rejected.

## 4. System Architecture

- Layered structure: API, services, schemas, models, database
- Why admin-managed reference data and incident-centric analytics were used
- Mermaid or architecture diagram

## 5. Database Design

- Entity descriptions for Station, Route, Incident
- Primary keys, foreign keys, constraints, and indexes
- Why these relationships are realistic

## 6. Authentication And Authorization

- API-key approach
- Admin vs operator permissions
- Why JWT and user accounts were intentionally not included

## 7. API Design

- Resource structure and naming
- Filtering design
- Error handling and HTTP status code choices
- How FastAPI documentation supports usability

## 8. Analytics Design

- Route overview
- Worst travel hour
- Top delayed stations
- Incidents by hour
- Reliability score heuristic and its limitations

## 9. Testing Strategy

- Endpoint tests
- Auth tests
- Validation tests
- Analytics tests
- Summary of what was not tested and why

## 10. Challenges And Trade-Offs

- Keeping scope realistic
- Modelling reliability without timetable data
- Choosing API keys instead of larger auth
- Using curated seed data rather than live runtime integrations

## 11. Limitations And Future Improvements

- No real-time feed ingestion
- No passenger volume or timetable information
- No user account audit trail
- Potential future features such as dashboards, scheduled imports, or deployment hardening

## 12. Generative AI Declaration And Reflection

- Which AI tools were used
- What tasks they supported
- What was manually reviewed or verified
- Why the usage was high-level and methodical rather than blind generation

## 13. References

- Dataset references
- Library/framework documentation
- Any tutorials or official docs consulted
