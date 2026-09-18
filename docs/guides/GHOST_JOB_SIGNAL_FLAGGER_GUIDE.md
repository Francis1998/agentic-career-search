# Ghost Job Signal Flagger Guide

![Ghost job signal flagger HITL flow](../../assets/demo/ghost-job-signal-flagger.gif)

Flag evergreen / vague-comp / repost ghost-job cues from JD text. Never
auto-applies. Closes the Teal / Simplify / Huntr ghost-listing gap.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

Distinct from `JobPostingFreshnessScorer` and `ApplicationGhostingDetector`.

## Usage

```python
from autoapply_agent.services.ghost_job import GhostJobSignalFlagger

report = GhostJobSignalFlagger().flag(
    "We are always hiring on a rolling basis for our talent community."
)
assert report.auto_apply is False
assert report.requires_human_review is True
print(report.risk_band, report.risk_score, [s.kind for s in report.signals])
```

## Safety

Always `requires_human_review=True` and `auto_apply=False`. No HTTP. Humans
decide whether to apply. See `SAFETY.md`.
