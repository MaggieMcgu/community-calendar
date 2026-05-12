# Moab Community Calendar — Sources

## Currently Implemented

### ICS Feeds (direct curl)
| Source | URL | Notes |
|--------|-----|-------|
| Grand County Library | CivicPlus catID=28 | Story times, book clubs, programs |
| Grand County | CivicPlus catID=14 | Gov, Sports, Community (incl. OSTARC) |
| Old Spanish Trail Arena | CivicPlus catID=30 | OSTA events |
| Moab City Council | CivicPlus catID=23 (moabcity.org) | Council, P&Z, boards |
| City of Moab Special Events | CivicPlus catID=25 (moabcity.gov) | City special events |
| City of Moab Recreation | CivicPlus catID=29 (moabcity.gov) | Recreation programs |
| Center Street Gym / Arena | Google Calendar ICS | Community events |

### Scrapers
| Source | Scraper | Notes |
|--------|---------|-------|
| Grand County HS (Red Devils) | `maxpreps.py --school grand-county-red-devils` | All sports. Mountain timezone. |
| Moab Museum | `moab_museum.py` (JSON-LD / MEC) | Low volume |
| Climb Moab | `climb_moab.py` (Squarespace) | `?format=json` API, quarterly volume |
| Back of Beyond Books | `back_of_beyond.py` (HTML) | WordPress, ~31 events/60d |
| Wellness Collective Moab | `wellness_collective.py` (GoDaddy) | Client-side rendered, needs headless |

## Non-Starters
- **Facebook Events** — Meta killed `/events/ical/` in 2019
- **Moab Area Chamber of Commerce** — `moab_chamber.py` scraper built + deactivated 2026-05-11 same day. Chamber re-lists member-venue events (museum exhibits, MIC lectures) so the importer created mis-attributed dupes with chamber-as-organizer. Direction reversed: chamber will embed MSN's calendar (Calendar Outbound plan), not the other way around. Scraper code retained at `scrapers/moab_chamber.py` in case the chamber's behavior changes.

## Prospective Sources (Future)
- Slickrock Cinemas (sponsorship + showtime feed)
- Moab MBA (may have iCal)
- USU Extension
- School District
- Moab Music Festival
- Grand Center
- KZMU
- Eventbrite Moab organizers
- 10-15 Moab churches (special events only)
