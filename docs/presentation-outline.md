# Presentation Outline

## Slide 1. Title And Project Goal

- Project name
- One-sentence problem statement
- One-sentence value proposition

## Slide 2. Why This Project

- Why transport reliability is a good API problem
- What makes the project more than simple CRUD

## Slide 3. Architecture And Stack

- FastAPI, PostgreSQL, SQLAlchemy, Pydantic, Alembic, pytest
- Layered backend diagram

## Slide 4. Data Model

- Station
- Route
- Incident
- Explain reference data vs operational data

## Slide 5. API Design

- Example endpoints
- Filtering
- Status codes
- Swagger/OpenAPI docs

## Slide 6. Security Design

- X-API-Key header
- Admin vs operator permissions
- Why this was chosen over JWT

## Slide 7. Analytics

- Route overview
- Worst time to travel
- Top delayed stations
- Reliability score heuristic

## Slide 8. Testing And Version Control

- Summary of pytest coverage
- Show commit history screenshot
- Explain incremental development process

## Slide 9. Documentation And Deliverables

- README
- API documentation PDF
- Technical report
- Public repository

## Slide 10. Reflection

- Main challenges
- What you would improve next
- How GenAI was used methodically

## Demo Flow Suggestion

- Show `/docs`
- Show one protected create endpoint
- Show one filtered incident query
- Show one analytics endpoint
- Mention tests passed and migration support
