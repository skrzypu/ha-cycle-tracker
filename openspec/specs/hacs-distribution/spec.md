# hacs-distribution Specification

## Purpose

Defines how the integration is packaged, versioned, and distributed so it can be installed and updated through HACS as a custom repository while remaining outside the public HACS catalog.

## Requirements

### Requirement: HACS metadata at repository root

The repository SHALL provide a `hacs.json` file at its root containing at least the integration name and the minimum supported Home Assistant version, and SHALL NOT rely on a `hacs.json` inside the component directory.

#### Scenario: Root metadata present

- **WHEN** HACS inspects the repository root
- **THEN** a valid `hacs.json` containing a name is found

### Requirement: Valid integration manifest

The component SHALL provide a `manifest.json` in `custom_components/cycle_tracker/` whose `domain` matches the directory name and which declares name, version, documentation, issue tracker, code owners, config flow, and I/O class.

#### Scenario: Manifest validates

- **WHEN** the official hassfest validation runs against the component
- **THEN** it reports no missing or invalid manifest fields

### Requirement: Supported Home Assistant version

The integration SHALL declare a minimum supported Home Assistant version of 2026.1.0 and SHALL run on that version without errors.

#### Scenario: Minimum version declared

- **WHEN** the manifest and HACS metadata are inspected
- **THEN** both declare a minimum Home Assistant version of 2026.1.0

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

### Requirement: Brand assets

The repository SHALL provide brand image assets for the integration at a resolution sufficient for display in Home Assistant.

#### Scenario: Brand icon present

- **WHEN** the repository is inspected
- **THEN** a brand icon of at least 256 by 256 pixels exists

### Requirement: Versioned releases

The repository SHALL publish GitHub releases whose version tag matches the `version` declared in `manifest.json`.

#### Scenario: Release matches manifest

- **WHEN** a release is published
- **THEN** its tag corresponds to the manifest version

### Requirement: Continuous validation

Continuous integration SHALL run the official HACS validation action for the integration category and the official hassfest validation, and SHALL fail when either reports an error.

#### Scenario: Validation runs in CI

- **WHEN** a change is pushed or a pull request is opened
- **THEN** both the HACS and hassfest validation jobs execute

### Requirement: Custom-repository-only distribution

The integration SHALL be distributed only as a HACS custom repository and SHALL NOT be submitted to the HACS default catalog, so that it is not listed or searchable within HACS.

#### Scenario: No default-catalog submission

- **WHEN** distribution is prepared
- **THEN** no pull request to the HACS default catalog is created
