#!/usr/bin/env python3
"""
Scraper for Back of Beyond Books (Moab, UT) events.

WordPress site with no JSON-LD event data. Events are listed on /happenings/
as h3 headings with title ~ date ~ time ~ location separated by tildes,
followed by div.excerpt (description) and div.more (permalink).

Usage:
    python scrapers/back_of_beyond.py -o cities/moab/back_of_beyond.ics
"""

import sys
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

import re
from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from lib.base import BaseScraper
from lib.utils import DEFAULT_HEADERS, fetch_with_retry, MONTH_MAP

MOUNTAIN = ZoneInfo('America/Denver')

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
        url = "https://backofbeyondbooks.com/happenings/"
        self.logger.info(f"Fetching {url}")
        html = fetch_with_retry(url, headers=DEFAULT_HEADERS)

        soup = BeautifulSoup(html, 'lxml')
        events = []

        for h3 in soup.select('h3'):
            heading_text = h3.get_text(strip=True)
            if not heading_text or '~' not in heading_text:
                continue

            parsed = self._parse_heading(heading_text, h3)
            if parsed:
                events.append(parsed)

        if not events and soup.select('h3'):
            self.logger.warning("Page has h3 elements but no events parsed — format may have changed")
        self.logger.info(f"Found {len(events)} events")
        return events

    def _parse_heading(self, heading: str, h3_tag) -> Optional[dict[str, Any]]:
        """Parse an event from the h3 heading and sibling elements."""
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

        # Location — look for known location names in parts after date
        location = "Back of Beyond Books, 83 N Main St, Moab, UT 84532"
        for part in parts:
            lower = part.lower()
            if 'star hall' in lower:
                location = "Star Hall, 159 E Center St, Moab, UT 84532"
            elif 'castle valley' in lower and 'town hall' in lower:
                location = "Castle Valley Town Hall, Castle Valley, UT"
            elif 'library' in lower:
                location = "Grand County Public Library, 257 E Center St, Moab, UT 84532"

        # Description from div.excerpt sibling
        description = ''
        excerpt_div = h3_tag.find_next_sibling('div', class_='excerpt')
        if excerpt_div:
            # Get text, skip img tags
            desc_parts = []
            for p in excerpt_div.find_all('p'):
                text = p.get_text(strip=True)
                # Skip image-only paragraphs and "Read More" links
                if text and not p.find('img', recursive=False):
                    desc_parts.append(text)
            description = '\n'.join(desc_parts[:3])  # first 3 paragraphs

        # URL from div.more sibling
        url = ''
        more_div = h3_tag.find_next_sibling('div', class_='more')
        if more_div:
            link = more_div.find('a')
            if link and link.get('href'):
                url = link['href']

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
