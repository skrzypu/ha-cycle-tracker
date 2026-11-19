# Parked OpenSpec Changes

Historical reference only. Both changes that were once drafted here were later
revived, implemented and archived: `google-sheets-source-of-truth` (archived
2026-11-17) and `add-lovelace-card` (archived 2026-11-19). The draft files remain
here as design reference. `openspec list` does not see them, and nothing here is
active work.

| Change | Parked on | Status | Why / revival |
|---|---|---|---|
| `google-sheets-source-of-truth` | 2026-11-09 | superseded — archived 2026-11-17 | Was parked because the domain model was not settled; revived, implemented and archived. Historical reference only. |
| `add-lovelace-card` | 2026-11-09 | superseded — archived 2026-11-19 | Was parked pending stable entities and a data model; revived, implemented and archived. Historical reference only. |

## Historical revival notes (no longer applicable)

Both drafts have already been revived and archived. The steps below are kept to
document how that was done:

1. Move the draft directory out of `docs/ideas/parked/` back under
   `openspec/changes/`.
2. Re-read the specs against the current `openspec/specs/` and the accepted ADRs;
   update or rewrite them.
3. Run `openspec validate <name> --strict` and `openspec status --change <name>`.
4. Only then start `/opsx-apply`.

Nothing in this folder is committed to a decision. Deleting a directory here is
a valid outcome.
