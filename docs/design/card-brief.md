# Design Brief: Cycle Tracker Lovelace Card

Status: draft, 2026-11-09. Companion to
`openspec/changes/add-lovelace-card/`. Open questions are for the user; nothing
here is final.

## Purpose

Give the user a single glanceable surface for their cycle and a one-tap way to
log a period start or end, without opening Developer Tools or an automation.

## Audience and context of use

- One primary user, on a phone, often in a hurry or not feeling well.
- Also usable on a desktop dashboard.
- Private data on a personal dashboard; no sharing features.

## Questions the card must answer, in priority order

1. Where am I in my cycle right now? (cycle day and phase)
2. When is my next period? (days remaining, then the date)
3. How do I log that a period started or ended? (two actions)

Secondary: days until ovulation, next ovulation date.

## Content inventory

| Element | Source | Notes |
|---|---|---|
| Cycle day | `sensor.cycle_tracker_cycle_day` | Number plus "day" |
| Cycle phase | `sensor.cycle_tracker_cycle_phase` | menstrual / follicular / ovulatory / luteal |
| Days until period | `sensor.cycle_tracker_days_until_period` | Most actionable number |
| Next period date | `sensor.cycle_tracker_next_period_date` | ISO date, format with locale |
| Days until ovulation | `sensor.cycle_tracker_days_until_ovulation` | Secondary |
| Next ovulation date | `sensor.cycle_tracker_next_ovulation_date` | Secondary |
| Start action | `cycle_tracker.log_start` | Sends today's local date |
| End action | `cycle_tracker.log_end` | Inline confirmation first |

## States to design

| State | What the user sees |
|---|---|
| No data ever logged | "Not tracked yet" plus a clear start action; no zeros |
| Active cycle | Day and phase prominent, prediction below |
| Predicted period due | Emphasis on days until period, without alarm styling |
| Entity unavailable | Per-row "not tracked", rest of the card still renders |
| Entity missing | Per-row "not tracked", no crash |
| Sheet not configured | A setup hint pointing at the integration configuration; no zeros |
| Service in flight | Both actions disabled, subtle progress state |
| End confirmation | End button changes label for five seconds |
| Service error | Message in a polite live region, values stay visible |

## Layout directions to explore

- **A. Stat card** — large cycle day and phase, prediction row, two buttons at
  the bottom. Simple, fits any dashboard.
- **B. Cycle arc** — a ring or bar showing progress through the cycle, with day
  and phase in the center and actions below. More expressive, more code and more
  accessibility risk.
- **C. Compact row** — one line: phase, day, next period, two icon buttons. Good
  for dense dashboards, poor for glanceability on a phone.

Direction A is the safe default; B is the one worth mocking if the user wants
personality. C is a variant of A for small screens, not a separate card.

## Constraints

- Home Assistant theme variables only; no hard-coded palette.
- Mobile-first, readable at 360 px wide; no horizontal scroll.
- Keyboard operable, visible focus, accessible names, polite live region.
- No external assets, fonts, or CDN; single ES module with no build step.
- English labels in the first version; localization is out of scope.
- The card reads entity states and calls existing services only; it never writes
  storage directly.

## Non-goals

- Visual card editor.
- Charts or history views.
- Flow-intensity input (parked as idea I-005).
- Logging for a past or future date.
- Editing or deleting recorded periods.

## Open questions

- Which number should dominate: cycle day or days until period?
- Does the user want a calm, neutral tone or something warmer and more personal?
- Is a ring/arc worth the extra complexity, or is a clean stat card enough?
- Should the card show statistics (average cycle length, confidence) at all?
- Does the user want the actions always visible, or only when relevant?

## Next step

The user dumps ideas; they get clustered into this brief; then two or three
layout variants are produced (text/static first, OpenDesign once Docker is
available); one is chosen and folded back into the change's `design.md` and
`spec.md`.
