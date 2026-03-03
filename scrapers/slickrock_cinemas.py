#!/usr/bin/env python3
"""
Scraper for Slickrock Cinemas 3 showtimes via CinemaClock.

Slickrock doesn't have its own website or submit to any aggregator API.
CinemaClock (cinemaclock.com) is the only source with server-side rendered
showtime data in HTML — no JavaScript execution needed.

Theater ID: 5894
URL: https://www.cinemaclock.com/movie-theaters/slickrock-cinemas-3

Usage:
    python scrapers/slickrock_cinemas.py -o cities/moab/slickrock_cinemas.ics
"""

import sys
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

import re
from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from lib.base import BaseScraper
from lib.utils import DEFAULT_HEADERS


MOUNTAIN = ZoneInfo('America/Denver')

THEATER_URL = "https://www.cinemaclock.com/movie-theaters/slickrock-cinemas-3"
LOCATION = "Slickrock Cinemas, 580 Kane Creek Blvd, Moab, UT 84532"


class SlickrockCinemasScraper(BaseScraper):
    """Scraper for Slickrock Cinemas showtimes from CinemaClock."""

    name = "Slickrock Cinemas"
    domain = "cinemaclock.com"
    timezone = "America/Denver"

    def fetch_events(self) -> list[dict[str, Any]]:
        """Fetch showtimes from CinemaClock theater page."""
        self.logger.info(f"Fetching {THEATER_URL}")

        resp = requests.get(THEATER_URL, headers=DEFAULT_HEADERS, timeout=30)
        resp.raise_for_status()

        return self._parse_showtimes(resp.text)

    def _parse_showtimes(self, html: str) -> list[dict[str, Any]]:
        """Extract movie showtimes from CinemaClock HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        events = []
        now = datetime.now(MOUNTAIN)
        current_year = now.year

        # Each movie is in a div.showtimeblock with class cin5894
        for block in soup.select('div.showtimeblock.cin5894'):
            # Get movie title
            title_el = block.select_one('h3.movietitle a')
            if not title_el:
                continue
            movie_title = title_el.get_text(strip=True)

            # Get genre/rating info for description
            genre_el = block.select_one('p.moviegenre')
            description_parts = []
            if genre_el:
                genre_text = genre_el.get_text(' ', strip=True)
                # Clean up rating spans and whitespace
                genre_text = re.sub(r'\s+', ' ', genre_text).strip()
                if genre_text:
                    description_parts.append(genre_text)

            # Get movie detail URL for the description
            movie_url = ''
            title_link = block.select_one('h3.movietitle a')
            if title_link and title_link.get('href'):
                movie_url = f"https://www.cinemaclock.com{title_link['href']}"

            # Parse showtimes from timesother paragraphs
            for times_p in block.select('p.timesother'):
                # Each <s> or top-level <u> is a day's showtimes
                # Structure: <u>Day <span class="timesdate">Mon DD</span></u><i><span data-time="HHMM">H:MM</span>...</i>
                # Days can be in <s> tags (future days) or bare (today)
                day_sections = self._extract_day_sections(times_p)

                for day_str, times in day_sections:
                    for time_str in times:
                        event = self._create_showtime_event(
                            movie_title, day_str, time_str,
                            current_year, now, description_parts, movie_url
                        )
                        if event:
                            events.append(event)

        self.logger.info(f"Found {len(events)} showtime events")
        return events

    def _extract_day_sections(self, times_p) -> list[tuple[str, list[str]]]:
        """Extract (day_string, [time_strings]) pairs from a timesother paragraph."""
        sections = []

        # Get all the HTML content and parse day/time pairs
        # The structure alternates: <u>day</u><i>times</i> possibly wrapped in <s>
        current_day = None
        current_times = []

        for child in times_p.children:
            tag = getattr(child, 'name', None)

            if tag == 'u':
                # New day - save previous if exists
                if current_day and current_times:
                    sections.append((current_day, current_times))
                date_span = child.select_one('span.timesdate')
                current_day = date_span.get_text(strip=True) if date_span else None
                current_times = []

            elif tag == 'i':
                # Times for current day
                for time_span in child.select('span[data-time]'):
                    time_val = time_span.get('data-time', '')
                    if time_val:
                        current_times.append(time_val)

            elif tag == 's':
                # Wrapped day section (future days)
                inner_u = child.find('u')
                if inner_u:
                    if current_day and current_times:
                        sections.append((current_day, current_times))
                    date_span = inner_u.select_one('span.timesdate')
                    current_day = date_span.get_text(strip=True) if date_span else None
                    current_times = []

                inner_i = child.find('i')
                if inner_i:
                    for time_span in inner_i.select('span[data-time]'):
                        time_val = time_span.get('data-time', '')
                        if time_val:
                            current_times.append(time_val)

        # Don't forget the last section
        if current_day and current_times:
            sections.append((current_day, current_times))

        return sections

    def _create_showtime_event(
        self, movie_title: str, day_str: str, time_str: str,
        current_year: int, now: datetime,
        description_parts: list[str], movie_url: str
    ) -> Optional[dict[str, Any]]:
        """Create a single showtime event dict."""
        # Parse date: "Mar 5", "Mar 6", etc.
        try:
            # time_str is HHMM format like "1900", "1300"
            hour = int(time_str[:2])
            minute = int(time_str[2:])

            # Parse "Mon DD" format
            dt = datetime.strptime(f"{day_str} {current_year}", "%b %d %Y")
            # Handle year rollover (Dec showtimes seen in January)
            if dt.month < now.month - 1:
                dt = dt.replace(year=current_year + 1)

            dtstart = dt.replace(hour=hour, minute=minute, tzinfo=MOUNTAIN)
        except (ValueError, IndexError):
            return None

        # Skip past showtimes
        if dtstart < now:
            return None

        # Assume ~2 hour runtime
        dtend = dtstart + timedelta(hours=2)

        description = '\n'.join(description_parts)
        if movie_url:
            description += f"\n\n{movie_url}"

        return {
            'title': f"{movie_title} — Slickrock Cinemas",
            'dtstart': dtstart,
            'dtend': dtend,
            'location': LOCATION,
            'description': description.strip(),
            'url': movie_url,
        }


if __name__ == '__main__':
    SlickrockCinemasScraper.main()
