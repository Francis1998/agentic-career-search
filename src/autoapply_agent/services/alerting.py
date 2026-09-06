"""Priority-tier webhook alerting helpers.

Posts a JSON payload to a configured webhook when a decision is marked
``priority_tier == "high"``. Failures are logged and never raised so a
flaky webhook cannot break an autonomous run.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from autoapply_agent.core.config import Settings, settings

logger = logging.getLogger(__name__)


def build_priority_alert_payload(
    *,
    run_id: str | None = None,
    job_title: str | None = None,
    job_url: str | None = None,
    company: str | None = None,
    score: float | None = None,
    priority_tier: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the JSON body sent to a priority alert webhook.

    Args:
        run_id: Optional run identifier for correlation.
        job_title: Optional job title.
        job_url: Optional posting URL.
        company: Optional company name.
        score: Optional relevance score.
        priority_tier: Decision priority tier.
        extra: Optional additional fields merged into the payload.

    Returns:
        JSON-serializable alert payload.
    """

    payload: dict[str, Any] = {
        "event": "priority.alert",
        "priority_tier": priority_tier,
        "run_id": run_id,
        "job_title": job_title,
        "job_url": job_url,
        "company": company,
        "score": score,
    }
    if extra:
        payload.update(extra)
    return payload


def should_send_priority_alert(
    priority_tier: str,
    *,
    config: Settings | None = None,
) -> bool:
    """Return True when alerting is enabled and the tier is high.

    Args:
        priority_tier: Decision priority tier.
        config: Optional settings override (defaults to global settings).

    Returns:
        Whether a webhook POST should be attempted.
    """

    active = config or settings
    if not active.priority_alert_webhook_enabled:
        return False
    if not active.priority_alert_webhook_url:
        return False
    return priority_tier == "high"


def send_priority_alert(
    priority_tier: str,
    *,
    run_id: str | None = None,
    job_title: str | None = None,
    job_url: str | None = None,
    company: str | None = None,
    score: float | None = None,
    extra: dict[str, Any] | None = None,
    config: Settings | None = None,
    client: httpx.Client | None = None,
) -> bool:
    """Synchronously POST a high-priority alert (fail-soft).

    Args:
        priority_tier: Decision priority tier.
        run_id: Optional run identifier.
        job_title: Optional job title.
        job_url: Optional posting URL.
        company: Optional company name.
        score: Optional relevance score.
        extra: Optional extra payload fields.
        config: Optional settings override.
        client: Optional httpx client (for tests).

    Returns:
        True when the webhook accepted the POST, otherwise False.
    """

    active = config or settings
    if not should_send_priority_alert(priority_tier, config=active):
        return False

    payload = build_priority_alert_payload(
        run_id=run_id,
        job_title=job_title,
        job_url=job_url,
        company=company,
        score=score,
        priority_tier=priority_tier,
        extra=extra,
    )
    owns_client = client is None
    http_client = client or httpx.Client(timeout=active.priority_alert_webhook_timeout_seconds)
    try:
        response = http_client.post(active.priority_alert_webhook_url or "", json=payload)
        response.raise_for_status()
        logger.info(
            "Priority alert webhook delivered for tier=%s title=%s",
            priority_tier,
            job_title,
        )
        return True
    except Exception as exc:
        logger.warning(
            "Priority alert webhook failed (fail-soft): %s",
            exc,
        )
        return False
    finally:
        if owns_client:
            http_client.close()


async def send_priority_alert_async(
    priority_tier: str,
    *,
    run_id: str | None = None,
    job_title: str | None = None,
    job_url: str | None = None,
    company: str | None = None,
    score: float | None = None,
    extra: dict[str, Any] | None = None,
    config: Settings | None = None,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Asynchronously POST a high-priority alert (fail-soft).

    Intended as a thin hook for the worker loop. Failures are logged and
    never propagate so webhook issues cannot fail a run.

    Args:
        priority_tier: Decision priority tier.
        run_id: Optional run identifier.
        job_title: Optional job title.
        job_url: Optional posting URL.
        company: Optional company name.
        score: Optional relevance score.
        extra: Optional extra payload fields.
        config: Optional settings override.
        client: Optional async httpx client (for tests).

    Returns:
        True when the webhook accepted the POST, otherwise False.
    """

    active = config or settings
    if not should_send_priority_alert(priority_tier, config=active):
        return False

    payload = build_priority_alert_payload(
        run_id=run_id,
        job_title=job_title,
        job_url=job_url,
        company=company,
        score=score,
        priority_tier=priority_tier,
        extra=extra,
    )
    owns_client = client is None
    http_client = client or httpx.AsyncClient(timeout=active.priority_alert_webhook_timeout_seconds)
    try:
        response = await http_client.post(active.priority_alert_webhook_url or "", json=payload)
        response.raise_for_status()
        logger.info(
            "Priority alert webhook delivered (async) for tier=%s title=%s",
            priority_tier,
            job_title,
        )
        return True
    except Exception as exc:
        logger.warning(
            "Priority alert webhook failed async (fail-soft): %s",
            exc,
        )
        return False
    finally:
        if owns_client:
            await http_client.aclose()
