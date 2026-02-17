## ADDED Requirements

### Requirement: System SHALL allow SA and Admin to review submitted reports
The system SHALL allow SA and Admin to access review workspace and process submitted reports.

#### Scenario: SA opens review workspace
- **WHEN** SA accesses report review page
- **THEN** system MUST allow access
- **AND** system MUST list submitted reports

#### Scenario: Analyst opens review workspace
- **WHEN** Analyst accesses report review page
- **THEN** system MUST deny access

### Requirement: System SHALL support approve, reject, and reopen actions
The system SHALL allow SA and Admin to approve, reject, and reopen reports according to state machine.

#### Scenario: Approve submitted report
- **WHEN** SA or Admin approves a report in `submitted`
- **THEN** system MUST transition status to `published`

#### Scenario: Reject submitted report
- **WHEN** SA or Admin rejects a report in `submitted` with reason
- **THEN** system MUST transition status to `rejected`

#### Scenario: Reopen rejected report
- **WHEN** SA or Admin reopens a report in `rejected`
- **THEN** system MUST transition status to `draft`

### Requirement: System SHALL provide file download only in review detail
The system SHALL provide report and model file download in review detail without online word preview.

#### Scenario: Review detail with files
- **WHEN** SA or Admin opens review detail for a report with files
- **THEN** system MUST provide download actions for available files

#### Scenario: Review detail without files
- **WHEN** SA or Admin opens review detail for a report without files
- **THEN** system MUST show no-file state and MUST NOT render preview component
