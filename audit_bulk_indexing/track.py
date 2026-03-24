import json
import logging
from typing import Dict

logger = logging.getLogger(__name__)

INDEX_NAME = "audit-bench"

_BULK_BODY_CACHE: Dict[int, str] = {}


def _build_bulk_body(bulk_size: int) -> str:
    cached = _BULK_BODY_CACHE.get(bulk_size)
    if cached is not None:
        return cached

    lines = []
    for i in range(bulk_size):
        lines.append(json.dumps({"index": {"_index": INDEX_NAME}}))
        lines.append(
            json.dumps(
                {
                    "@timestamp": "2024-01-01T00:00:00.000Z",
                    "message": "test",
                    "counter": i,
                }
            )
        )
    body = "\n".join(lines) + "\n"
    _BULK_BODY_CACHE[bulk_size] = body
    return body


async def toggle_audit(es, params):
    """
    Toggle which audit events are emitted.

    Requires Elasticsearch to be started with `xpack.security.audit.enabled: true` (static),
    but can change event selection at runtime (dynamic cluster setting).
    """
    audit_mode = params.get("audit_mode", "on")

    if audit_mode == "on":
        include = ["access_granted"]
        exclude = []
    elif audit_mode == "off":
        include = []
        exclude = ["_all"]
    else:
        raise ValueError(f"Unknown audit_mode [{audit_mode}]. Expected 'on' or 'off'.")

    body = {
        "transient": {
            "xpack.security.audit.logfile.events.include": include,
            "xpack.security.audit.logfile.events.exclude": exclude,
        }
    }
    await es.cluster.put_settings(body=body)
    return {"weight": 1, "unit": "ops", "success": True}


async def bulk_index_trivial(es, params):
    bulk_size = int(params.get("bulk_size", 1000))
    if bulk_size <= 0:
        raise ValueError(f"bulk_size must be > 0 but was [{bulk_size}]")

    body = _build_bulk_body(bulk_size)
    resp = await es.bulk(body=body, refresh=False)

    success = True
    if isinstance(resp, dict) and resp.get("errors") is True:
        success = False
        first_err = next(
            (item for item in resp.get("items", []) if "error" in item.get("index", {})),
            None,
        )
        logger.warning("bulk_index_trivial: bulk response contained errors; first: %s", first_err)

    return {"weight": bulk_size, "unit": "docs", "success": success}


def register(registry):
    registry.register_runner("toggle_audit", toggle_audit, async_runner=True)
    registry.register_runner("bulk_index_trivial", bulk_index_trivial, async_runner=True)

