# OfferExpirationUrgencyAdvisor Guide

![OfferExpirationUrgencyAdvisor HITL flow](../../assets/demo/offer-expiration-urgency-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Levels.fyi/Blind/Candor offer-expiration urgency planners.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from ``OfferDeadlineTracker` and `NegotiationTalkingPointsService``.

## Usage

```python
from autoapply_agent.services.offer_expiration_urgency import OfferExpirationUrgencyAdvisor

report = OfferExpirationUrgencyAdvisor().advise(
    days_until_expire=10.0,
    min_decision_days=7.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
