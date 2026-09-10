from __future__ import annotations

"""Classify what kind of source a URL is, from structure before identity.

Authority was previously derived from a short list of hostnames, so almost every
source arrived unclassified, and an unclassified source can support no evidence
dimension. The gap was metadata, not quality: official Python documentation and a
vendor landing page were equally "unknown".

Rules here are structural wherever possible - a documentation subdomain, a
documentation path, a reserved top-level domain, a package registry's canonical
URL shape - because those generalise to sites nobody has enumerated. A small named
set covers primary-source families whose URLs carry no structural signal, and each
entry says why it is there. The intent is that the named set stays small; if it
starts absorbing sites one at a time, the structural rules are the thing to fix.

Classification says what a source *is*. Whether it may support a particular claim
is decided elsewhere, and a promotional page stays promotional whatever this
returns.
"""

import re
from urllib.parse import urlsplit

CONTRACT_VERSION = "v2731.0.6"

# Subdomain labels that name a documentation or developer-reference surface.
_DOCUMENTATION_LABELS = frozenset({
    "docs", "doc", "documentation", "developer", "developers", "devcenter",
    "learn", "reference", "manual", "apidocs", "readthedocs",
})

# Path segments that name reference material rather than marketing.
_DOCUMENTATION_PATHS = re.compile(
    r"/(?:docs?|documentation|reference|manual|handbook|javadoc|godoc|rfc|spec|specs|specification)(?:/|$)",
    re.IGNORECASE,
)

# Community surfaces: a person's experience, not a publisher's statement.
_COMMUNITY_LABELS = frozenset({"forum", "forums", "community", "discuss", "discussion", "answers", "ask"})
_COMMUNITY_HOSTS = frozenset({
    "stackoverflow.com", "serverfault.com", "superuser.com", "askubuntu.com",
    "news.ycombinator.com", "lobste.rs", "reddit.com", "indiehackers.com", "producthunt.com",
})
_COMMUNITY_PATHS = re.compile(r"/(?:issues|discussions|questions|threads|t)(?:/|$)", re.IGNORECASE)

# Canonical package registries: the authoritative record for a package.
_PACKAGE_REGISTRIES = frozenset({
    "pypi.org", "npmjs.com", "crates.io", "rubygems.org", "nuget.org",
    "packagist.org", "hex.pm", "pkg.go.dev", "hackage.haskell.org", "metacpan.org",
})

# Standards bodies publish the specification itself, not commentary on it.
_STANDARDS_BODIES = frozenset({
    "w3.org", "ietf.org", "rfc-editor.org", "iana.org", "iso.org", "unicode.org",
    "whatwg.org", "ecma-international.org", "oasis-open.org", "khronos.org", "postgresql.org",
})

# Primary-source families whose canonical URLs carry no structural signal.
# Each is the project's own site, publishing its own reference material.
_PRIMARY_SOURCE_FAMILIES = {
    "python.org": "the CPython project and PEP index",
    "openjdk.org": "the OpenJDK project",
    "kernel.org": "the Linux kernel project",
    "gnu.org": "GNU project manuals",
    "mozilla.org": "MDN and Mozilla project documentation",
    "sqlite.org": "the SQLite project",
    "rust-lang.org": "the Rust project",
    "golang.org": "the Go project",
    "go.dev": "the Go project",
    "nodejs.org": "the Node.js project",
    "kubernetes.io": "the Kubernetes project",
    "apache.org": "Apache Software Foundation projects",
}

# Scholarly and dataset publishers.
_SCHOLARLY_HOSTS = frozenset({"arxiv.org", "doi.org", "pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov", "zenodo.org"})

_CODE_HOSTS = frozenset({"github.com", "gitlab.com", "bitbucket.org", "codeberg.org"})


def _registrable(host: str) -> str:
    """Best-effort registrable domain, enough to recognise a project family."""
    parts = [part for part in host.split(".") if part]
    if len(parts) < 2:
        return host
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "net", "ac", "gov"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def classify_source_kind(url: str, supplied: str = "unknown") -> str:
    """Return a source kind for a URL, preferring an already-known classification."""
    kind = str(supplied or "").strip().lower()
    if kind and kind != "unknown":
        return kind

    parsed = urlsplit(str(url or ""))
    host = (parsed.hostname or "").lower().strip(".")
    if not host:
        return "unknown"
    path = parsed.path or "/"
    labels = host.split(".")
    domain = _registrable(host)

    # Reserved top-level domains state the publisher's nature.
    if host.endswith(".gov") or ".gov." in host or host.endswith(".mil") or host.endswith(".int"):
        return "primary_official"
    if host.endswith(".edu") or host.endswith(".ac.uk"):
        return "primary_data"

    # Community surfaces first: a project forum is experience, not reference.
    if domain in _COMMUNITY_HOSTS or any(label in _COMMUNITY_LABELS for label in labels[:-2] or labels[:1]):
        return "community_experience"

    # A documentation subdomain outranks the site it sits on: docs.github.com
    # publishes reference material, whatever github.com is otherwise.
    if labels and labels[0] in _DOCUMENTATION_LABELS:
        return "primary_official"
    if host.endswith("readthedocs.io") or host.endswith("readthedocs.org"):
        return "primary_official"

    if domain in _CODE_HOSTS:
        return "community_experience" if _COMMUNITY_PATHS.search(path) else "primary_data"

    if domain in _SCHOLARLY_HOSTS:
        return "primary_data"
    if domain in _PACKAGE_REGISTRIES:
        return "primary_official"
    if domain in _STANDARDS_BODIES:
        return "primary_official"
    if _DOCUMENTATION_PATHS.search(path):
        return "primary_official"

    if domain in _PRIMARY_SOURCE_FAMILIES:
        return "primary_official"

    return "unknown"


def classification_reason(url: str) -> str:
    """Which rule family classified a URL, for measuring coverage."""
    parsed = urlsplit(str(url or ""))
    host = (parsed.hostname or "").lower().strip(".")
    if not host:
        return "no_host"
    path = parsed.path or "/"
    labels = host.split(".")
    domain = _registrable(host)
    if host.endswith((".gov", ".mil", ".int")) or ".gov." in host:
        return "reserved_tld"
    if host.endswith(".edu") or host.endswith(".ac.uk"):
        return "academic_tld"
    if domain in _COMMUNITY_HOSTS or any(label in _COMMUNITY_LABELS for label in labels[:-2] or labels[:1]):
        return "community_surface"
    if labels and labels[0] in _DOCUMENTATION_LABELS:
        return "documentation_subdomain"
    if host.endswith(("readthedocs.io", "readthedocs.org")):
        return "documentation_host"
    if domain in _CODE_HOSTS:
        return "code_host"
    if domain in _SCHOLARLY_HOSTS:
        return "scholarly_host"
    if domain in _PACKAGE_REGISTRIES:
        return "package_registry"
    if domain in _STANDARDS_BODIES:
        return "standards_body"
    if _DOCUMENTATION_PATHS.search(path):
        return "documentation_path"
    if domain in _PRIMARY_SOURCE_FAMILIES:
        return "primary_source_family"
    return "unclassified"


__all__ = ["CONTRACT_VERSION", "classify_source_kind", "classification_reason"]
