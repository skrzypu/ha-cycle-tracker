# Spec Delta

## Purpose

Defines how the integration is packaged, versioned, and distributed so it can be installed and updated through HACS as a custom repository while remaining outside the public HACS catalog.

## ADDED Requirements

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
The integration SHALL provide user-facing strings for every config-flow step and field so that the config flow renders fully in the Home Assistant UI.

#### Scenario: Strings provided
- **WHEN** the config flow is opened in Home Assistant
- **THEN** every step and field shows a translated label rather than a raw key

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
