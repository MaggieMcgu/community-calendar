#!/usr/bin/env python3
"""
Scraper for Moab Folk Festival events.

Two sources:
1. moabfolkfestival.com — WordPress/MEC main festival (Nov). Eventbrite for
   ticketing but Eventbrite's Festival JSON-LD omits startDate, so we scrape
   the main site's JSON-LD instead.
2. moabfreeconcerts.com — Squarespace free summer concert series (Jun-Aug).
   No structured data; dates extracted from page text.

Usage:
    python scrapers/moab_folk_festival.py -o cities/moab/moab_folk_festival.ics
"""

import sys
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

import re
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from lib.base import BaseScraper
from lib.jsonld import extract_jsonld_blocks, extract_events_from_blocks
from lib.utils import DEFAULT_HEADERS

MOUNTAIN = ZoneInfo('America/Denver')

FESTIVAL_URL = "https://www.moabfolkfestival.com/"
FREE_CONCERTS_URL = "https://www.moabfreeconcerts.com/"

FESTIVAL_LOCATION = "Center Street Ballfields, 198 E Center St, Moab, UT 84532"
FREE_CONCERT_LOCATION = "Swanny Park, 100 E 100 N, Moab, UT 84532"


class MoabFolkFestivalScraper(BaseScraper):
    """Scraper for Moab Folk Festival and Free Concert Series."""

    name = "Moab Folk Festival"
    domain = "moabfolkfestival.com"
    timezone = "America/Denver"

    def fetch_events(self) -> list[dict[str, Any]]:
        events = []
        events.extend(self._fetch_festival_events())
        events.extend(self._fetch_free_concerts())
        return events

    def _fetch_festival_events(self) -> list[dict[str, Any]]:
        """Check main festival site for JSON-LD Event data."""
        self.logger.info(f"Fetching {FESTIVAL_URL}")
        try:
            resp = requests.get(FESTIVAL_URL, headers=DEFAULT_HEADERS, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch festival site: {e}")
            return []

        blocks = extract_jsonld_blocks(resp.text)
        jsonld_events = extract_events_from_blocks(blocks)
        self.logger.info(f"Found {len(jsonld_events)} JSON-LD events on festival site")

        events = []
        now = datetime.now(timezone.utc)

        for item in jsonld_events:
            title = item.get('name', '').strip()
            if not title:
                continue

            start_str = item.get('startDate', '')
            if not start_str:
                continue

            try:
                dtstart = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            except ValueError:
                continue

            if dtstart.tzinfo is None:
                dtstart = dtstart.replace(tzinfo=MOUNTAIN)
            if dtstart < now:
                continue

            dtend = None
            end_str = item.get('endDate', '')
            if end_str:
                try:
                    dtend = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    if dtend.tzinfo is None:
                        dtend = dtend.replace(tzinfo=MOUNTAIN)
                except ValueError:
                    pass

            # Location from JSON-LD or default
            loc = item.get('location', {})
            location = FESTIVAL_LOCATION
            if isinstance(loc, dict):
                loc_name = loc.get('name', '')
                if loc_name:
                    location = loc_name

            # Clean description
            desc = item.get('description', '') or ''
            desc = re.sub(r'<[^>]+>', ' ', desc).strip()
            desc = re.sub(r'\s+', ' ', desc)

            # Clean HTML entities from title
            title = re.sub(r'<br\s*/?>', ' - ', title)
            title = re.sub(r'<[^>]+>', '', title).strip()

            events.append({
                'title': title,
                'dtstart': dtstart,
                'dtend': dtend,
                'location': location,
                'description': desc[:500] if desc else '',
                'url': item.get('url', FESTIVAL_URL),
            })

        return events

    def _fetch_free_concerts(self) -> list[dict[str, Any]]:
        """Parse free concert series dates from moabfreeconcerts.com."""
        self.logger.info(f"Fetching {FREE_CONCERTS_URL}")
        try:
            resp = requests.get(FREE_CONCERTS_URL, headers=DEFAULT_HEADERS, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch free concerts site: {e}")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        text = soup.get_text(' ', strip=True)

        events = []
        now = datetime.now(MOUNTAIN)
        current_year = now.year

        # Look for date patterns like "June 26", "july 10", etc.
        # Free concerts are typically 6-9pm at Swanny Park
        date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})'
        matches = re.findall(date_pattern, text, re.IGNORECASE)

        seen_dates = set()
        for month_name, day in matches:
            try:
                dt = datetime.strptime(f"{month_name.capitalize()} {day} {current_year}", "%B %d %Y")
                # Free concerts are typically summer evening events, 6pm
                dt = dt.replace(hour=18, minute=0, tzinfo=MOUNTAIN)
            except ValueError:
                continue

            # Skip past dates and duplicates
            date_key = dt.strftime('%Y-%m-%d')
            if dt < now or date_key in seen_dates:
                continue
            seen_dates.add(date_key)

            dtend = dt.replace(hour=21)  # 6-9pm typical

            events.append({
                'title': 'Moab Free Concert Series',
                'dtstart': dt,
                'dtend': dtend,
                'location': FREE_CONCERT_LOCATION,
                'description': 'Free community concert at Swanny Park. Part of the Moab Free Concert Series presented by Friends of the Moab Folk Festival.',
                'url': FREE_CONCERTS_URL,
            })

        self.logger.info(f"Found {len(events)} free concert dates")
        return events


if __name__ == '__main__':
    MoabFolkFestivalScraper.main()
