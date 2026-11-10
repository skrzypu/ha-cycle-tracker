# Parked OpenSpec Changes

Changes that were drafted before their turn. They are kept as design reference,
not as active work. `openspec list` does not see them, and nothing here should be
implemented without an explicit decision to revive it.

| Change | Parked on | Why | Revive when |
|---|---|---|---|
| `google-sheets-source-of-truth` | 2026-11-09 | The domain data model is not settled; the sheet schema depends on it. ADR-0004 is `proposed`. | The data model and repository port are decided. |
| `add-lovelace-card` | 2026-11-09 | The card is roadmap Phase 1 but depends on stable entities and a data model; UI work comes after the domain. | The data model is stable and the entity set is final. |

## How to revive

1. Move the directory back to `openspec/changes/<name>/`.
2. Re-read the specs against the current `openspec/specs/` and the accepted ADRs;
   update or rewrite them.
3. Run `openspec validate <name> --strict` and `openspec status --change <name>`.
4. Only then start `/opsx-apply`.

Nothing in this folder is committed to a decision. Deleting a directory here is
a valid outcome.
