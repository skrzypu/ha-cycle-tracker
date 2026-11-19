# Spec Delta

## MODIFIED Requirements

### Requirement: Config flow UI strings

The integration SHALL provide user-facing strings for every config-flow step
and field so that the config flow renders fully in the Home Assistant UI, SHALL
provide a Polish translation in `translations/pl.json` covering every step,
field, error, selector option, and repair issue, and SHALL keep English as the
fallback language with copy that clearly describes each step, especially the
Google Sheets step.

#### Scenario: Strings provided

- **WHEN** the config flow is opened in Home Assistant
- **THEN** every step and field shows a translated label rather than a raw key

#### Scenario: Polish translation provided

- **WHEN** the config flow is opened with Polish as the Home Assistant language
- **THEN** every step and field shows Polish text, with no raw key and no
  English fallback text

#### Scenario: English fallback remains

- **WHEN** the config flow is opened in English or an unsupported language
- **THEN** the English copy renders with clear instructions for the Google
  Sheets step

## ADDED Requirements

### Requirement: Bundled frontend asset

The repository SHALL ship the Lovelace card inside the integration directory and
SHALL deliver it through the same HACS Integration entry and the same release
version as the Python component, without requiring a separate HACS Dashboard
entry or a separate package.

#### Scenario: Single entry installs both parts

- **WHEN** a user installs or updates the repository through HACS as an
  Integration
- **THEN** the card asset is present under the integration directory at the same
  version as the component

#### Scenario: Release version covers the card

- **WHEN** a GitHub release is published
- **THEN** its tag matches the manifest version and the served card URL carries
  that same version

#### Scenario: No duplicate catalog entry

- **WHEN** distribution metadata is prepared
- **THEN** the repository declares only the integration category and no separate
  Dashboard repository or entry
