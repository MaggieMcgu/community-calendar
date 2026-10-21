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
from datetime import date, datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from lib.base import BaseScraper
from lib.utils import DEFAULT_HEADERS, fetch_with_retry, MONTH_MAP

MOUNTAIN = ZoneInfo('America/Denver')
API_BASE = "https://backofbeyondbooks.com/wp-json/wp/v2/happening"

# Pattern: "Thursday, April 16th" or "Tuesday, March 3rd" or "April, 23rd" or
# "Wednesday, Oct. 21, 2026". Weekday prefix is optional since some BoBB posts
# omit it (e.g. "Music in the Bookstore ~ April, 23rd ~ 6-9 pm"); months may be
# abbreviated with an optional period; a year is used when present.
DATE_PATTERN = re.compile(
    r'(?:\b(Mon|Tue|Tues|Wed|Thu|Thur|Thurs|Fri|Sat|Sun)(?:day|nesday|sday|rsday|urday)?\.?,?\s+)?'
    r'\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|'
    r'Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?,?\s+'
    r'(\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s+(\d{4})\b)?',
    re.IGNORECASE
)

WEEKDAY_INDEX = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}

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
        # _cb busts BoBB's edge cache (WordPress.com), which served GitHub Actions a
        # copy missing posts published hours earlier (2026-10-21).
        url = (f"{API_BASE}?after={after}&per_page=100&orderby=modified&order=desc"
               f"&_cb={int(now.timestamp())}")
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

            # BoBB's `date` is when the draft was created, always before the event
            posted = None
            try:
                posted = datetime.fromisoformat(post.get('date', '')).date()
            except ValueError:
                pass

            parsed = self._parse_heading(title_text, description=description, url=post_url,
                                         posted=posted)
            if parsed:
                events.append(parsed)

        self.logger.info(f"Found {len(events)} events")
        return events

    def _resolve_year(self, heading: str, month: int, day: int, weekday: Optional[str],
                      explicit_year: Optional[str], posted: Optional[date]) -> Optional[int]:
        """Pick the event year. Titles rarely carry one, and a past post must
        never be re-dated into next year (2026-10 bug: six spring events
        reappeared as 2027).

        - Explicit year in the title wins.
        - Otherwise the event is the first occurrence of month/day on or after
          the post's publish date (30 days of slack for posts made just after).
        - If the title names a weekday, that year's date must fall on it; a
          mismatch means we can't trust the date, so skip.
        """
        if explicit_year:
            return int(explicit_year)

        anchor = posted or datetime.now(MOUNTAIN).date()
        year = anchor.year
        try:
            if date(year, month, day) < anchor - timedelta(days=30):
                year += 1
            if weekday and date(year, month, day).weekday() != WEEKDAY_INDEX[weekday[:3].lower()]:
                self.logger.warning(f"Weekday mismatch for {year}, skipping: {heading}")
                return None
        except ValueError:
            return None
        return year

    def _parse_heading(self, heading: str, description: str = '', url: str = '',
                       posted: Optional[date] = None) -> Optional[dict[str, Any]]:
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

        weekday, month_name, day_str, explicit_year = date_match.groups()
        day = int(day_str)
        month = MONTH_MAP.get(month_name.lower()[:3])
        if not month:
            return None

        year = self._resolve_year(heading, month, day, weekday, explicit_year, posted)
        if year is None:
            return None

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

        # Location — use the last tilde-separated segment as the venue name.
        # BoBB's title format is: "Speaker ~ Day, Date ~ Time ~ Venue"
        # If the 4th segment exists and isn't a date/time, use it; otherwise
        # default to the bookstore. Known venues get full addresses from
        # VENUE_ADDRESSES; unknown ones pass through as bare names (MSN's
        # msn_find_or_create_venue handles the rest).
        location = "Back of Beyond Books, 83 N Main St, Moab, UT 84532"
        VENUE_ADDRESSES = {
            'back of beyond books': "Back of Beyond Books, 83 N Main St, Moab, UT 84532",
            'star hall': "Star Hall, 159 E Center St, Moab, UT 84532",
            'grand county public library': "Grand County Public Library, 257 E Center St, Moab, UT 84532",
            'grand county library': "Grand County Public Library, 257 E Center St, Moab, UT 84532",
            'castle valley town hall': "Castle Valley Town Hall, Castle Valley, UT",
            'moab arts & recreation center': "Moab Arts and Recreation Center (MARC), 111 E 100 N, Moab, UT 84532",
            'moab arts and recreation center': "Moab Arts and Recreation Center (MARC), 111 E 100 N, Moab, UT 84532",
            'marc': "Moab Arts and Recreation Center (MARC), 111 E 100 N, Moab, UT 84532",
            'spanish valley vineyard & winery': "Spanish Valley Vineyard & Winery, 4710 Zimmerman Ln, Moab, UT 84532",
            'spanish valley vineyard and winery': "Spanish Valley Vineyard & Winery, 4710 Zimmerman Ln, Moab, UT 84532",
            'spanish valley winery': "Spanish Valley Vineyard & Winery, 4710 Zimmerman Ln, Moab, UT 84532",
        }

        # Try the last tilde-separated segment first (the title format's venue slot)
        venue_candidate = None
        if len(parts) >= 4:
            last = parts[-1].strip()
            # Skip if the last segment is actually a time/date leftover
            if last and not DATE_PATTERN.search(last) and not TIME_PATTERN.fullmatch(last):
                venue_candidate = last

        if venue_candidate:
            key = venue_candidate.lower()
            if key in VENUE_ADDRESSES:
                location = VENUE_ADDRESSES[key]
            else:
                # Unknown venue — pass through the bare name. MSN side will
                # create a TEC venue record for it on import.
                location = venue_candidate

        # Fallback: also scan all parts for known venue substrings (covers
        # older posts where venue isn't in the last segment).
        for part in parts:
            lower = part.lower()
            for key, addr in VENUE_ADDRESSES.items():
                if key in lower and location == "Back of Beyond Books, 83 N Main St, Moab, UT 84532":
                    location = addr
                    break

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
