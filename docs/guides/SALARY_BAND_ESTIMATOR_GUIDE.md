# Salary Band Estimator Guide

![Salary band estimator](../../assets/demo/salary-band-estimator.gif)

Estimate a **non-authoritative USD salary band** (low / mid / high) from job
title seniority tokens and location / remote heuristics. Pure deterministic
math — no market API scraping.

Optional later calibration can use GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x /
Kimi K2 for narrative rationale polish. The estimator itself stays offline.

## Why this exists

Teal and Levels.fyi-style tools surface compensation signals in product UIs.
JobSpy scrapes salary fields inconsistently and does not estimate missing
bands. OpenHands is the wrong default for compensation advice. This service
fills the gap with an explicit, auditable heuristic band for triage.

## Estimate a band

```python
from autoapply_agent.services.salary_band import SalaryBandEstimator

estimate = SalaryBandEstimator().estimate(
    job_title="Senior Backend Engineer",
    location="San Francisco, CA",
    job_text="Remote-friendly backend role.",
)

print(estimate.low, estimate.mid, estimate.high)
print(estimate.level, estimate.confidence)
print(estimate.rationale)
```

## What you get

| Field | Purpose |
|---|---|
| `low` / `mid` / `high` | USD band (±15% around adjusted mid) |
| `level` | Parsed seniority bucket |
| `location_factor` | Multiplier from location/remote tokens |
| `confidence` | Heuristic confidence in `[0.0, 1.0]` |
| `rationale` | Auditable explanation lines |

## Safety notes

- Estimates are assistive triage signals, not offers or legal advice.
- No external salary API calls; do not treat output as market truth.
- Keep personal compensation data out of shared logs.

See `SAFETY.md` for project-wide boundaries.
