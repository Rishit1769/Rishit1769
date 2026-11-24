"""Generate the complete universe atomically after all API calls succeed."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from xml.etree import ElementTree as ET

from .data import collect, collect_public_preview
from .github_client import GitHubClient
from .svg import solar, profile_card, project_card, languages_card, contributions_card, pending_contributions, esc


ROOT = Path(__file__).resolve().parents[1]


def moon_table(pinned):
    lines = ["<table>"]
    for index, item in enumerate(pinned, 1):
        url = item["url"]
        if not url.startswith("https://github.com/"):
            raise ValueError("Unexpected pinned repository URL")
        if index % 2:
            lines.append("  <tr>")
        lines.append(
            f'    <td width="50%"><a href="{esc(url)}"><img src="assets/moons/{index:02d}.svg" '
            f'width="340" alt="{esc(item["name"])} project card"></a></td>'
        )
        if index % 2 == 0:
            lines.append("  </tr>")
    if len(pinned) % 2:
        lines.extend(['    <td width="50%"></td>', "  </tr>"])
    return lines + ["</table>", ""]


def render_readme(snapshot, config):
    pinned = snapshot["pinned"]
    pro = config["professional"]
    lines = [
        '<div align="center">',
        '',
        '# RISHIT SINGH',
        '',
        '**Software Engineer × ML Engineer**',
        '',
        'Building products, systems, infrastructure & intelligent software.',
        '',
        '</div>',
        '',
        '## 01 / Solar System',
        '',
        '![Animated developer solar system](assets/solar-system.svg)',
        '',
        'Sun = Developer · Planets = Languages · Moons = Repositories · Comets = Recent pushes',
        '',
        '## 02 / The Sun',
        '',
        '![Developer profile card](assets/the-sun.svg)',
        '',
        pro["bio"],
        '',
        '## 03 / Major Moons',
        '',
    ]
    if not snapshot.get("authenticated", True):
        lines.extend(['Pinned repositories will appear after the first authenticated workflow run.', ''])
    elif pinned:
        lines.extend(moon_table(pinned))
    else:
        lines.extend(['No repositories are currently pinned on GitHub.', ''])
    lines.extend([
        '## 04 / Planetary Composition', '',
        '![Programming language statistics](assets/planets.svg)', '',
        'Percentages are calculated from language bytes in public, owned, non-fork, non-archived repositories.', '',
        '## 05 / Orbit Log', '',
        '![GitHub contribution dashboard](assets/orbit-log.svg)', '',
        'The heatmap shows the latest 26 weeks. The current streak includes today when active, otherwise yesterday. '
        'The longest streak is measured over the fetched current calendar year. GitHub reports contribution days in its calendar timezone.', '',
        '## 06 / Space Stations', '',
    ])
    for station in config["stations"]:
        lines.extend([f'**{station["name"]}** · {" · ".join(station["items"])}', ''])
    lines.extend([
        '## 07 / Mission Log', '',
        '**2024 → 2028 · Bachelor of Engineering, Artificial Intelligence & Data Science**',
        'Thakur College of Engineering & Technology, Mumbai, India', '',
        '**Full Stack Web Development Intern · Unified Mentor**',
        'Worked on production-oriented full-stack applications across frontend, backend, databases, APIs, infrastructure and deployment. '
        'Projects included RakshaAI and AI Financial Habit Builder.', '',
        '## 08 / Establish Contact', '',
        '[Portfolio](https://rishitcodes.in) · [LinkedIn](https://www.linkedin.com/in/rishit-singh-586742361/) · '
        '[GitHub](https://github.com/rishit1769)', '',
        '`TRANSMISSION END // KEEP BUILDING`', ''
    ])
    return "\n".join(lines)


def generate(snapshot, config, root=ROOT):
    outputs = {
        root / "assets/solar-system.svg": solar(snapshot, config),
        root / "assets/the-sun.svg": profile_card(snapshot, config),
        root / "assets/planets.svg": languages_card(snapshot),
        root / "assets/orbit-log.svg": contributions_card(snapshot) if snapshot.get("authenticated", True) else pending_contributions(),
    }
    for i, item in enumerate(snapshot["pinned"], 1):
        outputs[root / f"assets/moons/{i:02d}.svg"] = project_card(item, i)
    outputs[root / "README.md"] = render_readme(snapshot, config)
    for path, content in outputs.items():
        if path.suffix == ".svg":
            ET.fromstring(content)
        if "GITHUB_TOKEN" in content or (os.getenv("GITHUB_TOKEN") and os.getenv("GITHUB_TOKEN") in content):
            raise ValueError("Credential-like content in output")
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(content, encoding="utf-8")
        temp.replace(path)
    wanted = {p.name for p in outputs if p.parent == root / "assets/moons"}
    for stale in (root / "assets/moons").glob("*.svg"):
        if stale.name not in wanted:
            stale.unlink()
    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "data/config.json"))
    parser.add_argument("--public-preview", action="store_true", help="Generate public-data preview; pins and contributions await authenticated run")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    snapshot = collect_public_preview(GitHubClient(), config) if args.public_preview else collect(GitHubClient(), config)
    generate(snapshot, config)
    print(f'Generated universe for {config["username"]} from GitHub data')


if __name__ == "__main__":
    main()
