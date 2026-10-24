# Contribo

**They make it by AI so we judge by AI.**

Contribo helps developers find open-source issues that match their skills and helps maintainers review pull requests using evidence from the repository, code changes, tests, reviews, and CI checks.

The idea is simple. If AI is being used to write code, it should also help us review that code. But its decisions should be backed by evidence, not just generated opinions.

## The Problem

Contributing to open source is not always easy.

- Beginners often struggle to find issues they can work on.
- Understanding an unfamiliar codebase takes time.
- Maintainers have to spend hours reviewing pull requests and checking whether changes actually work.
- AI can make incorrect claims, so its recommendations need to be verified.

## What Contribo Does

### For Developers

- Find issues that match their skills and interests.
- Understand what an issue requires before starting work.
- Get guidance on how to approach a contribution.
- See why an issue might be a good fit for them.

### For Maintainers

- Review pull requests with relevant repository context.
- Check code changes against available tests and CI results.
- Identify claims that need more evidence.
- Get structured reviews with references to supporting information.

These are the project's planned capabilities. Features will be marked as implemented as development progresses.

## How It Works

```text
CONTRIBUTOR / MAINTAINER
                              |
                              v
                    +-------------------+
                    |     FRONTEND      |
                    | Vanilla HTML/JS   |
                    +-------------------+
                              |
                              | HTTP requests (JSON)
                              v
                    +-------------------+
                    |      BACKEND      |
                    |      FastAPI      |
                    +-------------------+
                              |
                 +------------+------------+
                 |            |            |
                 v            v            v
          +-------------+ +-------------+ +-------------+
          | Issue       | | Beginner    | | PR          |
          | Discovery   | | Guidance    | | Verification|
          | Engine      | | Engine      | | Engine      |
          +-------------+ +-------------+ +-------------+
                 |            |            |
                 +------------+------------+
                              |
                              v
                    +-------------------+
                    |   QWEN MODEL      |
                    | Issue and code    |
                    | understanding     |
                    +-------------------+
                              |
                              v
                    +-------------------+
                    | RULES + EVIDENCE  |
                    | Scoring, checks,  |
                    | tests, rankings   |
                    +-------------------+
                              |
                              v
                    +-------------------+
                    | JSON RESPONSE     |
                    +-------------------+
                              |
                              v
                    FRONTEND DISPLAYS RESULTS
```

Contribo has four main stages.

1. **Repository Understanding:** Understand the repository's structure, programming languages, dependencies, and tests.
2. **Issue Understanding:** Identify what an issue asks for, its requirements, and its possible difficulty.
3. **Contribution Verification:** Examine pull request changes and compare claims against available code, reviews, tests, and CI results.
4. **Recommendation:** Rank issues based on relevant skills, developer preferences, and evidence gathered from the previous stages.

## Evidence and Verification

Contribo should be able to explain why it makes a recommendation or flags a problem.

- Every important claim should refer to identifiable evidence.
- Claims with missing or invalid evidence should be rejected or marked as unverified.
- AI responses should follow a defined output format.
- Recommendations should include understandable reasons.
- Developers and maintainers should make the final decisions.

## AI Models

Contribo uses four models for its intelligence layer.

### 1. Repository Intelligence
**[Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)** | Apache-2.0

Analyzes repository structure, source files, dependencies, architecture, and tests to build a repository map.

### 2. Issue Intelligence
**[Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)** | Apache-2.0

Understands issue requirements and provides beginner-friendly explanations or detailed mentor guidance using separate prompts and output schemas.

### 3. Contribution Verification
**[Qwen2.5-Coder-14B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct)** | Apache-2.0

Analyzes pull request changes against issue requirements, identifies potential gaps, and suggests missing tests. Findings must be checked against actual code, CI results, and review data.

### 4. Recommendation Intelligence
**[Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B)** | Apache-2.0

Ranks issues and pull requests based on relevance to developer skills, requirements, and available evidence.

### Model Integration

Each model will use a defined interface and structured output. A deterministic validator will check evidence references and flag unsupported claims. Recommendation scores will be combined with verified GitHub signals and repository rules.

These are the selected model candidates. Their exact checkpoints, licenses, and usage conditions will be verified before integration. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for third-party licensing information.

## Planned Technology

- GitHub API for issues, pull requests, reviews, and CI checks.
- Repository file and code diff analysis.
- An interchangeable AI model interface.
- Structured outputs and deterministic validation.
- Evidence-based issue recommendations and ranking.

The final technology stack will be documented as the implementation develops.

## Project Status

**Active development — backend and frontend are connected and working.**

| Layer | Status |
|---|---|
| Frontend (HTML/CSS/JS) | ✅ Complete |
| Backend API (FastAPI) | ✅ Complete |
| GitHub data fetching | ✅ Complete (issue, PRs, diffs, CI checks) |
| SQLite caching | ✅ Complete |
| Rule engine (scoring) | ✅ Placeholder — deterministic signals |
| LLM integration (Qwen) | 🔜 Placeholder hooks in place |

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### 1. Clone the repository

```bash
git clone https://github.com/vanshikasoni22/Metamorph-OpenSource.git
cd Metamorph-OpenSource
```

### 2. Set up the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and add your GitHub Personal Access Token (optional but recommended):

```
GITHUB_TOKEN=ghp_your_token_here
```

Without a token, the GitHub API allows 60 requests/hour. With a token, the limit is 5,000 requests/hour.

### 4. Start the backend server

```bash
python3 -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at `http://localhost:8000`. The frontend is served automatically from the same server.

Open your browser at: **http://localhost:8000**

### API Documentation

Interactive API docs are available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Contributing

Contributions, feedback, and suggestions are welcome.

Before contributing:

1. Check existing issues and pull requests.
2. Explain what you want to change and why.
3. Include tests or verification steps when relevant.
4. Keep changes focused and easy to review.

More detailed contribution guidelines will be added as the project grows.

## Responsible AI

Contribo is intended to support developers and maintainers, not replace their judgment.

- Do not treat an AI-generated claim as a verified fact without checking its evidence.
- Report missing evidence instead of inventing it.
- Make uncertainty clear when the available information is insufficient.
- Leave final merge and contribution decisions to the people responsible for the project.

## License

Contribo's original application code will be released under the **Apache License 2.0**.

Third-party dependencies, model weights, and external code may have separate licenses and conditions. These must be checked independently.

See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for more information.