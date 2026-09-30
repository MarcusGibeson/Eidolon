# Development campaign failure at 479da08 (preserved)

`g_route4_campaign.py --quick` at commit 479da08 (a development check, not the CERT run) ended with exit code 1 and
two problems, preserved here byte-for-byte as the campaign wrote them:

- `gap_seeds / damaged_root_json`: refused with `data_root_experiment_unreadable`. The pre-lease data-root identity
  check read the working `root.json` rather than the committed name, so a damaged working copy (which R7 restores
  from the root commit) was refused.
- `review_seeds / module_rule_no_forbidden_module_loaded`: the probe's `-c` source contained a literal newline, so
  the probe never ran; it failed closed (rc=1), it did not pass.

Both were implementation defects, fixed in 7d90599 (with `DataRootIdentityTests`; 3 of its 4 tests fail on the old
code) and c9716bb. The rerun at c9716bb had 0 problems in all 11 sections. No criterion, threshold or expected
outcome was changed.
