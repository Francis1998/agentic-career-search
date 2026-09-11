# Offer Deadline Tracker Guide

![Offer deadline tracker HITL flow](../../assets/demo/offer-deadline-tracker.gif)

Generate deterministic, offline **offer deadline countdowns and HITL reminders**.
Never auto-declines. Closes the gap vs Teal/Huntr offer trackers that lack
local deadline countdowns and urgency reminders.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.
The countdown itself stays deterministic.

## Why this exists

Teal and Huntr track offers, but few open-source career agents expose a local
deadline countdown with explicit urgency and human-review reminders. This
service always sets `requires_human_review=True`, keeps `auto_decline=False`,
and performs no network I/O.

## Usage

```python
from autoapply_agent.services.offer_deadline import OfferDeadlineTracker

status = OfferDeadlineTracker().track(
    company="Acme",
    role="Platform Engineer",
    deadline_iso="2026-09-15",
    now_iso="2026-09-11",
)
assert status.requires_human_review is True
assert status.auto_decline is False
print(status.days_remaining, status.urgency)
print(status.reminders)
```

Urgency values: `overdue`, `due_today`, `due_soon` (1–3 days), `upcoming`.

## Safety

Always `requires_human_review=True` and `auto_decline=False`. No HTTP. Humans
decide accept / counter / decline manually. See `SAFETY.md`.
