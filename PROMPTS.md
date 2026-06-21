# PROMPTS

Copy-paste prompts for recreating and upgrading repositories with an AI-agent-first focus.

## 1) Full Repo Recreation (AI-Agent Portfolio Mode)

```text
Create a new improved repository under my current workspace by recreating the core product behavior from an existing local repo path I provide.

Hard requirements:
1. Build a NEW standalone repo (do not modify the source repo).
2. Prioritize AI-agent engineering design and portfolio quality:
   - explicit Observe -> Decide -> Act loop
   - deterministic decision engine with rationale traces
   - optional LLM enrichment layer that consumes Gemini, Kimi, or Claude API responses
   - state-machine run lifecycle and durable event log
   - tool/adapters abstraction for external integrations
   - safety controls (timeouts, bounded scope, cancellation)
3. Use Python 3.11+, FastAPI, typed code, docstrings, pytest, ruff, mypy.
4. Include production-minded repo design:
   - src/, tests/, scripts/, CI workflow, env config, migrations scaffold
5. Include high-quality documentation:
   - README (showcase quality), QUICKSTART, CONFIGURATION, SAFETY, ARCHITECTURE
6. Push to GitHub remote and set About metadata (description, homepage, topics) to be clearly AI-agentic.
7. Validate with lint/type/tests before finalizing.

Execution style:
- Do not stop at planning.
- Implement end-to-end.
- Keep claims in docs aligned to actual code.
- Use concise but high-signal status updates while working.
```

## 2) Repo Upgrade (Agentic Positioning + Code Design)

```text
Upgrade this repository to be visibly AI-agent-first for portfolio use.

Scope:
- Strengthen architecture with an explicit decision engine layer.
- Persist agent decision traces (score, priority, rationale, matched terms).
- Improve API/event semantics for observability.
- Improve docs aggressively (README polish + architecture and safety docs).
- Improve GitHub About metadata to emphasize autonomous agent orchestration.

Constraints:
- Smallest correct diff; no unnecessary rewrites.
- Keep behavior deterministic and testable.
- Add/adjust tests for changed behavior.
- Run lint/type/tests and fix failures.

Tone for docs:
- confident, technical, showcase-ready.
- no fake claims.
```

## 3) README Polish (Fancy, Recruiter-Friendly)

```text
Rewrite README into a polished showcase page for an AI-agent systems project.

Include:
- hero statement + badges
- concise value proposition
- architecture flow diagram (mermaid)
- capabilities tied to actual implementation
- API map
- quick demo commands
- portfolio framing section (what this demonstrates technically)
- links to additional docs

Style:
- modern, scannable, strong technical branding
- short sections with clear headings
- avoid fluff and avoid claims not implemented in code
```

## 4) One-Line Prompt (Fast Start)

```text
Recreate this project as a new repo with stronger AI-agent architecture, deterministic decision tracing, production-grade docs/CI/tests, and push it to GitHub with polished About metadata and portfolio-ready README.
```

## 5) Branch-Safe Merge Prompt (Protect README and docs)

```text
Before making new changes, check the latest remote master/main and verify whether README or docs updates were overridden.

Branch strategy requirements:
1. Never merge directly from master/main into working changes.
2. Create a dedicated integration branch (for example: `merge/integration-readme-recovery`).
3. Pull latest master/main into that integration branch.
4. Auto-merge conflict resolution in favor of preserving the newest intended README/docs improvements.
5. If conflicts are non-trivial, resolve them explicitly and keep claims aligned to actual code.
6. Validate lint/type/tests after merge resolution.
7. Push the integration branch and merge from that branch into target branch via PR-style flow.

Output requirements:
- Show what changed in README/docs after merge.
- Confirm master/main was not directly merged into target without the integration branch.
```
