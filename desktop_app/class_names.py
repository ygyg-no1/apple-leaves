from pathlib import Path

import yaml

from desktop_app.paths import DATA_YAML


def load_class_names():
    path = Path(DATA_YAML)
    if path.is_file():
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            names = data.get("names") or {}
            if isinstance(names, dict):
                return [names[i] for i in sorted(names, key=int)]
            if isinstance(names, list):
                return names
        except Exception:
            pass
    return [
        "Apple__BlackRot",
        "Apple__CedarRust",
        "Apple__Healthy",
        "Apple__Scab",
    ]
