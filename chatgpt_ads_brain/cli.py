"""Product-facing CLI for knowledge, normalized analysis, and read-only ads data."""
from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from . import __version__
from .adapters import AdsAdapter, CapabilityUnavailable
from .capabilities import CapabilityState, CapabilityStatus
from .openai_ads import AdsApiError, OpenAIAdsAdapter

ROOT = Path(__file__).resolve().parents[1]


class CliUsageError(ValueError):
    pass


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CliUsageError(message)


class _StaticProvider:
    def __init__(self, provider: str, states):
        self.provider = provider
        self._states = tuple(states)

    def capabilities(self):
        return self._states


def _capability_states(adapter: AdsAdapter) -> tuple[CapabilityState, ...]:
    return tuple(adapter.capabilities()) + (
        CapabilityState("account.read", "host_native", CapabilityStatus.UNAVAILABLE, "no host-native account adapter detected"),
        CapabilityState("report.native_csv.read", "native_csv", CapabilityStatus.REQUIRES_NATIVE_EVIDENCE, "sanitized native export and reviewed mapping required"),
        CapabilityState("report.normalized_csv.analyze", "normalized_csv", CapabilityStatus.SUPPORTED, "manual-normalized-v1 local analysis", configured=True),
        CapabilityState("knowledge.query", "knowledge", CapabilityStatus.SUPPORTED, "offline sourced registry retrieval", configured=True),
        CapabilityState("campaign.write", "advertiser_api", CapabilityStatus.UNSUPPORTED, "read-only phase; writes are not implemented"),
        CapabilityState("scheduling", "advertiser_api", CapabilityStatus.UNSUPPORTED, "scheduling is disabled"),
    )


def _primitive(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {field.name: _primitive(getattr(value, field.name)) for field in dataclasses.fields(value) if field.name != "raw"}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _primitive(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_primitive(item) for item in value]
    return value


def _emit(payload: dict[str, Any], machine: bool, human: Iterable[str]) -> None:
    if machine:
        print(json.dumps(_primitive(payload), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False))
    else:
        print("\n".join(human))


def _emit_error(code: str, message: str, machine: bool) -> None:
    if machine:
        print(json.dumps({"error": {"code": code, "message": message}}, sort_keys=True), file=sys.stderr)
    else:
        print(f"Error [{code}]: {message}", file=sys.stderr)


def list_skills() -> int:
    skills = []
    for directory in sorted((ROOT / "skills").iterdir()):
        skill_file = directory / "SKILL.md"
        if directory.is_dir() and skill_file.exists():
            description = "Specialized advertising skill"
            for line in skill_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("description:"):
                    description = line.split(":", 1)[1].strip()
                    break
            skills.append((directory.name, description))
    print(f"\nAvailable ChatGPT Ads Skills ({len(skills)} registered):")
    for name, description in skills:
        print(f"  - {name:<25} : {description}")
    print("\nOrchestrator: skills/chatgpt-ads/SKILL.md")
    return 0


def _parser() -> SafeArgumentParser:
    parser = SafeArgumentParser(prog="chatgpt-ads", description="Read-only ChatGPT Ads research and account analysis")
    parser.add_argument("--version", action="version", version=f"chatgpt-ads-brain v{__version__}")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=SafeArgumentParser)

    account = commands.add_parser("account", help="Inspect the configured ad account")
    account_commands = account.add_subparsers(dest="account_command", required=True, parser_class=SafeArgumentParser)
    status = account_commands.add_parser("status")
    status.add_argument("--json", action="store_true")

    capabilities = commands.add_parser("capabilities", help="Inspect native adapter capability state")
    capabilities.add_argument("--json", action="store_true")

    campaigns = commands.add_parser("campaigns", help="Read campaigns")
    campaign_commands = campaigns.add_subparsers(dest="campaign_command", required=True, parser_class=SafeArgumentParser)
    campaign_list = campaign_commands.add_parser("list")
    campaign_list.add_argument("--json", action="store_true")
    campaign_show = campaign_commands.add_parser("show")
    campaign_show.add_argument("selector")
    campaign_show.add_argument("--json", action="store_true")

    report = commands.add_parser("report", help="Read normalized delivery insights")
    report.add_argument("--level", choices=("account", "campaign", "ad_group", "ad"), required=True)
    report.add_argument("--last", default="30d")
    report.add_argument("--json", action="store_true")

    conversions = commands.add_parser("conversions", help="Read conversion configuration")
    conversion_commands = conversions.add_subparsers(dest="conversion_command", required=True, parser_class=SafeArgumentParser)
    for name in ("sources", "settings"):
        child = conversion_commands.add_parser(name)
        child.add_argument("--json", action="store_true")

    diagnose = commands.add_parser("diagnose", help="Verify configured read-only account access")
    diagnose.add_argument("--json", action="store_true")

    for name in ("research", "query"):
        research = commands.add_parser(name, help="Query sourced knowledge")
        research.add_argument("question")
        research.add_argument("--limit", type=int, default=8)
        research.add_argument("--json", action="store_true")

    analyze = commands.add_parser("analyze", help="Analyze manual-normalized-v1 CSV")
    analyze.add_argument("path", type=Path)
    analyze.add_argument("--json", action="store_true")

    doctor = commands.add_parser("doctor", help="Inspect local runtime safety")
    doctor.add_argument("--json", action="store_true")
    commands.add_parser("list-skills", help="List agent routing skills")
    commands.add_parser("validate", help="Run package validation")
    return parser


def _duration(value: str) -> timedelta:
    if not value.endswith("d") or not value[:-1].isdigit():
        raise CliUsageError("--last must be a positive day duration such as 30d")
    days = int(value[:-1])
    if days < 1 or days > 366:
        raise CliUsageError("--last must be between 1d and 366d")
    return timedelta(days=days)


def _load_analyzer():
    path = ROOT / "skills/chatgpt-ads/scripts/analyze.py"
    spec = importlib.util.spec_from_file_location("chatgpt_ads_normalized_analyzer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("normalized analyzer unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _legacy(command: str, arguments: list[str]) -> int | None:
    scripts = {
        "knowledge": "knowledge_core.py",
        "operate": "operating_core.py",
    }
    script = scripts.get(command)
    if script is None:
        return None
    return subprocess.call([sys.executable, str(ROOT / "scripts" / script), *arguments])


def main(argv: list[str] | None = None, *, adapter: AdsAdapter | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if values:
        legacy = _legacy(values[0], values[1:])
        if legacy is not None:
            return legacy
    machine = "--json" in values
    try:
        args = _parser().parse_args(values)
        ads = adapter or OpenAIAdsAdapter()

        if args.command == "list-skills":
            return list_skills()
        if args.command == "validate":
            if not (ROOT / "scripts/validate_pack.py").is_file():
                _emit_error("capability_unavailable", "package validation requires the public distribution tree", machine)
                return 2
            return subprocess.call([sys.executable, str(ROOT / "scripts/validate_pack.py")])
        if args.command == "capabilities":
            states = _capability_states(ads)
            _emit({"capabilities": states}, args.json, (f"{item.capability}: {item.status.value} ({item.reason})" for item in states))
            return 0
        if args.command == "account":
            account = ads.get_account()
            _emit({"account": account, "live_verification": "account_read_succeeded"}, args.json, (
                f"Account: {account.name or account.id}",
                f"Status: {account.status or 'not_reported'}",
                f"Timezone: {account.timezone or 'not_reported'}",
                f"Currency: {account.currency or 'not_reported'}",
                f"Review: {account.review_status or 'not_reported'}",
            ))
            return 0
        if args.command == "campaigns":
            campaigns = ads.list_campaigns()
            if args.campaign_command == "list":
                _emit({"campaigns": campaigns}, args.json, (f"{item.id}  {item.status or '-':<12}  {item.name or '-'}" for item in campaigns))
                return 0
            needle = args.selector.casefold()
            matches = [item for item in campaigns if item.id.casefold() == needle or (item.name and item.name.casefold() == needle)]
            if len(matches) != 1:
                raise CliUsageError("campaign selector must match exactly one campaign id or name")
            item = matches[0]
            _emit({"campaign": item}, args.json, (f"Campaign: {item.name or item.id}", f"ID: {item.id}", f"Status: {item.status or 'not_reported'}"))
            return 0
        if args.command == "report":
            end = datetime.now(timezone.utc).replace(microsecond=0)
            start = end - _duration(args.last)
            ads.get_account()
            query = {
                "aggregation_level": args.level,
                "time_granularity": "daily",
                "time_ranges[]": json.dumps({"type": "unix_range", "start": int(start.timestamp()), "end": int(end.timestamp())}, separators=(",", ":")),
            }
            rows = ads.get_account_insights(query)
            _emit({"level": args.level, "period_start": start, "period_end": end, "rows": rows}, args.json, (f"{len(rows)} {args.level} insight row(s), {start.date()} through {end.date()}",))
            return 0
        if args.command == "conversions":
            items = ads.list_conversion_sources() if args.conversion_command == "sources" else ads.list_conversion_settings()
            key = "sources" if args.conversion_command == "sources" else "settings"
            _emit({key: items}, args.json, (f"{len(items)} conversion {key}",))
            return 0
        if args.command == "diagnose":
            before = tuple(ads.capabilities())
            account = ads.get_account()
            after = tuple(ads.capabilities())
            _emit({"status": "read_only_account_verified", "account": account, "capabilities_before": before, "capabilities_after": after}, args.json, ("Read-only account probe succeeded.", f"Account: {account.name or account.id}"))
            return 0
        if args.command in {"research", "query"}:
            from scripts.query_brain import query
            result = query(args.question, limit=args.limit)
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
            else:
                print(f"Knowledge status: {result['status']}")
                for item in result["results"]:
                    print(f"- {item['id']}: {item.get('claim', '')}")
            return 0
        if args.command == "analyze":
            analyzer = _load_analyzer()
            result = analyzer.analyze(analyzer.read_normalized_csv(args.path))
            _emit(result, args.json, (f"Analysis status: {result['status']}", f"Ads: {result['ad_count']}", f"Source: {result['source_type']}"))
            return 0
        if args.command == "doctor":
            from scripts.doctor import report
            result = report()
            _emit(result, args.json, (f"Doctor: {result['status']}", f"Filesystem: {result['filesystem']['backend']}", "Secrets: not inspected"))
            return 0
        raise CliUsageError("unknown command")
    except CliUsageError as exc:
        _emit_error("invalid_usage", str(exc), machine)
        return 2
    except AdsApiError as exc:
        _emit_error(exc.code, str(exc).split(": ", 1)[-1], machine)
        return 2 if exc.code in {"not_configured", "invalid_request", "capability_unavailable"} else 3
    except CapabilityUnavailable as exc:
        _emit_error(exc.reason, exc.capability, machine)
        return 2
    except (ValueError, OSError):
        _emit_error("invalid_input", "input could not be processed", machine)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
