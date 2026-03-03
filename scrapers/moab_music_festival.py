#!/usr/bin/env python3
"""
Scraper for Moab Music Festival events.

WordPress site with Modern Events Calendar (MEC) plugin — same pattern as
Moab Museum. Outputs schema.org Event JSON-LD. Seasonal: Winterlude (Feb)
and main festival (Sep).

Usage:
    python scrapers/moab_music_festival.py -o cities/moab/moab_music_festival.ics
"""

import sys
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

from lib.jsonld import JsonLdScraper


class MoabMusicFestivalScraper(JsonLdScraper):
    name = "Moab Music Festival"
    domain = "moabmusicfest.org"
    url = "https://moabmusicfest.org/calendar/"
    default_location = "Star Hall, 159 E Center St, Moab, UT 84532"
    timezone = "America/Denver"


if __name__ == '__main__':
    MoabMusicFestivalScraper.main()
