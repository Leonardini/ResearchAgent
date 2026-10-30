#!/usr/bin/env python3
"""Run skill-creator's eval viewer with one fix: escape "</" in the embedded data.

The viewer puts every output file into a <script> block as JSON. An output that is itself an
HTML page contains "</script>", which ends the viewer's script early and breaks the page (the
Demonstrator's demo pages do this). Same arguments as generate_review.py.
"""
import importlib.util
import sys
from pathlib import Path

VIEWER = Path.home() / ".claude/plugins/cache/claude-plugins-official/skill-creator/a0b04d9ddcca/skills/skill-creator/eval-viewer/generate_review.py"
spec = importlib.util.spec_from_file_location("generate_review", VIEWER)
gr = importlib.util.module_from_spec(spec)
sys.modules["generate_review"] = gr
spec.loader.exec_module(gr)
_original = gr.json.dumps


def _safe_dumps(obj, *args, **kwargs):
    return _original(obj, *args, **kwargs).replace("</", "<\\/")


gr.json.dumps = _safe_dumps  # json is imported as a module there; only the HTML embedding uses it for output
if __name__ == "__main__":
    gr.main()
