# template-file-management Specification

## Purpose
TBD - created by archiving change coverage-sector-template-management. Update Purpose after archive.
## Requirements
### Requirement: Admin can manage Word and Excel templates
The system SHALL allow Admin users to upload and manage template metadata for `word` and `excel` file types.

#### Scenario: Upload a new template version by drag-and-drop
- **WHEN** Admin drags a valid template file into upload area on Report Template page
- **THEN** system MUST create a new template version record

#### Scenario: Non-Admin tries to upload template by drag-and-drop
- **WHEN** SA or Analyst drags template file into upload area
- **THEN** system MUST reject the request

### Requirement: Template versioning must be retained
The system SHALL retain all historical template versions per `report_type` and `file_type`.

#### Scenario: Multiple versions exist
- **WHEN** Admin uploads templates repeatedly for the same `report_type` and `file_type`
- **THEN** system MUST keep each version as a distinct historical record

### Requirement: Only one active template is allowed per report_type and file_type
The system SHALL allow at most one active template version in the same template group.

#### Scenario: Activate one version
- **WHEN** Admin marks a specific version as active
- **THEN** system MUST ensure that version is active for that group

#### Scenario: Switch active version
- **WHEN** Admin activates a different version in the same group
- **THEN** system MUST deactivate the previous active version and keep only one active version

### Requirement: Report Template page SHALL support drag-and-drop with click-upload fallback
The system SHALL support drag-and-drop upload on Report Template page while preserving click-upload behavior.

#### Scenario: Drag-and-drop unavailable or not used
- **WHEN** Admin uploads via file picker instead of drag-and-drop
- **THEN** system MUST keep upload behavior and validation consistent with existing flow

