# v1206.3-v1206.5 Browser Runtime Test Adapter Foundations

Adds a bounded Chromium runtime adapter for already-approved, generated, and isolated small websites. The adapter serves the verified external workspace only from the verified local workspace, blocks external requests and service workers, captures content-free runtime evidence, and grants no apply, repair, provider, source, model, network, release, or independent authority.

The adapter records navigation readiness, DOM readiness, runtime-marker presence, console/page-error/request counts and digests, blocked external requests, popups, and downloads. Raw console text, DOM text, screenshots, filenames, source, paths, and browser output remain private or are not persisted.

Next: v1206.6-v1206.8 Node, JavaScript, and Python adapter reliability and cross-platform hardening.
