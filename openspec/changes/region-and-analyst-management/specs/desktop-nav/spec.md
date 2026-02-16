# Desktop Navigation - Region and Analyst Management

## ADDED Requirements

### Requirement: Desktop displays admin-only management cards
The system SHALL display Regions and Analyst Info management cards on Desktop for Admin users only.

#### Scenario: Admin sees management cards
- **WHEN** Admin user accesses Desktop page
- **THEN** system displays Regions card
- **AND** system displays Analyst Info card
- **AND** both cards are visible in Data Management section

#### Scenario: Non-admin cannot see management cards
- **WHEN** non-Admin user (SA or Analyst) accesses Desktop page
- **THEN** system does not display Regions card
- **AND** system does not display Analyst Info card

### Requirement: Management cards open in new tab
The system SHALL open management pages in new tab when clicked, following Desktop-as-Launcher contract.

#### Scenario: Click Regions card
- **WHEN** Admin user clicks Regions card
- **THEN** system opens `/regions` page in new tab
- **AND** Desktop page remains open in original tab

#### Scenario: Click Analyst Info card
- **WHEN** Admin user clicks Analyst Info card
- **THEN** system opens `/analyst-info` page in new tab
- **AND** Desktop page remains open in original tab
