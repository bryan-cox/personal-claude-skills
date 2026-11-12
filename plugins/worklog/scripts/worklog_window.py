"""Resolve a daily note's rolling activity watermark without losing overnight work."""

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

UTC = timezone.utc
DEFAULT_TIMEZONE = "America/New_York"
LAST_UPDATED = re.compile(r"^\*Last updated: (.+)\*$", re.MULTILINE)


def parse_timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Activity timestamps must include a timezone")
    return parsed.astimezone(UTC)


def iso(value):
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ActivityWindow:
    since: datetime
    until: datetime
    strict_start: bool

    @classmethod
    def for_date(cls, target, since="", until="", timezone_name=DEFAULT_TIMEZONE, current=None):
        target = date.fromisoformat(target) if isinstance(target, str) else target
        zone = ZoneInfo(timezone_name)
        current = current or datetime.now(UTC).replace(microsecond=0)
        start = parse_timestamp(since) if since else datetime.combine(target, time.min, zone).astimezone(UTC)
        if until:
            end = parse_timestamp(until)
        elif target < current.astimezone(zone).date():
            end = datetime.combine(target + timedelta(days=1), time.min, zone).astimezone(UTC) - timedelta(microseconds=1)
        else:
            end = current
        if start > end:
            raise ValueError("The activity watermark is later than the collection cutoff")
        return cls(start, end, bool(since))

    def contains(self, value):
        moment = parse_timestamp(value)
        return (moment > self.since if self.strict_start else moment >= self.since) and moment <= self.until


def resolve_window(vault, target, since="", until="", timezone_name=DEFAULT_TIMEZONE, current=None):
    target = date.fromisoformat(target) if isinstance(target, str) else target
    root = Path(vault) / "Work log"
    note = root / target.strftime("%Y/%m") / (target.isoformat() + ".md")
    source = None
    if not since:
        candidates = [note] if note.exists() else []
        candidates.extend(sorted((p for p in root.glob("*/*/*.md") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem) and p.stem < target.isoformat()), reverse=True))
        for path in candidates:
            match = LAST_UPDATED.search(path.read_text())
            if match:
                since = iso(parse_timestamp(match.group(1)))
                source = str(path)
                break
    window = ActivityWindow.for_date(target, since, until, timezone_name, current)
    return {"date": target.isoformat(), "note": str(note), "since": iso(window.since) if window.strict_start else "",
            "until": iso(window.until), "timezone": timezone_name, "watermark_source": source}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date")
    parser.add_argument("--since", default="")
    parser.add_argument("--until", default="")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    parser.add_argument("--vault", type=Path, default=Path.home() / "Red Hat")
    args = parser.parse_args()
    target = args.date or datetime.now(ZoneInfo(args.timezone)).date().isoformat()
    print(json.dumps(resolve_window(args.vault, target, args.since, args.until, args.timezone), indent=2))
