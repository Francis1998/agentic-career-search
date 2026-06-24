#!/usr/bin/env python3
"""Health check script for agentic-career-search."""

import json
import sys
from urllib import error, request

BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT_SECONDS = 5.0
HEALTH_ENDPOINTS = (("/health/live", "liveness"), ("/health/ready", "readiness"))


def check_health(
    base_url: str = BASE_URL,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
) -> bool:
    """Check the service liveness and readiness endpoints."""

    normalized_base_url = base_url.rstrip("/")
    for endpoint_path, probe_name in HEALTH_ENDPOINTS:
        endpoint_url = f"{normalized_base_url}{endpoint_path}"
        try:
            with request.urlopen(endpoint_url, timeout=timeout) as response:
                status_code = int(response.status)
                data = json.loads(response.read().decode("utf-8"))
        except error.URLError:
            print(f"✗ Service {probe_name} probe not reachable: {endpoint_url}")
            return False
        except (TimeoutError, json.JSONDecodeError):
            print(f"✗ Service {probe_name} probe returned an invalid response")
            return False

        if status_code != 200:
            print(f"✗ Service {probe_name} probe unhealthy: {status_code}")
            return False
        print(f"✓ Service {probe_name} probe healthy: {data}")

    return True


if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)
