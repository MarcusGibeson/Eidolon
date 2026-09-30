# Clean development campaign provenance

This is the preserved **development-only** `--quick` campaign report. It is not
the official G-ROUTE4 certification report and does not replace the full CERT
campaign.

- Report: `CAMPAIGN_QUICK_C9716BB_REPORT.json`
- Literal report SHA-256: `a9ffe55644afda710d270ce3e816ffca20db60e2682f47d89934093abf316271`
- Run commit: `c9716bbd4735e6db11ba6aed577fbf6258e9701f`
- Reviewed implementation checkpoint: `b675ccb2a76c8e10221f34006ebb6544ec9b16db`
- Source transcript: Claude session `ee541c8c-4d7b-4754-92ec-54959f6c39f3`,
  `C:\Users\marcu\.claude\projects\C--Users-marcu-Eidolon\ee541c8c-4d7b-4754-92ec-54959f6c39f3.jsonl`
- Transcript line 13120: the tool command checks out `C:\Users\marcu\Eidolon-g4adj`, prints `git rev-parse --short HEAD`, then runs `python -B -u tools/g_route4_campaign.py --quick` with the scratchpad `campaign_quick` workdir. The command was issued after the `c9716bb` commit.
- Transcript line 13156: the terminal result begins `c9716bb` and `campaign exit 0`, ends with `seconds 2831.2`, and lists all 11 campaign sections with zero problems.
- Transcript line 13183: `build_implementation_status.py` consumed this exact scratchpad `campaign_report.json` with `--campaign-commit c9716bb`.

The preserved report contains all 11 sections: `clean_kills`, `clean_power_loss`,
`transport_failure_kills`, `torn_entries`, `torn_ledger`, `flush_failures`,
`environment`, `gap_seeds`, `review_seeds`, `resumed_interrupts`, and
`power_loss_subsets`. Each has `problems: []`.

The report itself does not embed a commit ID; the launch/terminal transcript
supplies that binding. The source transcript is not copied here because it
contains unrelated private session content. A fresh review must verify both
the preserved report hash and the transcript evidence; the status summary
alone is insufficient. No `tools/` file changed between the run commit and
the reviewed implementation checkpoint.

The original report is 3,944 bytes with 142 CRLF line endings. The local
`.gitattributes` disables text normalization for this report only, so its
committed blob retains the literal source hash. Git's whitespace checker may
flag those preserved CRLF bytes; they are not added trailing spaces.
