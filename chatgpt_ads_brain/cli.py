"""Source-checkout convenience dispatcher; the portable ZIP is the supported distribution."""
import argparse, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def list_skills():
    skills_dir = ROOT / "skills"
    skills = []
    for d in sorted(skills_dir.iterdir()):
        skill_file = d / "SKILL.md"
        if d.is_dir() and skill_file.exists():
            desc = "Specialized advertising skill"
            for line in skill_file.read_text().splitlines():
                if line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip()
                    break
            skills.append((d.name, desc))
    print(f"\nAvailable ChatGPT Ads Skills ({len(skills)} registered):")
    for name, desc in skills:
        print(f"  - {name:<25} : {desc}")
    print("\nOrchestrator: skills/chatgpt-ads/SKILL.md")
    return 0

def main(argv=None):
    p = argparse.ArgumentParser(description='ChatGPT Ads local tools')
    p.add_argument('command', choices=['query', 'knowledge', 'operate', 'validate', 'doctor', 'list-skills'])
    p.add_argument('arguments', nargs=argparse.REMAINDER)
    a = p.parse_args(argv)
    if a.command == 'list-skills':
        return list_skills()
    scripts = {
        'query': 'query_brain.py',
        'knowledge': 'knowledge_core.py',
        'operate': 'operating_core.py',
        'validate': 'validate_pack.py',
        'doctor': 'doctor.py'
    }
    return subprocess.call([sys.executable, str(ROOT / 'scripts' / scripts[a.command]), *a.arguments])

if __name__ == '__main__':
    raise SystemExit(main())
