from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional, Sequence


PROMPTS_DIR = Path("prompts")


def compose_task_prompts(
    frames_dir: Path,
    transcript: str,
    user_prompt: str,
    frames: Optional[Sequence[Path]] = None,
) -> Dict[str, str]:
    base = (PROMPTS_DIR / "base.system.md").read_text(encoding="utf-8")
    def _read(name: str) -> str:
        return (PROMPTS_DIR / "modules" / f"{name}.md").read_text(encoding="utf-8")

    if frames is not None:
        frames_list = [str(p) for p in frames]
    else:
        frames_list = sorted([str(p) for p in frames_dir.glob("*.jpg")])
    frames_hint = "\n".join(frames_list[:12])

    shared = f"\n[FRAMES]\n{frames_hint}\n[TRANSCRIPT]\n{transcript[:4000]}\n"

    tasks = {
        "role_archetype": _read("role_archetype"),
        "face_visibility": _read("face_visibility"),
        "scene_type": _read("scene_type"),
        "positions": _read("positions"),
    }

    composed: Dict[str, str] = {}
    for k, v in tasks.items():
        composed[k] = base + "\n" + v + shared
        if user_prompt:
            composed[k] += "\n[USER_PROMPT]\n" + user_prompt
    return composed


def compose_name_prompt(tags: Dict[str, Any], user_prompt: str, n_candidates: int) -> str:
    generator = (PROMPTS_DIR / "modules" / "name_generator.md").read_text(encoding="utf-8")
    base = (PROMPTS_DIR / "base.system.md").read_text(encoding="utf-8")
    content = base + "\n" + generator + f"\n[TAGS]\n{tags}\n[N]\n{n_candidates}\n"
    if user_prompt:
        content += "\n[USER_PROMPT]\n" + user_prompt
    return content

