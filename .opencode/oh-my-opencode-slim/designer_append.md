## Project-Specific Designer Rules for ha-cycle-tracker

### Design Scope
1. **Lovelace Custom Card** (TypeScript/Lit) - Primary user interface
2. **Config Flow UI** (HA native) - Setup wizard
3. **Sensor/Calendar Presentation** - State display, icons, attributes
4. **Dashboard Integration** - Responsive layout, theming

### Lovelace Card Requirements (`custom_components/cycle_tracker/lovelace/`)

#### Visual Design
- **Phase Indicator**: Large, clear visual for current phase
  - Menstrual: Red accent, droplet icon
  - Follicular: Green accent, leaf icon
  - Ovulatory: Blue accent, egg icon
  - Luteal: Orange accent, moon icon
- **Days Until Next Period**: Prominent countdown (large number)
- **Cycle Day**: Subtle "Day X of Y" display
- **One-Tap Logging**: Two large buttons - "Start Period" / "End Period"
- **Quick Stats**: Average cycle length, typical period length (collapsible)

#### Interaction Design
- **Tap Targets**: Minimum 48x48dp (HA standard)
- **Feedback**: Ripple effect, haptic on mobile
- **Loading State**: Skeleton screen while prediction loads
- **Error State**: Inline banner with retry action
- **Empty State**: Friendly onboarding illustration + "Log first period" CTA

#### Responsive Behavior
- **Mobile (320-480px)**: Stacked layout, full-width buttons
- **Tablet (480-768px)**: Two-column, side-by-side buttons
- **Desktop (768px+)**: Compact card, optional sidebar layout
- **Panel Mode**: Full-width in HA panel view

#### Theming (CSS Custom Properties)
```css
:host {
  --cycle-tracker-primary: var(--primary-color);
  --cycle-tracker-menstrual: #e53935;
  --cycle-tracker-follicular: #43a047;
  --cycle-tracker-ovulatory: #1e88e5;
  --cycle-tracker-luteal: #fb8c00;
  --cycle-tracker-surface: var(--card-background-color);
  --cycle-tracker-text: var(--primary-text-color);
  --cycle-tracker-text-secondary: var(--secondary-text-color);
  --cycle-tracker-border: var(--divider-color);
}
```
- Respects HA light/dark mode automatically via CSS variables
- No hardcoded colors except phase accents (semantic, not decorative)

#### Accessibility (WCAG 2.1 AA)
- **Color Contrast**: Phase accents meet 4.5:1 on light/dark backgrounds
- **ARIA Labels**: All buttons, status regions
- **Keyboard Navigation**: Tab order logical, Enter/Space activates buttons
- **Screen Readers**: Live region for phase changes, countdown updates
- **Reduced Motion**: Respect `prefers-reduced-motion` for animations

#### Icons
- Use HA's `mdi:` icon set (built-in)
- Phase icons: `mdi:water`, `mdi:leaf`, `mdi:egg`, `mdi:moon-waxing-gibbous`
- Action icons: `mdi:play-circle`, `mdi:stop-circle`
- Size: 24px standard, 32px for primary phase indicator

### Config Flow UX
- **Step 1**: Basic info (avg cycle length, period length) - number selectors with helpers
- **Step 2**: Tracking preferences (symptoms, BBT, OPK, medications) - multi-select chips
- **Step 3**: Notifications (upcoming period, ovulation, fertile window) - toggle groups
- **Validation**: Inline, helpful messages ("Typical range: 21-35 days")
- **Progress**: Step indicator, back/next navigation

### Sensor/Calendar Presentation
- **Sensor Names**: `sensor.cycle_day`, `sensor.cycle_phase`, `sensor.next_period_date`
- **Icons**: Dynamic per phase (via `icon` property)
- **Attributes**: Rich data for automations (phase, days_until, uncertainty_window)
- **Calendar**: Native HA calendar entity, events for period days (past + predicted)

### Handoff to Implementers
- **Specs**: Detailed markdown in `specs/ui/` with states, breakpoints, tokens
- **Assets**: SVG icons exported from Figma (or use MDI)
- **Interactions**: Animation specs (150ms ease-out for transitions)
- **Copy**: Grounded, normal wording (orchestrator reviews copy)

### Review Checklist (per `verification-before-completion`)
- [ ] Responsive at 320px, 768px, 1024px
- [ ] Light/dark mode correct
- [ ] Keyboard navigable
- [ ] Screen reader tested (NVDA/VoiceOver)
- [ ] Color contrast passes (axe-core)
- [ ] HA theming variables used (no hardcoded colors except semantic)
- [ ] Loading/error/empty states implemented
- [ ] Copy reviewed by orchestrator