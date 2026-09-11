# OpenAI Codex & ChatGPT Plugin Entrypoint

This repository is configured as a native OpenAI Codex and ChatGPT Plugin via `.codex-plugin/plugin.json` and the root `SKILL.md` orchestrator.

## Quickstart for Codex

1. Review the operating contract in [AGENTS.md](AGENTS.md) and [SKILL.md](SKILL.md).
2. The orchestrator routes queries across 12 specialized advertising skills located under [skills/](skills/).
3. For runtime-specific adapters and headless execution guidance, consult [runtime/codex.md](runtime/codex.md).

## Plugin Manifest

The plugin configuration is located at `.codex-plugin/plugin.json`:
- Entrypoint: `SKILL.md`
- Skills catalog: `skills/`
- Guarded local execution: `scripts/operating_core.py` and `scripts/knowledge_core.py`

## Codex Commands

```bash
# Query sourced ChatGPT advertising knowledge
python3 -m chatgpt_ads_brain query "attribution modeling"

# Validate package integrity
python3 scripts/validate_pack.py

# Check system capabilities
python3 scripts/doctor.py
```
