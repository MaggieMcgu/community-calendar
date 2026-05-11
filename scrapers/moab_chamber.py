#!/usr/bin/env python3
"""
Scraper for the Moab Area Chamber of Commerce event calendar.

Platform: ChamberMaster / GrowthZone. The platform exposes a per-event
iCalendar file at /eventcalendar/ICal/<slug>-<id>.ics but no calendar-wide
feed. So this scraper:

1. Walks the listing page in 30-day windows out to SCRAPE_MONTHS ahead
2. Extracts each event's Details slug-id
3. Fetches the matching per-event .ics
4. Parses VEVENT and returns event dicts

The wider community-calendar plumbing then re-emits a single combined
moab_chamber.ics that the MSN iCal importer (feed 7 / new-sources.ics)
picks up daily.

Usage:
    python scrapers/moab_chamber.py -o cities/moab/moab_chamber.ics
"""

import sys
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

import re
from datetime import datetime, timedelta, date
from typing import Any
from zoneinfo import ZoneInfo

from icalendar import Calendar

from lib.base import BaseScraper
from lib.utils import fetch_with_retry, DEFAULT_HEADERS

MOUNTAIN = ZoneInfo('America/Denver')
LISTING_URL = "https://business.moabchamber.com/eventcalendar/Search"
ICS_URL_TEMPLATE = "https://business.moabchamber.com/eventcalendar/ICal/{slug_id}.ics"

# Matches /eventcalendar/Details/<slug>-<numeric-id> (numeric id always trailing,
# 7 digits in observed samples but allow any length).
DETAIL_PATTERN = re.compile(
    r'/eventcalendar/Details/([a-z0-9][a-z0-9-]*-\d+)(?:[/?][^"\s]*)?',
    re.IGNORECASE,
)


class MoabChamberScraper(BaseScraper):
    name = "Moab Area Chamber of Commerce"
    domain = "moabchamber.com"
    timezone = "America/Denver"

    def fetch_events(self) -> list[dict[str, Any]]:
        slug_ids = self._collect_slug_ids()
        self.logger.info(f"Found {len(slug_ids)} unique events on the listing")

        events: list[dict[str, Any]] = []
        for slug_id in sorted(slug_ids):
            try:
                event = self._fetch_event(slug_id)
                if event:
                    events.append(event)
            except Exception as e:  # noqa: BLE001 — one bad event shouldn't kill the run
                self.logger.warning(f"Skipping {slug_id}: {e}")
        return events

    def _collect_slug_ids(self) -> set[str]:
        """Walk the listing in 30-day windows; collect Details slug-id strings."""
        slug_ids: set[str] = set()

        # Start a few days back so events already in progress still come through.
        cursor = datetime.now(MOUNTAIN).date() - timedelta(days=3)
        end = cursor + timedelta(days=self.months_ahead * 31)

        while cursor < end:
            window_end = min(cursor + timedelta(days=30), end)
            url = (
                f"{LISTING_URL}"
                f"?from={cursor.strftime('%m/%d/%Y')}"
                f"&to={window_end.strftime('%m/%d/%Y')}"
                f"&mode=0&DateFilter=5"
            )
            try:
                html = fetch_with_retry(url, headers=DEFAULT_HEADERS, timeout=30)
            except Exception as e:  # noqa: BLE001
                self.logger.warning(f"Listing fetch failed for {cursor}–{window_end}: {e}")
                cursor = window_end + timedelta(days=1)
                continue

            new = {m.group(1) for m in DETAIL_PATTERN.finditer(html)}
            self.logger.debug(f"{cursor}–{window_end}: {len(new)} events")
            slug_ids.update(new)
            cursor = window_end + timedelta(days=1)

        return slug_ids

    def _fetch_event(self, slug_id: str) -> dict[str, Any] | None:
        ics_url = ICS_URL_TEMPLATE.format(slug_id=slug_id)
        try:
            ics_text = fetch_with_retry(ics_url, headers=DEFAULT_HEADERS, timeout=30)
        except Exception as e:  # noqa: BLE001
            self.logger.warning(f"Could not fetch ICS for {slug_id}: {e}")
            return None

        try:
            cal = Calendar.from_ical(ics_text)
        except ValueError as e:
            self.logger.warning(f"Invalid ICS for {slug_id}: {e}")
            return None

        for component in cal.walk('VEVENT'):
            return self._parse_vevent(component, slug_id)
        return None

    def _parse_vevent(self, component, slug_id: str) -> dict[str, Any] | None:
        summary = str(component.get('SUMMARY', '')).strip()
        if not summary:
            return None

        dtstart = component.get('DTSTART').dt if component.get('DTSTART') else None
        dtend = component.get('DTEND').dt if component.get('DTEND') else dtstart
        if not dtstart:
            return None

        # Normalize date-only to a datetime so downstream filtering works.
        if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
            dtstart = datetime.combine(dtstart, datetime.min.time(), tzinfo=MOUNTAIN)
        if isinstance(dtend, date) and not isinstance(dtend, datetime):
            dtend = datetime.combine(dtend, datetime.min.time(), tzinfo=MOUNTAIN)

        location = str(component.get('LOCATION', '')).strip() or 'Moab, UT'
        description = str(component.get('DESCRIPTION', '')).strip()
        url = str(component.get('URL', '')).strip() or \
            f"https://business.moabchamber.com/eventcalendar/Details/{slug_id}"

        # Preserve the chamber's UID so re-runs are idempotent across the pipeline.
        uid = str(component.get('UID', '')).strip() or None

        return {
            'title': summary,
            'dtstart': dtstart,
            'dtend': dtend or dtstart,
            'url': url,
            'location': location,
            'description': description,
            'uid': uid,
        }


if __name__ == '__main__':
    MoabChamberScraper.main()
