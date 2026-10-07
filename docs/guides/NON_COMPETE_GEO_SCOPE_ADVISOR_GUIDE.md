# NonCompeteGeoScopeAdvisor Guide

![NonCompeteGeoScopeAdvisor HITL flow](../../assets/demo/noncompete-geo-scope-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Clerky/Blind/Levels.fyi non-compete geographic-scope planners.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `NoncompeteFlagger` and `OfferDeadlineAdvisor`.

## Usage

```python
from autoapply_agent.services.noncompete_geo_scope import NonCompeteGeoScopeAdvisor

report = NonCompeteGeoScopeAdvisor().advise(
    restricted_radius_miles=80.0,
    acceptable_radius_miles=50.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
