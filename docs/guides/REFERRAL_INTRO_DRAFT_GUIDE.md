# Referral Intro Draft Guide

![Referral intro draft HITL flow](../../assets/demo/referral-intro-draft.gif)

Generate deterministic, offline **warm-intro email / LinkedIn drafts** for human
review. Never auto-sends. Closes the gap vs LinkedIn InMail templates and
Teal/Huntr referral trackers that either fire messages or leave intros unstructured.

Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.
The draft itself stays deterministic.

## Why this exists

LinkedIn InMail and Easy Apply can auto-send; Teal tracks referrals without a
testable HITL draft primitive. This service always sets
`requires_human_review=True` and performs no network I/O.

## Usage

```python
from autoapply_agent.services.referral_intro import ReferralIntroDraftService

draft = ReferralIntroDraftService().generate(
    company="Nimbus",
    role="ML Engineer",
    connector_name="Jordan",
    mutual_context="same ML reading group",
    channel="email",
)
assert draft.requires_human_review is True
print(draft.subject)
print(draft.body)
print(draft.talking_points)
```

Supported channels: `email`, `linkedin`.

## Safety

Always `requires_human_review=True`. No HTTP. Make it easy for connectors to
decline. Humans edit and send manually. See `SAFETY.md`.
