# Changelog

## 0.5.0 - 2026-09-11

- Added deterministic offline Arabic/English hybrid retrieval with advertising aliases while retaining freshness and contradiction gates.
- Added provider-neutral domain models, an inspectable capability resolver, and explicit missing-versus-zero measurement semantics.
- Added an account-unverified, read-only OpenAI Advertiser API adapter with environment-only authentication, bounded retries, pagination, structured redacted errors, response validation, and synthetic contract tests.
- Added account, campaign, insight, conversion, capability, diagnosis, research, normalized analysis, and doctor commands to the product CLI with stable JSON output.
- Added offline source snapshot comparison and explicit claim-review transitions. No source change automatically rewrites a canonical claim.
- Native CSV still requires a genuine sanitized sample. Campaign writes, live action automation, and scheduling remain unavailable.

## 0.4.0 - 2026-09-11

Authored and copyrighted by Mamdouh Aboammar. Establishes full multi-agent distribution across OpenAI Codex, Claude Marketplace, Skills.sh, and Universal Agent Kernel:
- **OpenAI Codex Plugin**: Native `.codex-plugin/plugin.json` and enhanced `CODEX.md` integration.
- **Claude Marketplace**: Registered `marketplace.json` conforming to Claude Plugin specification and `.claude-plugin/plugin.json`.
- **Skills.sh Hub**: Added `.skills.json` registry descriptor for `npx skills add imMamdouhaboammar/chatgpt-ads`.
- **Universal Multi-Agent Installer**: Provided `install.sh` and Bun/npm CLI entrypoint `bin/cli.js` (`chatgpt-ads`).
- **macOS (Darwin) POSIX Safe I/O**: Resolved system symlink root alias handling (`/var`, `/tmp`, `/etc`), achieving 100% test pass rate across all 69 core tests on macOS.
- **AI & Search Engine Discovery**: Added `llms.txt` and `llms-full.txt` context files, GitHub topics, and aesthetic Mermaid workflow documentation.

## 0.3.1 - 2026-09-11

Adds the supplied repository cover; closes the manifest metadata scanning gap and guarded ZIP output race; adds broader secret checks, hash-locked validation dependencies and CI scanning. Corrects current runtime status while preserving dated acceptance evidence. Repository and release protections are verified separately through GitHub.

## 0.3.0 - 2026-09-11

Public-source release preparation. The distributable tree is now created from
an explicit allowlist and can be archived only after that projection is
verified. The package includes its tests, schemas, synthetic fixtures, runtime
guidance and a first-run walkthrough. Linux is locally checked. Windows is a
doctor and CI capability-check target; guarded Windows workflows are unavailable. This is
an independent community project, not an official OpenAI integration or a
production certification.

## 0.2.1

Expanded synthetic workflow acceptance, offline measurement preparation cases, current native integration prerequisites, native Claude browser capability checks and explicit live-account handoff. The account session exposed a country-availability gate; live campaign and native reporting acceptance remain open.

## 0.2.0

Compact knowledge and 12 workflow skills; incremental source updates; client/account guard interfaces; reviewed learning promotion; Codex/Claude procedures; explicit report provenance; simulated operating tests; allowlisted portable archive. Live account acceptance remains open.

## 0.1.0 - 2026-09-10

- Created a source-cited ChatGPT Ads research vault and ten portable skill entrypoints.
- Added dated claim/source joins, documented capability states, conflict records and independent reviews.
- Implemented normalized aggregate analysis, HTML reports and deterministic source freshness checks.
- Added synthetic fixtures and regression tests for arithmetic, input safety, output preservation and stale evidence.
- Local candidate only; no account execution, publication or global installation acceptance.
