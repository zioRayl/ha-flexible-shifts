from pathlib import Path

import yaml


def test_addon_is_available_to_non_admin_users():
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "flexible_shifts" / "config.yaml").read_text())
    assert config["version"] == "0.3.0"
    assert config["ingress"] is True
    assert config["panel_admin"] is False
