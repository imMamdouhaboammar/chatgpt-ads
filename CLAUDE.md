# Claude Code & Marketplace Entrypoint

This repository is configured as a native Claude Plugin and Marketplace package via `marketplace.json`, `.claude-plugin/plugin.json`, and the root `SKILL.md` orchestrator.

## Quickstart for Claude Code

1. Read [AGENTS.md](AGENTS.md) and [SKILL.md](SKILL.md).
2. For runtime-specific adapters and headless execution guidance, consult [runtime/claude.md](runtime/claude.md).
3. The package exposes 12 specialized advertising skills under [skills/](skills/) covering research, planning, creative, measurement, monitor, and policy.

## Claude Marketplace & Plugin Configuration

- Marketplace Manifest: `marketplace.json` (Claude Plugin schema)
- Plugin Manifest: `.claude-plugin/plugin.json`
- Universal Link: `install.sh` automatically installs the skill to `~/.claude/skills/chatgpt-ads`

## Claude Commands

```bash
# Query knowledge base
python3 -m chatgpt_ads_brain query "creative policy"

# Run complete deterministic verification
python3 scripts/validate_pack.py
python3 -m unittest discover -s tests -p "test_*.py"
```
