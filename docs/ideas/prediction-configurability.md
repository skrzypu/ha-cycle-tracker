# Ideas: Configurable Prediction and Statistics Window

Theme: how many past cycles feed the prediction and the displayed statistics, and
whether that number is the user's choice instead of a product constant.

---

### I-013: Configurable number of cycles used in calculation (6 → 12)

- **Status:** idea
- **Problem:** BDR-0004 fixes the history used for prediction to the last 6
  completed cycles (`docs/bdr/0004-prediction-is-a-window-not-a-date.md:42`), and
  it is not user-configurable. Cycle-length statistics use the same window
  (`domain/statistics.py:64` passes `config.history_window`), so both the
  prediction and the displayed averages under-sample long or irregular
  histories. In code the window is a `PredictionConfig` field that defaults to 6
  (`domain/ports.py:20,37`), which the coordinator never overrides
  (`coordinator.py:415-420`) and the config flow never asks for. A user with a
  long history asked for 12 because 6 is too few for her.
- **Idea:** make the window size a setting in the config entry options
  (ADR-0011), with a **minimum of 6 cycles** and the user's requested value of
  12 as the intended setting; decide the upper bound and the default, and
  whether prediction and statistics share one number or have separate ones.
- **Value:** predictions and averages reflect more of the user's real history;
  users with long histories stop seeing values jump when a single old cycle
  drops out of the window.
- **Constraints / conflicts:** this contradicts BDR-0004 as decided — its
  history rule is "the last 6 completed cycles" and its confidence formula is
  `min(1, 1 − σ/mean) × min(1, n/6)` (same file, line 51) — so promoting the idea
  means superseding or amending BDR-0004, not only changing code. Filtering
  happens before the window: out-of-range cycles and everything before the most
  recent gap over 90 days are removed first, and an excluded cycle never takes a
  window slot (`domain/history.py:4-7`, `domain/history.py:48-51`). More cycles
  widen σ for irregular users, so stability trades against responsiveness, and
  the confidence normalization has to follow the configured N — otherwise
  confidence is always 1 above 6 cycles. The 6-cycle floor applies to the
  setting, not to the data: it is an upper cap on cycles used, so a user with 2–5
  completed cycles still gets a prediction. BDR-0004's separate rule — at least
  2 completed cycles before prediction returns a value
  (`docs/bdr/0004-prediction-is-a-window-not-a-date.md:43`) — is not changed by
  this idea.
- **Dependencies:**
  - BDR-0004 (fixed 6-cycle history and confidence formula; the idea conflicts
    with it and must name it) — known
  - ADR-0011 (the config entry owns settings) — known
  - I-015 (chart of period and cycle lengths; whether the chart shows the
    prediction window or all history, and so whether one setting serves both, is
    not decided) — dependency unknown
- **Open questions:** one number or two (prediction versus the statistics
  display)? Upper bound (for example 6–24, with 6 as the fixed floor) and
  default — offer 12 for new entries, keep 6 for existing ones? Does the
  confidence denominator become the configured N or stay a constant? Should the
  statistics sensor keep an all-history figure alongside
  the windowed one (still open in `prediction-algorithms.md`, question 9)? Is
  this options-flow only, or also a service to change it?
- **Decision:** —
