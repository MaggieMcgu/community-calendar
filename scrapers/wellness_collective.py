#!/usr/bin/env python3
"""
Scraper for Wellness Collective Moab events.

GoDaddy Website Builder site with calendar widget. Events served from
calendar.apps.secureserver.net JSON API — no headless browser needed.

Usage:
    python scrapers/wellness_collective.py -o cities/moab/wellness_collective.ics
"""

import sys
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

from lib.godaddy import GoDaddyScraper


class WellnessCollectiveScraper(GoDaddyScraper):
    name = "Wellness Collective Moab"
    domain = "wellnesscollectivemoab.com"
    website_id = "850abeb2-a96f-4bb3-941d-245ce2f0e203"
    section_id = "9c296a07-7f6a-4f27-a79a-bc4c6982a216"
    widget_id = "f33a9bca-c60a-4de5-8fa4-b78b6fd1c4ba"
    default_location = "Wellness Collective, 76 S 100 W, Moab, UT 84532"
    timezone = "America/Denver"


if __name__ == '__main__':
    WellnessCollectiveScraper.main()
