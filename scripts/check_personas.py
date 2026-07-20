"""CI gate for `personas/*.md` PRs: validate frontmatter has name/style/
risk_appetite and the prompt body isn't empty. Exits non-zero on any
failure so a red check blocks merge; passes with an empty diff (nothing
to check) so it's a no-op on unrelated PRs.

    python scripts/check_personas.py [files...]   # defaults to all personas/*.md
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_FIELDS = ("name", "style", "risk_appetite")


def check_file(path: Path) -> list[str]:
    errors = []
    text = path.read_text(encoding="utf-8")

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, flags=re.DOTALL)
    if not match:
        return [f"{path}: missing --- frontmatter block"]

    frontmatter_raw, body = match.groups()
    try:
        frontmatter = yaml.safe_load(frontmatter_raw) or {}
    except yaml.YAMLError as exc:
        return [f"{path}: invalid frontmatter YAML: {exc}"]

    for field in REQUIRED_FIELDS:
        if not str(frontmatter.get(field, "")).strip():
            errors.append(f"{path}: frontmatter missing required field '{field}'")

    if not body.strip():
        errors.append(f"{path}: prompt body is empty")

    return errors


def main(argv: list[str]) -> int:
    files = [Path(f) for f in argv] if argv else sorted((ROOT / "personas").glob("*.md"))
    if not files:
        print("no persona files to check")
        return 0

    all_errors = []
    for f in files:
        all_errors.extend(check_file(f))

    if all_errors:
        for e in all_errors:
            print(f"::error::{e}")
        print(f"\n{len(all_errors)} problem(s) found.")
        return 1

    print(f"{len(files)} persona file(s) OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
