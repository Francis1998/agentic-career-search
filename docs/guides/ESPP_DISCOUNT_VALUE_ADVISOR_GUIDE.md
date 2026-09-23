        # EsppDiscountValueAdvisor Guide

        ![EsppDiscountValueAdvisor HITL flow](../../assets/demo/espp-discount-value-advisor.gif)

        Offline HITL advisor. Never auto-acts. Closes closed-UI gaps vs popular
        career tools.

        Optional later polish via **GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2**.

        Distinct from `EquityVestingCliffAdvisor` and `RsuRefreshCadenceAdvisor`.

        ## Usage

        ```python
from autoapply_agent.services.espp_discount_value import EsppDiscountValueAdvisor

report = EsppDiscountValueAdvisor().advise(
    contribution_usd=10_000.0,
    discount_pct=15.0,
)
assert report.auto_enroll is False
assert report.requires_human_review is True
print(report.value_band, report.estimated_value_usd)
```


        ## Safety

        Always `requires_human_review=True`. No HTTP. Humans decide. See `SAFETY.md`.
