# Referral Intro Draft Guide

![Referral intro draft HITL flow](../../assets/demo/referral-intro-draft.gif)

Generate deterministic, offline **warm-intro email / direct-message drafts** for
human review. Never auto-sends. Closes the gap vs networking-site auto-templates and
Teal/Huntr referral trackers that either fire messages or leave intros unstructured.

Optional later polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.
The draft itself stays deterministic.

## Why this exists

Networking-site templates and one-click apply flows can auto-send; Teal tracks
referrals without a testable HITL draft primitive. This service always sets
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

Supported channels: `email`, `dm` (direct message).

## Safety

Always `requires_human_review=True`. No HTTP. Make it easy for connectors to
decline. Humans edit and send manually. See `SAFETY.md`.
