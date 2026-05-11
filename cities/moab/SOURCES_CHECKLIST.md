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
| Moab Area Chamber of Commerce | `moab_chamber.py` (GrowthZone per-event .ics) | Walks listing in 30-day windows, fetches each event's .ics. ~10 events visible at once. |

## Non-Starters
- **Facebook Events** — Meta killed `/events/ical/` in 2019

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
