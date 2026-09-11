# Release v0.4.0 — Universal Multi-Agent & Sourced Advertising Engine

**Authored and copyrighted by Mamdouh Aboammar** ([@imMamdouhaboammar](https://github.com/imMamdouhaboammar))

This release establishes full multi-agent distribution, zero-vendor-lockin integration, and native macOS Darwin runtime verification for the **ChatGPT Ads** knowledge and guarded operating system.

---

### Highlights & Multi-Agent Distribution

- **OpenAI Codex & ChatGPT Plugin**: Native plugin configuration in `.codex-plugin/plugin.json` and `CODEX.md`.
- **Claude Code & Desktop Marketplace**: Certified plugin manifest in `marketplace.json` and `.claude-plugin/plugin.json`.
- **Skills.sh Hub**: Added registry descriptor in `.skills.json` enabling `npx skills add imMamdouhaboammar/chatgpt-ads`.
- **Universal Multi-Agent CLI & Installer**:
  - `bin/cli.js` (`chatgpt-ads`): Zero-dependency Bun and Node executable.
  - `install.sh`: One-liner installer for Claude Code, Antigravity / Gemini CLI, Codex, and Universal Agent Kernel.
- **macOS (Darwin) Safe I/O**: Normalized standard macOS system root aliases (`/var`, `/tmp`, `/etc`) in `scripts/safe_io.py`, achieving 100% test pass rate (69/69 core tests) on macOS.
- **AI Tool & Search Engine Discovery**: Added `llms.txt` and `llms-full.txt` machine-readable context files for Perplexity, ChatGPT, Claude, and search engines.

---

### Verification & Quality Gates

- **Core Python Tests**: 69/69 tests passed.
- **Specialized Skill Tests**: 12/12 tests passed.
- **Integrity Validation**: `scripts/validate_pack.py` status: `pass`.
- **Runtime Doctor**: `ready_for_local_posix_checks` on Linux and macOS.

---

### Downloadable Packages & Checksums

| File | SHA-256 Checksum |
| --- | --- |
| `chatgpt-ads-brain-v0.4.0.zip` | `28ad0689a56a7cc2444d690b1dfaec612ef8d22db485c089b77b6ddcbc5d7dab` |
