# GreenCardSponsorshipTimelineAdvisor Guide

![GreenCardSponsorshipTimelineAdvisor HITL flow](../../assets/demo/green-card-sponsorship-timeline-advisor.gif)

Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs Boundless/MyVisaJobs/Trackitt green-card sponsorship timeline planners.

Optional later polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

Distinct from `VisaTimelineGapAdvisor` and `H1bLotteryOddsAdvisor`.

## Usage

```python
from autoapply_agent.services.green_card_sponsorship_timeline import (
    GreenCardSponsorshipTimelineAdvisor,
)

report = GreenCardSponsorshipTimelineAdvisor().advise(
    sponsored_months=48.0,
    wait_months=36.0,
)
assert report.auto_enroll is False
print(report.coverage_band)
```

## Safety

Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
