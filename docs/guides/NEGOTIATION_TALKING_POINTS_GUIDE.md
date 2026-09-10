# Negotiation Talking Points Guide

![Negotiation talking points HITL flow](../../assets/demo/negotiation-talking-points.gif)

Generate deterministic, offline **compensation counter-offer talking points**
for human review. Never submits counters or emails recruiters. Closes the gap
vs Levels.fyi / Blind threads and Teal offer trackers that leave candidates to
improvise.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.
The points themselves stay deterministic.

## Why this exists

Levels.fyi and Blind provide market anecdotes; Teal tracks offers. Few open-source
career agents produce auditable counter-offer talking points with an explicit
HITL gate. This service always sets `requires_human_review=True` and performs
no network I/O.

## Usage

```python
from autoapply_agent.services.negotiation_talking import NegotiationTalkingPointsService

points = NegotiationTalkingPointsService().generate(
    company="Acme",
    role="Platform Engineer",
    current_total_usd=190_000,
    target_total_usd=215_000,
    leverage_notes="Competing offer from Nimbus",
)
assert points.requires_human_review is True
print(points.talking_points)
print(points.risks)
```

## Safety

Always `requires_human_review=True`. No HTTP. Never invent competing offers.
Humans edit and send manually. See `SAFETY.md`.
