#!/usr/bin/env python3
"""
Scraper for Back of Beyond Books (Moab, UT) events.

WordPress site with a custom `happening` post type exposed via REST API.
Uses /wp-json/wp/v2/happening?after=... to fetch only current-year posts,
avoiding stale 2022/2023 events that appear on the /happenings/ listing page.

Each post's title uses the format: title ~ date ~ time ~ location
Description and URL come from the REST API response fields.

Usage:
    python scrapers/back_of_beyond.py -o cities/moab/back_of_beyond.ics
"""

import sys
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

import re
import json
from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from lib.base import BaseScraper
from lib.utils import DEFAULT_HEADERS, fetch_with_retry, MONTH_MAP

MOUNTAIN = ZoneInfo('America/Denver')
API_BASE = "https://backofbeyondbooks.com/wp-json/wp/v2/happening"

# Pattern: "Thursday, April 16th" or "Tuesday, March 3rd"
DATE_PATTERN = re.compile(
    r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+'
    r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+'
    r'(\d{1,2})(?:st|nd|rd|th)?',
    re.IGNORECASE
)

# Pattern: "4-6 pm" or "6:30am" or "3-5pm" or "6 pm"
TIME_PATTERN = re.compile(
    r'(\d{1,2})(?::(\d{2}))?\s*(?:-\s*\d{1,2}(?::\d{2})?)?\s*(am|pm)',
    re.IGNORECASE
)


class BackOfBeyondScraper(BaseScraper):
    name = "Back of Beyond Books"
    domain = "backofbeyondbooks.com"
    timezone = "America/Denver"

    def fetch_events(self) -> list[dict[str, Any]]:
        now = datetime.now(MOUNTAIN)
        after = f"{now.year}-01-01T00:00:00"
        url = f"{API_BASE}?after={after}&per_page=100&orderby=modified&order=desc"
        self.logger.info(f"Fetching REST API: {url}")

        raw = fetch_with_retry(url, headers=DEFAULT_HEADERS)
        try:
            posts = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            self.logger.warning("REST API returned non-JSON — falling back to empty list")
            return []

        if not isinstance(posts, list):
            self.logger.warning(f"Unexpected REST API response shape: {type(posts)}")
            return []

        events = []
        for post in posts:
            title_raw = post.get('title', {}).get('rendered', '')
            # Strip any HTML entities (e.g. &#8211; → –)
            title_text = BeautifulSoup(title_raw, 'html.parser').get_text()
            if '~' not in title_text:
                continue

            # Description from excerpt or content
            excerpt_html = post.get('excerpt', {}).get('rendered', '')
            content_html = post.get('content', {}).get('rendered', '')
            description_html = excerpt_html or content_html
            description = BeautifulSoup(description_html, 'html.parser').get_text(separator='\n').strip()
            # Trim to first 3 paragraphs worth
            description = '\n'.join(description.splitlines()[:6])

            post_url = post.get('link', '')

            parsed = self._parse_heading(title_text, description=description, url=post_url)
            if parsed:
                events.append(parsed)

        self.logger.info(f"Found {len(events)} events")
        return events

    def _parse_heading(self, heading: str, description: str = '', url: str = '') -> Optional[dict[str, Any]]:
        """Parse an event from the post title (format: title ~ date ~ time ~ location)."""
        parts = [p.strip() for p in heading.split('~')]
        if len(parts) < 2:
            return None

        # Extract title — first part, before date info
        title = parts[0]

        # Find date in the heading
        date_match = DATE_PATTERN.search(heading)
        if not date_match:
            return None

        month_name = date_match.group(1).lower()
        day = int(date_match.group(2))
        month = MONTH_MAP.get(month_name)
        if not month:
            return None

        # Determine year — assume current year, bump to next if date is well past
        now = datetime.now(MOUNTAIN)
        year = now.year
        candidate = datetime(year, month, day, tzinfo=MOUNTAIN)
        if candidate.date() < now.date() - timedelta(days=60):
            year += 1

        # Find time in heading
        time_match = TIME_PATTERN.search(heading)
        hour, minute = 18, 0  # default 6pm if no time found
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            ampm = time_match.group(3).lower()
            if ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0

        dtstart = datetime(year, month, day, hour, minute, tzinfo=MOUNTAIN)
        dtend = dtstart + timedelta(hours=2)

        # Location — look for known location names in parts
        location = "Back of Beyond Books, 83 N Main St, Moab, UT 84532"
        for part in parts:
            lower = part.lower()
            if 'star hall' in lower:
                location = "Star Hall, 159 E Center St, Moab, UT 84532"
            elif 'castle valley' in lower and 'town hall' in lower:
                location = "Castle Valley Town Hall, Castle Valley, UT"
            elif 'library' in lower:
                location = "Grand County Public Library, 257 E Center St, Moab, UT 84532"

        return {
            'title': title,
            'dtstart': dtstart,
            'dtend': dtend,
            'location': location,
            'description': description,
            'url': url,
        }


if __name__ == '__main__':
    BackOfBeyondScraper.main()
