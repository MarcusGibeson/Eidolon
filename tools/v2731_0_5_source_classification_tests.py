from __future__ import annotations

"""Classify sources from structure, so authority reflects the source not our gaps.

Authority came from a short list of hostnames, so nearly every source arrived
unclassified - and an unclassified source can support no evidence dimension. The
measured runs showed 5 to 9 sources per trial failing on authority, which read as
poor quality when it was really absent metadata.

Rules are structural first: a documentation subdomain or path, a reserved
top-level domain, a package registry, a standards body. A small named set covers
project families whose URLs carry no structural signal. These checks exist partly
to keep that set small - if it grows one site at a time, the structural rules are
what need fixing.
"""

import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-0-5-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from research_source_classification import (
    _PRIMARY_SOURCE_FAMILIES,
    classification_reason,
    classify_source_kind,
)
from research_evidence_policy import AUTHORITY_KNOWN_AUTHORITATIVE, source_authority_state


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def kind(url: str) -> str:
    return classify_source_kind(url)


# --- structural signals, not enumerated identities ---------------------------

STRUCTURAL = [
    ("https://docs.python.org/3.14/library/asyncio-task.html", "primary_official", "documentation_subdomain"),
    ("https://developer.mozilla.org/en-US/docs/Web/API/fetch", "primary_official", "documentation_subdomain"),
    ("https://learn.microsoft.com/en-us/dotnet/csharp/", "primary_official", "documentation_subdomain"),
    ("https://docs.oracle.com/en/java/javase/21/docs/api/", "primary_official", "documentation_subdomain"),
    ("https://www.postgresql.org/docs/16/runtime-config-connection.html", "primary_official", "standards_body"),
    ("https://requests.readthedocs.io/en/latest/", "primary_official", "documentation_host"),
    # Documentation form on an unrecognised host: specialist material, not the publisher.
    ("https://example.org/documentation/getting-started", "specialist_secondary", "documentation_path"),
    ("https://www.rfc-editor.org/rfc/rfc9110", "primary_official", "standards_body"),
    ("https://www.w3.org/TR/webrtc/", "primary_official", "standards_body"),
    ("https://pypi.org/project/requests/", "primary_official", "package_registry"),
    ("https://crates.io/crates/serde", "primary_official", "package_registry"),
    ("https://www.nist.gov/publications/example", "primary_official", "reserved_tld"),
    ("https://cs.stanford.edu/research/paper", "primary_data", "academic_tld"),
    ("https://arxiv.org/abs/2401.00001", "primary_data", "scholarly_host"),
]
for url, expected_kind, expected_reason in STRUCTURAL:
    got = kind(url)
    require(got == expected_kind, f"{expected_reason}_classifies_{expected_kind} ({url.split('/')[2]} -> {got})")
    CHECKS.pop()
    require(classification_reason(url) == expected_reason, f"{url.split('/')[2]}_is_classified_by_{expected_reason}")

# A previously unclassified host now classified purely by URL shape.
require(kind("https://docs.github.com/en/actions") == "primary_official",
        "github_documentation_is_now_classified")
require(kind("https://packaging.python.org/en/latest/tutorials/packaging-projects/") == "primary_official",
        "a_project_subdomain_is_classified_by_its_family")

# --- community surfaces stay community ---------------------------------------

for url in ("https://discuss.python.org/t/tracking-cancellation/18352",
            "https://stackoverflow.com/questions/123/asyncio",
            "https://www.reddit.com/r/Twitch/comments/abc/",
            "https://github.com/python/cpython/issues/1234"):
    require(kind(url) == "community_experience", f"{url.split('/')[2]}_is_community_experience")

require(kind("https://github.com/python/cpython/blob/main/README.rst") == "primary_data",
        "code_hosting_outside_discussion_is_primary_data")

# --- the rules must not overreach --------------------------------------------

for url in ("https://vendor.example.com/pricing",
            "https://someblog.example.net/2026/why-our-tool-is-best",
            "https://mediabrief.example/creator-payment-survey"):
    require(kind(url) == "unknown", f"an_ordinary_page_stays_unclassified ({url.split('/')[2]})")
    CHECKS.pop()
CHECKS.append("ordinary_pages_are_left_unclassified_rather_than_guessed")

require(kind("") == "unknown", "an_empty_url_is_unclassified")
require(kind("not a url") == "unknown", "a_malformed_url_is_unclassified")
require(classification_reason("") == "no_host", "an_empty_url_reports_no_host")

# An already-known kind is never overridden by a guess.
require(classify_source_kind("https://docs.python.org/3/", "community_experience") == "community_experience",
        "a_supplied_classification_is_preserved")

# --- the named set must stay a last resort -----------------------------------

require(len(_PRIMARY_SOURCE_FAMILIES) <= 20,
        f"the_named_family_set_stays_small (currently {len(_PRIMARY_SOURCE_FAMILIES)})")
require(all(isinstance(reason, str) and reason.strip() for reason in _PRIMARY_SOURCE_FAMILIES.values()),
        "every_named_family_records_why_it_is_listed")
structural_only = [url for url, _, reason in STRUCTURAL if reason != "primary_source_family"]
require(len(structural_only) == len(STRUCTURAL),
        "every_documented_example_is_classified_structurally_not_by_name")

# --- precedence: overlapping rules must resolve the same way every time ------
# Rule order is the part of a structural classifier that rots silently. A
# documentation subdomain on a code host was already classified as a code host
# once; these pin every overlap that has a defensible answer.

PRECEDENCE = [
    # docs on a code host: reference material outranks the host it sits on.
    ("https://docs.github.com/en/actions/writing-workflows", "primary_official",
     "documentation_subdomain_outranks_code_host"),
    ("https://gitlab.com/group/project/-/issues/7", "community_experience",
     "discussion_path_outranks_code_host_default"),
    # a community subdomain on a project domain stays community.
    ("https://discuss.python.org/t/asyncio/1", "community_experience",
     "community_subdomain_outranks_primary_source_family"),
    ("https://forum.postgresql.example/t/pooling", "community_experience",
     "community_subdomain_outranks_documentation_path"),
    # scholarly and academic hosting.
    ("https://arxiv.org/abs/2401.00001", "primary_data", "scholarly_host_is_primary_data"),
    ("https://cs.example.edu/research/dataset", "primary_data", "university_research_page_is_primary_data"),
    ("https://cs.example.edu/~jsmith/notes.html", "unknown",
     "a_personal_page_does_not_inherit_institutional_authority"),
    ("https://example.edu/people/jsmith/blog", "unknown",
     "an_institutional_people_directory_page_is_not_primary_data"),
    # registries and standards.
    ("https://pypi.org/project/requests/", "primary_official", "package_registry_is_official"),
    ("https://www.w3.org/TR/webrtc/", "primary_official", "standards_body_is_official"),
    # reserved TLDs outrank everything structural beneath them.
    ("https://forum.agency.gov/threads/1", "primary_official",
     "a_reserved_tld_outranks_a_community_subdomain"),
]
for url, expected, name in PRECEDENCE:
    got = kind(url)
    require(got == expected, f"{name} (got {got})")

# Precedence must be deterministic, not dependent on evaluation happening to
# reach a rule first.
for url, expected, _ in PRECEDENCE:
    require(kind(url) == expected and kind(url) == expected, "precedence_is_stable_across_calls")
    CHECKS.pop()
CHECKS.append("precedence_is_stable_across_calls")

# --- mirrors: documentation form is not publisher authority ------------------
# A mirror, fork, syndicated copy or tutorial site can host faithful reference
# material without being the project that publishes it. A live run classified
# runebook.dev - a documentation mirror - as primary_official on the strength of
# its path alone.

from research_source_classification import REFERENCE_DOCUMENTATION_FORM, document_form  # noqa: E402

MIRRORS = [
    "https://runebook.dev/en/docs/python/library/asyncio-task",
    "https://tutorialsite.example/docs/python/asyncio",
    "https://someaggregator.example/documentation/postgres/pooling",
]
for url in MIRRORS:
    require(kind(url) == "specialist_secondary", f"a_documentation_mirror_is_not_primary_official ({url.split('/')[2]})")
    CHECKS.pop()
    require(document_form(url) == REFERENCE_DOCUMENTATION_FORM,
            f"a_documentation_mirror_is_still_recognised_as_documentation ({url.split('/')[2]})")
    CHECKS.pop()
CHECKS.append("a_documentation_mirror_is_not_primary_official")
CHECKS.append("a_documentation_mirror_is_still_recognised_as_documentation")

# The publisher's own surfaces keep their authority.
for url, why in (("https://docs.python.org/3.14/library/asyncio-task.html", "documentation subdomain"),
                 ("https://www.postgresql.org/docs/16/runtime-config-connection.html", "standards body"),
                 ("https://requests.readthedocs.io/en/latest/", "the project's own docs host")):
    require(kind(url) == "primary_official", f"an_authoritative_publisher_keeps_primary_official ({why})")
    CHECKS.pop()
CHECKS.append("authoritative_publishers_keep_primary_official")

# Form is reported for pages that are documentation, and withheld from those that are not.
require(document_form("https://docs.python.org/3.14/library/asyncio-task.html") == REFERENCE_DOCUMENTATION_FORM,
        "official_documentation_reports_documentation_form")
require(document_form("https://vendor.example.com/pricing") == "", "an_ordinary_page_reports_no_form")
require(document_form("") == "", "an_empty_url_reports_no_form")

# A mirror is still usable evidence, just not authoritative evidence.
mirror_state = source_authority_state({"public_url": MIRRORS[0], "source_kind": kind(MIRRORS[0]),
                                       "evidence_role": "independent_analysis"})
require(mirror_state == AUTHORITY_KNOWN_AUTHORITATIVE,
        "a_mirror_is_classified_rather_than_left_unknown")

# --- vendor documentation: classified, but not laundered ---------------------
# A vendor's own docs really are its official documentation. Classification says
# what it is; whether it may establish a claim about the vendor's market is a
# different question, decided by evidence role.

vendor_docs_url = "https://docs.vendor.example/product/getting-started"
require(kind(vendor_docs_url) == "primary_official", "vendor_documentation_is_still_official_documentation")
for role in ("first_party_product_claim", "promotional_summary"):
    require(source_authority_state({"public_url": vendor_docs_url, "source_kind": kind(vendor_docs_url),
                                    "evidence_role": role}) != AUTHORITY_KNOWN_AUTHORITATIVE,
            "a_first_party_role_still_withholds_authority")
    CHECKS.pop()
CHECKS.append("a_first_party_or_promotional_role_still_withholds_authority")

# --- the point of all this: authority stops reading as absent ----------------

docs = {"public_url": "https://docs.python.org/3.14/library/asyncio-task.html",
        "source_kind": kind("https://docs.python.org/3.14/library/asyncio-task.html"),
        "evidence_role": "independent_analysis"}
require(source_authority_state(docs) == AUTHORITY_KNOWN_AUTHORITATIVE,
        "official_documentation_now_reads_as_known_authoritative")

promotional = {"public_url": "https://docs.vendor.example/product",
               "source_kind": kind("https://docs.vendor.example/product"),
               "evidence_role": "promotional_summary"}
require(source_authority_state(promotional) != AUTHORITY_KNOWN_AUTHORITATIVE,
        "classification_does_not_launder_a_promotional_source")

print(json.dumps({"suite": "v2731.0.5-source-classification", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
