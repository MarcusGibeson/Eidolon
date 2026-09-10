# Desktop Codex Handoff: v1205.9

Candidate role: General Small-Project Implementation checkpoint candidate only.

## Windows verification

1. Verify the candidate ZIP SHA-256 against the supplied digest.
2. Extract beneath exactly one `Eidolon\` root.
3. Confirm no packaged `data\`, caches, bytecode, provider payloads, conversations, memories, credentials, or private project paths.
4. Run:

```powershell
python tools\v1205_9_general_small_project_implementation_checkpoint_tests.py
python tools\release_verify.py --profile quick --json
```

5. Verify a direct request such as `Build me a to-do webpage` creates one approval-gated proposal without implementation before approval.
6. Audit the mixed turn:

`It would be nice to hear your voice. Build your own text-to-speech system with a voice you choose.`

Expected v1205.9 result is known incomplete behavior: conversational handling occurs, but no separate proposal is created. Do not certify mixed-turn distinction as working.

Required next implementation bundle: **v1206.0-v1206.2 Natural Conversation and Command Distinction**.

Do not install, promote, certify, or declare the v1205.9 candidate final from this handoff.
