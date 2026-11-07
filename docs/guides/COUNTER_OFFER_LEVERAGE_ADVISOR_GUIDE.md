        # CounterOfferLeverageAdvisor Guide

        ![CounterOfferLeverageAdvisor HITL flow](../../assets/demo/counter-offer-leverage-advisor.gif)

        Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs popular
        career tools.

        Optional later polish via **GPT-6 Astra / Claude Opus 5.5 / Gemini 4 Argon / Kimi K3.1 Pro**.

        Distinct from `NegotiationTalkingPointsService` and `OfferDeadlineTracker`.

        ## Usage

        ```python
from autoapply_agent.services.counter_offer_leverage import CounterOfferLeverageAdvisor

report = CounterOfferLeverageAdvisor().advise(
    current_offer_tc=200_000.0,
    competing_offer_tc=230_000.0,
)
assert report.auto_send is False
assert report.requires_human_review is True
print(report.leverage_band, report.delta_pct)
```


        ## Safety

        Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
