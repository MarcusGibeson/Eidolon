# Eidolon v1337.9 Browser Validation Checkpoint Validation

This checkpoint completes v1337 on top of the durable v1336.9 Process Operations checkpoint.

## Completed behavior

- Real Chromium is launched only for a sealed v1333 disposable candidate workspace with satisfied v1332 browser preconditions and an active workspace-matching standing command grant.
- Candidate-local HTML can be rendered without URL navigation; click, fill, and keypress interactions plus attached/visible/text checks are typed and bounded.
- HTTP(S) navigation is restricted to loopback hosts. External targets are rejected before browser launch and browser routing aborts non-loopback network requests.
- Screenshot files live only beneath external runtime data. Public evidence exposes size/digest and outcome metadata, never screenshot paths, raw URLs, selectors, or entered values.
- Browser/tool failures, managed-browser policy limitations, HTTP product failures, and product-UI check failures remain distinct evidence domains.
- On this host Chromium policy blocks loopback URLs with ERR_BLOCKED_BY_ADMINISTRATOR. The checkpoint therefore records loopback validation as policy-limited. A fresh page in the same real Chromium process can render a bounded offline fallback to prove browser-engine and screenshot behavior, but target checks are not run against that fallback and no loopback product success is claimed.
- Ordinary chat can inspect sealed browser evidence but cannot launch or interact with a browser.

## Focused evidence

- v1337.0-v1337.2 foundations: 5/5
- v1337.3-v1337.5 integration: 4/4
- v1337.6-v1337.8 reliability/adversarial: 5/5
- v1337.9 checkpoint: 5/5

Real-browser fixtures exercise DOM interaction, screenshot capture, external-target rejection, product-vs-browser failure classification, managed loopback-policy handling, duplicate convergence, sealed-record tamper rejection, and selected-source immutability.

## Authority and platform boundary

Browser validation is candidate-workspace-only and does not authorize external networking, source application, release, installation, provider contact, or independent action. Browser evidence is Linux-host Chromium evidence. Native Windows browser behavior remains external validation and is not claimed.
