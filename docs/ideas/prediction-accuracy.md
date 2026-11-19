# Ideas: Prediction Accuracy

Theme: checking past predictions against what actually happened, and using that
feedback instead of guessing.

---

### I-018: Score past predictions against what actually happened

- **Status:** idea
- **Problem:** BDR-0004 promises a window with an uncertainty band and a
  confidence, but nothing tells the user — or us — whether those windows were
  right. Prediction is recomputed from current history on every refresh
  (`coordinator.py:422-433`, the `snapshot` property calling `build_snapshot`),
  so the prediction that was shown before a cycle started is not kept; after the
  fact it cannot be compared with the actual start without replaying the
  algorithm.
- **Idea:** keep a record of each prediction made — predicted date, uncertainty
  window, confidence, computed-at timestamp and the history it used — and
  compare it with the next actual start. Report a hit rate inside the window,
  the signed day error and whether the confidence bands are calibrated. Expose a
  compact summary as statistics-sensor attributes; a full replay/backtest over
  existing history is the fallback when no snapshots exist yet.
- **Value:** users can judge whether to trust the window rather than taking a
  number on faith; we get evidence to tune the window size (I-013) and the ±1σ
  choice instead of reacting to one user report.
- **Constraints / conflicts:** the honest option is to store snapshots, which
  means new data and a retention decision under ADR-0001; the alternative is a
  deterministic replay of the algorithm against the history as it stood before
  each cycle, which must be shown to reproduce the published prediction.
  Backdating or closing a past period (I-007) rewrites the history that a score
  was based on, so old scores must be invalidated or marked provisional. New
  users will have too few scored predictions for a meaningful rate. "Accuracy"
  must be reported as an observation about past windows, not turned into a new
  promise that contradicts BDR-0004.
- **Dependencies:**
  - BDR-0004 (windows, confidence and outlier rules being scored) — known
  - ADR-0001 (local-only storage, retention) — known
  - I-007 (backdating and closing past periods invalidate past scores) — known
  - I-013 (window size is the main tuning knob this would inform) — known
  - I-017 (diagnostics surface; whether it should show the underlying records
    is not decided) — dependency unknown
- **Open questions:** store snapshots or replay on demand? Window hit rate or
  point error as the headline metric? How many past predictions to keep? Do
  history edits reset the score? Is this an attribute on the statistics sensor
  or a separate sensor? Should I-017 (diagnostics) surface the stored prediction
  records? How should an "unknown" prediction be scored — counted as a miss or
  excluded?
- **Decision:** —
