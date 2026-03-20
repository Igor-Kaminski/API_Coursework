# Codebase review for coursework improvement
_Exported on 3/20/2026 at 22:33:09 GMT from Cursor (2.6.20)_

---

**User**

look through my codebase, @COMP3011_Coursework1_Brief__2025_2026 (1).pdf  and suggest what i need to improve my marks

---

**Cursor**

Let me also check the README and a few more key files before giving my analysis.

Now I have everything I need. Here's a comprehensive breakdown of what you should improve, ordered by impact on your marks.

---

## Critical FAIL Risks (fix these first)

**1. Technical Report is missing from your repo**

Your README even acknowledges this: *"The technical report, GenAI declaration, conversation logs, and presentation slides can be added alongside this repository for final submission."* — The brief is explicit: **missing technical report = automatic Fail** regardless of code quality. It must include:
- Justification for FastAPI, PostgreSQL, SQLAlchemy, Pydantic v2
- Challenges faced and lessons learned
- Limitations and future improvements
- GenAI declaration with conversation log exports as an appendix

**2. Presentation slides (PPTX) are missing**

Required for submission via Minerva. The brief specifies dedicated sections on: version control practices, API documentation overview, technical report highlights, and all deliverables.

---

## High Impact: Version Control & Deployment (6 marks)

**3. No deployment configuration**

The 50-59 band requires hosting on an external server. The 70-79 band requires "professional deployment". You have neither a `Dockerfile` nor any cloud config. Add one:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e .
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Then deploy to Railway, Render, or Fly.io — they all have free tiers and take ~10 minutes to set up. PythonAnywhere is also specifically mentioned in the brief.

**4. Commit history is thin**

You have 20 commits but they're all feature-level. The examiners *"will navigate through your GitHub repository and review your commit history"*. More granular commits (tests, fixes, docs updates) make the version control discipline more credible.

---

## Medium Impact: Security (for 80+ band)

**5. Security is very basic**

The 80-89 band requires "advanced security implementation". Currently you have 3 static plaintext API keys. Consider adding:

- **Rate limiting** — `slowapi` integrates with FastAPI in ~10 lines
- **CORS** — FastAPI's `CORSMiddleware` (currently absent from `app/main.py`)
- **Input sanitisation** — Pydantic handles types but you have no SQL injection protection beyond the ORM

**6. `app/main.py` is missing CORS and lifespan**

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Also no startup/shutdown lifespan events — adding a health check that actually tests the DB connection would be more robust.

---

## Medium Impact: Testing & Error Handling (6 marks)

**7. No coverage report in CI**

`pytest-cov` is installed but there's no `.coveragerc` or `pyproject.toml` coverage config. Add this to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "--cov=app --cov-report=term-missing"
```

Run it and include the output in your technical report. A number like "85% coverage" is very compelling in a Q&A.

**8. Error handling could be more explicit**

You return 404s and 403s, but there's no global exception handler for unexpected database errors. For 80+ band, add a structured error response model and register a handler in `main.py`.

---

## Medium Impact: Documentation (12 marks)

**9. README doesn't link to the technical report**

The brief says the technical report PDF must be in the repo and linked from the README. Currently only the API docs PDF is linked.

**10. Swagger UI auto-docs aren't highlighted**

FastAPI gives you `/docs` and `/redoc` for free, and these are specifically mentioned in the brief as accepted documentation formats. Make sure your presentation demo includes live interaction with Swagger UI — it's very visually impressive and takes no extra work.

---

## For 90-100 (Outstanding): Creativity & GenAI

**11. You already have the MCP server — lean into it hard**

The brief explicitly lists MCP as an "advanced feature" for the 70-79 band. Your 23-tool MCP server with resources and prompts is genuinely cutting-edge. This is your strongest differentiator for 80+ marks. In your presentation and technical report, frame this as:
- A second interface layer that makes the API accessible to LLM agents
- The prompt engineering in `investigate_route_delay` and `triage_recent_incidents` as an example of GenAI-native API design

**12. GenAI declaration should show high-level usage**

The rubric's 80-89 band requires *"high level use of GenAI to aid creative thinking and solution exploration"*, and 90-100 requires *"creative application of GenAI such as exploring high-level alternatives"*. Don't just log "used Cursor to write code" — document architecture decisions you explored with AI, alternatives you considered (e.g. GraphQL vs REST, JWT vs API keys), and how AI shaped your MCP design.

---

## Summary Table

| Priority | Item | Risk if missing |
|---|---|---|
| **CRITICAL** | Technical report + GenAI declaration | Automatic Fail |
| **CRITICAL** | Presentation slides (PPTX) | Automatic Fail |
| **HIGH** | Deployment (Dockerfile + hosted URL) | Capped at ~50-59 |
| **HIGH** | More granular commit history | Reduces version control marks |
| **MEDIUM** | Rate limiting + CORS | Capped below 80 |
| **MEDIUM** | Coverage report with % number | Testing marks |
| **MEDIUM** | Global error handler | Testing/error handling marks |
| **LOW** | README link to technical report | Minor documentation mark loss |

The oral exam is next week (23–27 March), so your highest-leverage actions right now are: (1) write the technical report, (2) make the deployment work and get a live URL, and (3) prepare to articulate the MCP server design decisions confidently in the Q&A.

