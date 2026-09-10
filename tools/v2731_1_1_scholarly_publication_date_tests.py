from __future__ import annotations

"""Scholarly sources declare their publication dates; now they are read.

Science was the one sterile result in the seven-domain corpus. Its finding cited
three peer-reviewed articles on pmc.ncbi.nlm.nih.gov - primary sources - and the
reference currency layer refused all three as undated. They were not undated:

    <meta name="citation_publication_date" content="2021 Aug 23">

Two gaps were stacked. The page parser read only the article:published_time
family and never the Highwire, Dublin Core or PRISM vocabularies scholarly
publishers use. And the timestamp parser accepted only ISO, so "2021 Aug 23"
would have come back unparsed even once the tag was read. Fixing only the first
would have produced a check that runs and changes nothing.

This is a metadata repair, not a policy relaxation: the currency layer is
unchanged, and it now sees the dates that were always there. Partial dates
resolve to the start of their period, so imprecision can make a source look
older, never fresher.
"""

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True

from datetime import datetime, timezone

from governed_public_web_research_adapter import _VisibleTextParser as Parser
from research_web_intelligence_v2100 import _parse_timestamp, derive_source_freshness


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def utc(*parts: int) -> datetime:
    return datetime(*parts, tzinfo=timezone.utc)


# --- the timestamp parser reads scholarly shapes -----------------------------

for text, expected in (
    ("2021 Aug 23", utc(2021, 8, 23)),          # the PMC page that prompted this
    ("2021 August 23", utc(2021, 8, 23)),
    ("2021 Sept 5", utc(2021, 9, 5)),
    ("2021/08/23", utc(2021, 8, 23)),
    ("2021.08.23", utc(2021, 8, 23)),
    ("23 Aug 2021", utc(2021, 8, 23)),
    ("Aug 23, 2021", utc(2021, 8, 23)),
    ("aug 23 2021", utc(2021, 8, 23)),
):
    require(_parse_timestamp(text) == expected, "a_scholarly_date_shape_is_read")
    CHECKS.pop()
CHECKS.append("every_full_scholarly_date_shape_is_read")

# A partial date resolves to the start of its period: never fresher than stated.
require(_parse_timestamp("2021/08") == utc(2021, 8, 1), "a_year_month_date_is_the_first_of_the_month")
require(_parse_timestamp("2021 Aug") == utc(2021, 8, 1), "a_named_month_date_is_the_first_of_the_month")
require(_parse_timestamp("August 2021") == utc(2021, 8, 1), "a_month_year_date_is_the_first_of_the_month")
require(_parse_timestamp("2021") == utc(2021, 1, 1), "a_year_only_date_is_the_first_of_the_year")

# ISO is untouched: it is tried first, exactly as before.
require(_parse_timestamp("2021-08-23T10:00:00Z") == utc(2021, 8, 23, 10), "iso_with_a_zone_is_unchanged")
require(_parse_timestamp("2021-08-23") == utc(2021, 8, 23), "an_iso_date_is_unchanged")

# Junk stays unknown rather than becoming a date.
for text in ("2021 Spring", "2021 Foo 3", "2021/13/40", "0021", "1234", "not a date", "", "   "):
    require(_parse_timestamp(text) is None, "junk_is_not_a_date")
    CHECKS.pop()
CHECKS.append("no_junk_string_becomes_a_date")

# --- freshness now sees those dates ------------------------------------------

dated = derive_source_freshness(published_at="2021 Aug 23", freshness_policy="slow_changing",
                                now=utc(2022, 8, 23))
require(dated["freshness_known"] is True, "a_scholarly_date_makes_freshness_known")
require(dated["fresh_enough"] is True, "a_year_old_article_is_fresh_for_a_slow_changing_question")
stale = derive_source_freshness(published_at="2021 Aug 23", freshness_policy="current",
                                now=utc(2022, 8, 23))
require(stale["freshness_known"] is True and stale["fresh_enough"] is False,
        "the_same_article_is_correctly_stale_for_a_current_question")
undated = derive_source_freshness(published_at="2021 Spring", freshness_policy="slow_changing",
                                  now=utc(2022, 8, 23))
require(undated["freshness_known"] is False, "an_unreadable_date_still_stays_unknown")

# --- the page parser reads the scholarly vocabularies ------------------------

def dates_in(head: str) -> list[str]:
    parser = Parser()
    parser.feed(f"<html><head>{head}</head><body><p>Body text.</p></body></html>")
    parser.close()
    return list(parser.publication_dates)


for tag in ("citation_publication_date", "citation_online_date", "citation_date",
            "DC.date", "DC.Date.Issued", "dcterms.issued", "DCTERMS.date", "dcterms.created",
            "prism.publicationDate", "PRISM.onlineDate"):
    require(dates_in(f'<meta name="{tag}" content="2021 Aug 23">') == ["2021 Aug 23"],
            "a_scholarly_meta_vocabulary_is_read")
    CHECKS.pop()
CHECKS.append("every_scholarly_meta_vocabulary_is_read_case_insensitively")

# The existing vocabularies still work.
require(dates_in('<meta property="article:published_time" content="2024-03-01T00:00:00Z">')
        == ["2024-03-01T00:00:00Z"], "article_published_time_is_still_read")

# An unrelated meta tag is still not mistaken for a publication date.
require(dates_in('<meta name="citation_title" content="2021 Aug 23">') == [],
        "a_non_date_citation_tag_is_not_read_as_a_date")
require(dates_in('<meta name="description" content="2021 Aug 23">') == [],
        "a_description_is_not_read_as_a_date")

# The exact page that prompted the repair, end to end: tag read, date parsed.
pmc = dates_in('<meta name="citation_publication_date" content="2021 Aug 23">')
require(pmc and _parse_timestamp(pmc[0]) == utc(2021, 8, 23),
        "the_pmc_publication_date_is_read_and_parsed_end_to_end")

print(json.dumps({"suite": "v2731.1.1-scholarly-publication-date", "passed": len(CHECKS),
                  "total": len(CHECKS), "ok": True, "checks": CHECKS}))
