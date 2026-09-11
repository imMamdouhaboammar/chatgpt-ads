# ChatGPT Ads

![ChatGPT Ads: Research. Plan. Create. Measure.](assets/chatgpt-ads-cover.webp)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v0.4.0-success.svg)](https://github.com/imMamdouhaboammar/chatgpt-ads/releases)
[![CI](https://github.com/imMamdouhaboammar/chatgpt-ads/actions/workflows/ci.yml/badge.svg)](https://github.com/imMamdouhaboammar/chatgpt-ads/actions/workflows/ci.yml)
[![Claude Plugin](https://img.shields.io/badge/Claude-Marketplace%20Ready-purple.svg)](marketplace.json)
[![OpenAI Codex](https://img.shields.io/badge/OpenAI-Codex%20Plugin-green.svg)](.codex-plugin/plugin.json)
[![Skills.sh](https://img.shields.io/badge/Skills.sh-Registered-orange.svg)](.skills.json)
[![Bun](https://img.shields.io/badge/Bun-1.3+-fbf0df.svg?logo=bun)](package.json)

An independent, MIT-licensed universal knowledge and operating-skill pack for research, planning, creative, measurement, analysis, and guarded ChatGPT Ads workflows. Authored and maintained by **Mamdouh Aboammar**.

It provides zero-vendor-lockin multi-agent support across **OpenAI Codex**, **Claude Code / Desktop**, **Google Antigravity / Gemini CLI**, **Cursor**, and **Skills.sh**. It is not an official OpenAI product, integration, or live endorsement.

---

## Architecture & Workflow Engine

```mermaid
flowchart TD
    User["User Intent / Advertising Brief"] --> Router["SKILL.md Master Orchestrator"]

    subgraph Hub ["Universal Agent Connectors"]
        Claude["Claude Code & Marketplace"]
        Codex["OpenAI Codex Plugin"]
        Cursor["Skills.sh & Cursor Hub"]
        Gemini["Antigravity & Gemini CLI"]
    end

    Hub --> Router

    subgraph Skills ["ChatGPT Ads Domain Skills"]
        Router --> Research["chatgpt-ads-research"]
        Router --> Readiness["chatgpt-ads-readiness"]
        Router --> Plan["chatgpt-ads-plan"]
        Router --> Creative["chatgpt-ads-creative"]
        Router --> Measurement["chatgpt-ads-measurement"]
        Router --> Operate["chatgpt-ads-operate"]
        Router --> Monitor["chatgpt-ads-monitor"]
        Router --> Policy["chatgpt-ads-policy"]
    end

    subgraph Core ["Guarded Runtime & Knowledge Engine"]
        Research --> Ledger["Sourced Evidence Ledger"]
        Operate --> SafeIO["scripts/safe_io.py (O_NOFOLLOW)"]
        SafeIO --> Locks["Local Checkpoint Locks"]
    end
```

---

## Multi-Agent Installation & Distribution

Install and distribute across your preferred AI agent environment:

### 1. Claude Code & Claude Desktop
Install directly via Claude Code or register through the marketplace manifest:
```bash
# Register via marketplace.json or link directly
mkdir -p ~/.claude/skills && cp -r . ~/.claude/skills/chatgpt-ads
```

### 2. Skills.sh (Vercel & Multi-Agent)
```bash
npx skills add imMamdouhaboammar/chatgpt-ads
```

### 3. OpenAI Codex Plugin
Configured natively through [.codex-plugin/plugin.json](.codex-plugin/plugin.json). Point Codex directly to this repository or copy to `~/.codex/skills/chatgpt-ads`.

### 4. Universal One-Liner Installer
Automatically detects and installs into Claude Code, Antigravity/Gemini CLI, Codex, and Universal Agent Kernel (`~/.agents/skills`):
```bash
./install.sh
```

### 5. Bun & Node CLI
```bash
# Run commands directly with Bun
bun bin/cli.js list-skills
bun bin/cli.js doctor
bun bin/cli.js query "attribution modeling"
```

### 6. Python Source Environment
```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements/validation.txt
python3 -m chatgpt_ads_brain query "conversion attribution"
python3 scripts/validate_pack.py
```

---

## Registered Domain Skills

The system organizes advertising expertise into 12 discrete, specialized skills:

| Skill | Focus & Procedure |
| --- | --- |
| `chatgpt-ads` | Master orchestrator routing all queries |
| `chatgpt-ads-research` | Verify and maintain ChatGPT Ads evidence |
| `chatgpt-ads-readiness` | Establish client and account readiness |
| `chatgpt-ads-plan` | Design campaign strategy and economics |
| `chatgpt-ads-creative` | Create substantiated ads and destination briefs |
| `chatgpt-ads-measurement` | Design and validate measurement & attribution |
| `chatgpt-ads-analyze` | Analyze reports and diagnose performance |
| `chatgpt-ads-experiment` | Design and interpret advertising experiments |
| `chatgpt-ads-policy` | Review policy and privacy requirements |
| `chatgpt-ads-launch` | Prepare and verify exact campaign changes |
| `chatgpt-ads-operate` | Operate an authorized account via observed controls |
| `chatgpt-ads-monitor` | Monitor pacing, anomalies, and operational drift |

---

## Supported Environments

| Environment | Status | Scope |
| --- | --- | --- |
| **Linux (Python 3.11 & 3.14)** | Verified & Passing | Full POSIX descriptor-backed guarded workflows, validation, and packaging |
| **macOS Darwin (Python 3.11 & 3.14)** | Verified & Passing | 100% tests passing; descriptor-backed no-follow traversal with Darwin root alias normalization |
| **Windows (Python 3.11 & 3.14)** | Guarded workflows unavailable | Hosted restriction checks pass; doctor reports limited backend fail-closed |

---

## Core Invariants & Security Boundaries

1. **Safe Path Traversal**: Every directory traversal uses POSIX file descriptors and `O_NOFOLLOW` with explicit symlink rejection.
2. **Zero Inferred Execution**: Sourced claims, simulations, and approved live actions are strictly separated. No live campaign action is ever executed without explicit operator confirmation.
3. **Secret Hygiene**: Repository builds run offline detect-secrets scans; private keys, tokens, and credentials are strictly prohibited from public release trees.
4. **Offline Verifiability**: All 12 skills and the complete knowledge brain can be audited and queried without third-party network requests.

---

## Documentation Index

- [Beginner quickstart](docs/QUICKSTART.md)
- [Operator kit](docs/OPERATOR_KIT.md)
- [Knowledge index](brain/index.md)
- [Codex integration guide](CODEX.md)
- [Claude integration guide](CLAUDE.md)
- [Support policy](SUPPORT.md)
- [Security guidance](SECURITY.md)
- [Contributing guide](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

---

## Repository & Releases

- **GitHub Repository**: [imMamdouhaboammar/chatgpt-ads](https://github.com/imMamdouhaboammar/chatgpt-ads)
- **Author**: [Mamdouh Aboammar](https://github.com/imMamdouhaboammar)
- **Download Releases & Packages**: [GitHub Releases](https://github.com/imMamdouhaboammar/chatgpt-ads/releases)
