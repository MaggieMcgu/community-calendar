#!/usr/bin/env python3
"""
Scraper for Climb Moab Gym events.

Squarespace site — uses the ?format=json API on the events collection page.
Returns upcoming events with timestamps, locations, descriptions, and URLs.

Usage:
    python scrapers/climb_moab.py -o cities/moab/climb_moab.ics
"""

import sys
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

from lib.squarespace import SquarespaceScraper


class ClimbMoabScraper(SquarespaceScraper):
    name = "Climb Moab"
    domain = "climbmoabgym.com"
    collection_url = "https://climbmoabgym.com/events"
    default_location = "Climb Moab, 773 S Main St, Moab, UT 84532"
    timezone = "America/Denver"


if __name__ == '__main__':
    ClimbMoabScraper.main()
