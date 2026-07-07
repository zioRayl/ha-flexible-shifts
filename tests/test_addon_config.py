from pathlib import Path

import yaml


def test_addon_is_available_to_non_admin_users():
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "flexible_shifts" / "config.yaml").read_text())
    assert config["version"] == "0.4.0"
    assert config["ingress"] is True
    assert config["panel_admin"] is False


def test_user_colors_and_responsive_breakpoints_are_present():
    root = Path(__file__).resolve().parents[1]
    css = (root / "flexible_shifts" / "app" / "static" / "styles.css").read_text()
    js = (root / "flexible_shifts" / "app" / "static" / "app.js").read_text()
    assert "--user-color" in css
    assert "@media (max-width: 1100px)" in css
    assert "@media (max-width: 900px)" in css
    assert "@media (max-width: 600px)" in css
    assert "safeUserColor" in js
    assert "userColor" in js
