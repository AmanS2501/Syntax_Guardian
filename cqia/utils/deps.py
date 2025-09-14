from __future__ import annotations
from typing import Any, Dict, List, Tuple

def safe_dep_metrics(res: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize dependency metrics to simple JSON-safe, scalar formats:
    - fan_in, fan_out: dict[str, int]
    - top_fan_in, top_fan_out: list[tuple[str, int]]
    - cycles: list[list[str]]
    Accepts either res['dep_metrics'] or res['dependencies']['metrics'].
    """
    metrics = (res.get("dep_metrics") or res.get("dependencies", {}).get("metrics", {}) or {}).copy()

    fan_in = metrics.get("fan_in", {}) or {}
    fan_out = metrics.get("fan_out", {}) or {}
    top_fan_in = metrics.get("top_fan_in", []) or []
    top_fan_out = metrics.get("top_fan_out", []) or []
    cycles = metrics.get("cycles", []) or []

    def _as_int(v) -> int:
        try:
            if isinstance(v, (list, tuple)):
                if len(v) > 1:
                    return int(v[1])
                if len(v) == 1:
                    return int(v)
                return 0
            return int(v)
        except Exception:
            return 0

    fan_in = {str(k): _as_int(v) for k, v in fan_in.items()}
    fan_out = {str(k): _as_int(v) for k, v in fan_out.items()}

    def _pairize(items) -> List[Tuple[str, int]]:
        out: List[Tuple[str, int]] = []
        for item in items:
            try:
                n, v = item
            except Exception:
                n, v = item, 0
            out.append((str(n), _as_int(v)))
        return out

    metrics["fan_in"] = fan_in
    metrics["fan_out"] = fan_out
    metrics["top_fan_in"] = _pairize(top_fan_in)
    metrics["top_fan_out"] = _pairize(top_fan_out)
    metrics["cycles"] = [[str(x) for x in cyc] for cyc in cycles]
    return metrics
