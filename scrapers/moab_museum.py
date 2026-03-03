#!/usr/bin/env python3
"""
Scraper for Moab Museum events.

Uses JSON-LD extraction — the site runs WordPress with Modern Events Calendar (MEC),
which outputs schema.org Event data. The JsonLdScraper base handles MEC's
malformed description fields automatically.

Usage:
    python scrapers/moab_museum.py -o cities/moab/moab_museum.ics
"""

import sys
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

from lib.jsonld import JsonLdScraper


class MoabMuseumScraper(JsonLdScraper):
    name = "Moab Museum"
    domain = "moabmuseum.org"
    url = "https://moabmuseum.org/calendar-of-events/"
    default_location = "Moab Museum, 118 E Center St, Moab, UT 84532"
    timezone = "America/Denver"


if __name__ == '__main__':
    MoabMuseumScraper.main()
