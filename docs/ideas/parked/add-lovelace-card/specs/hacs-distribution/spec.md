# Spec Delta

## Purpose

Keeps the distribution contract accurate now that the integration ships a
frontend asset: one HACS Integration entry must deliver the card together with
the Python component, at the same version.

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
