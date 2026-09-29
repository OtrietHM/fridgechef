# 🧊 FridgeChef: AI-Powered Recipe Generator

FridgeChef generates personalized recipes from the ingredients you already have, helping reduce food waste. Built for my **NLP / AI (2026)** course.

> **Status:** Course prototype. Recipe generation works end to end (OpenAI call, validation layer, caching). The computer-vision endpoint is still a placeholder and user accounts aren't wired to the API yet (see [Roadmap](#roadmap)).

## Features
- Recipe generation from a list of ingredients and a dietary preference (e.g., vegan, keto)
- Structured JSON output from GPT to reduce hallucinated recipes
- JWT authentication with bcrypt password hashing
- PostgreSQL models for users, dietary preferences, and saved recipes
- Validation layer: rejects recipes that use ingredients you didn't provide or break your diet, and retries once with feedback
- In-memory caching of repeated ingredient combinations to cut API cost and latency
- Pytest suite (LLM calls are mocked, so tests need no API key)
- Dockerized for AWS/GCP deployment

## Tech Stack
| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Database | PostgreSQL + SQLAlchemy |
| AI | OpenAI GPT API |
| Auth | JWT (python-jose), passlib/bcrypt |
| Testing | Pytest |
| Deployment | Docker |
| Planned frontend | React (web) or Flutter (mobile) |

## Project Structure
```
app/
  main.py          FastAPI entry point
  models.py        SQLAlchemy models (User, SavedRecipe)
  services.py      GPT integration and dietary filter
  auth.py          Password hashing and JWT creation
  api/recipes.py   /recipes/generate and /recipes/vision/detect
tests/             Pytest suite
docs/              Project compilation and risk & mitigation report (PDF)
notebooks/         Original Colab notebook
```

## Getting Started
```bash
git clone https://github.com/<your-username>/fridgechef.git
cd fridgechef
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in your keys
uvicorn app.main:app --reload
```
API docs are served at http://localhost:8000/docs. Try it:
```bash
curl -X POST http://localhost:8000/recipes/generate \
  -H "Content-Type: application/json" \
  -d '{"ingredients": ["tomato", "egg", "spinach"], "preference": "vegetarian"}'
```
Response: `{"title": ..., "ingredients": [...], "steps": [...], "cached": false}`. Supported preferences: vegan, vegetarian, dairy-free, gluten-free.

Run tests:
```bash
pytest
```

Run with Docker:
```bash
docker build -t fridgechef .
docker run -p 8000:8000 --env-file .env fridgechef
```

## Risks & Mitigations
| Risk | Mitigation |
|---|---|
| Inaccurate ingredient detection | Manual correction UI before generation |
| Hallucinated recipes | JSON-mode structured output, strict system prompt, validation layer |
| API cost scaling | Prompt token optimization and caching of common queries |
| Latency over 3 s | Async FastAPI and caching |
| Data privacy | JWT auth, hashed passwords, encrypted DB connections |

Full details are in [`docs/FridgeChef_Risk_Report.pdf`](docs/FridgeChef_Risk_Report.pdf).

## Roadmap
- [x] Wire `/recipes/generate` to the OpenAI service
- [x] Validation layer and in-memory caching
- [ ] Move the cache to Redis/PostgreSQL so it persists across restarts
- [ ] Implement the computer-vision ingredient detection (Phase 2)
- [ ] Connect database sessions and auth routes (register/login)
- [ ] Add recipe caching
- [ ] Build the React/Flutter frontend

## Author
**Triet Le**

## License
MIT. See [LICENSE](LICENSE).
