
from __future__ import annotations
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
import pathlib

def render_markdown(spec: Dict[str, Any], template_name: str = "prd.md.j2") -> str:
    base = pathlib.Path(__file__).resolve().parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(base)), autoescape=select_autoescape())
    tmpl = env.get_template(template_name)
    return tmpl.render(spec=spec)
