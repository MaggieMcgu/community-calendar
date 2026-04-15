#!/usr/bin/env python3
"""
Scraper for Moab Arts & Recreation Center (MARC) events.

The MARC website (moabarts.org) runs on Wix with Wix Events.
Individual event pages have JSON-LD schema.org Event markup.
Event URLs are discovered via the Wix-generated sitemap at
/event-pages-sitemap.xml.

Usage:
    python scrapers/moab_arts.py -o cities/moab/moab_arts.ics
"""

import sys
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])

import logging
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

from lib.jsonld import JsonLdScraper

logger = logging.getLogger(__name__)

SITEMAP_URL = "https://www.moabarts.org/event-pages-sitemap.xml"


class MoabArtsScraper(JsonLdScraper):
    name = "Moab Arts & Recreation Center"
    domain = "moabarts.org"
    default_location = "Moab Arts & Recreation Center, 111 E 100 N, Moab, UT 84532"
    timezone = "America/Denver"

    def get_urls(self) -> list[str]:
        """Discover event page URLs from the Wix sitemap."""
        logger.info(f"Fetching sitemap: {SITEMAP_URL}")
        req = Request(SITEMAP_URL, headers=self.headers)
        try:
            with urlopen(req, timeout=15) as resp:
                xml_content = resp.read().decode('utf-8')
        except (HTTPError, URLError) as e:
            logger.error(f"Failed to fetch sitemap: {e}")
            return []

        # Parse sitemap XML
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.error(f"Failed to parse sitemap XML: {e}")
            return []

        # Extract all <loc> URLs — namespace-aware
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = []
        for loc in root.findall('.//sm:loc', ns):
            url = loc.text.strip() if loc.text else ''
            if '/event-details/' in url:
                urls.append(url)

        logger.info(f"Found {len(urls)} event URLs in sitemap")
        return urls


if __name__ == '__main__':
    MoabArtsScraper.main()
