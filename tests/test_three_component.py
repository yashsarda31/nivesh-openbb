"""Build and safety contracts for the local Three.js/GSAP component."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_frontend_dependencies_are_exactly_pinned() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    assert package["devDependencies"] == {
        "esbuild": "0.28.2",
        "gsap": "3.15.0",
        "three": "0.185.1",
    }


def test_readable_source_uses_ccv2_and_safe_dom_updates() -> None:
    source = (ROOT / "component_frontend/src/towers.js").read_text(encoding="utf-8")

    assert "export default function" in source
    assert "parentElement" in source
    assert "textContent" in source
    assert "innerHTML" not in source
    assert "Streamlit." not in source
    assert "window.Streamlit" not in source


def test_built_artifact_is_local_interactive_and_disposable() -> None:
    artifact = (
        ROOT / "nivesh/components/assets/towers.js"
    ).read_text(encoding="utf-8")

    for marker in (
        "WebGLRenderer",
        "prefers-reduced-motion",
        "requestAnimationFrame",
        "cancelAnimationFrame",
        "ResizeObserver",
        ".dispose",
    ):
        assert marker in artifact
    assert 'from"three"' not in artifact
    assert "from 'three'" not in artifact
    assert "cdn.jsdelivr" not in artifact
    assert "unpkg.com" not in artifact


def test_python_wrapper_uses_only_components_v2() -> None:
    wrapper = (
        ROOT / "nivesh/components/financial_towers.py"
    ).read_text(encoding="utf-8")

    assert "st.components.v2.component" in wrapper
    assert "components.v1" not in wrapper
    assert "declare_component" not in wrapper
