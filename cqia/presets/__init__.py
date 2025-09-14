from __future__ import annotations
from pathlib import Path
import yaml

DEFAULT_RULES = {
    "complexity": {"warn_at": 10, "p1_cutoff": 15, "p0_cutoff": 20},
    "duplication": {"k_shingle": 7, "similarity_threshold": 0.90},
    "weights": {
        "security": 1.0, "complexity": 0.6, "duplication": 0.5,
        "performance": 0.6, "documentation": 0.3, "testing": 0.7,
    },
}

def load_rules(rules_path: Path | None) -> dict:
    if not rules_path:
        p = Path("presets/rules.yaml")
    else:
        p = rules_path
    if p.exists():
        try:
            return yaml.safe_load(p.read_text(encoding="utf-8")) or DEFAULT_RULES
        except Exception:
            return DEFAULT_RULES
    return DEFAULT_RULES

def save_rules(rules: dict, rules_path: Path | None) -> Path:
    p = rules_path or Path("presets/rules.yaml")
    p.parent.mkdir(parents=True, exist_ok=True)
    import yaml
    p.write_text(yaml.safe_dump(rules, sort_keys=False), encoding="utf-8")
    return p
