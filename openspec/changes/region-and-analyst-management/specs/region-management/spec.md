# Region Management

## ADDED Requirements

### Requirement: Admin can view region list
The system SHALL allow Admin users to view a list of all regions with name, code, and creation date.

#### Scenario: Admin views region list
- **WHEN** Admin user accesses `/regions` page
- **THEN** system displays list of all regions showing name, code, and created_at
- **AND** regions are sorted by created_at DESC by default

#### Scenario: Non-admin cannot access regions page
- **WHEN** non-Admin user attempts to access `/regions` page
- **THEN** system redirects user to `/403` page

### Requirement: Admin can create region
The system SHALL allow Admin users to create new regions with name and code fields.

#### Scenario: Successful region creation
- **WHEN** Admin submits region creation form with valid name and code
- **THEN** system creates new region record
- **AND** system displays success message
- **AND** region list refreshes to show new region

#### Scenario: Region name uniqueness validation
- **WHEN** Admin attempts to create region with duplicate name
- **THEN** system displays field-level error indicating name already exists
- **AND** region is not created

#### Scenario: Region code uniqueness validation
- **WHEN** Admin attempts to create region with duplicate code
- **THEN** system displays field-level error indicating code already exists
- **AND** region is not created

### Requirement: Admin can edit region
The system SHALL allow Admin users to modify existing region name and code.

#### Scenario: Successful region update
- **WHEN** Admin submits region edit form with modified name or code
- **THEN** system updates region record
- **AND** system displays success message
- **AND** region list refreshes to show updated region

#### Scenario: Edit region uniqueness validation
- **WHEN** Admin attempts to update region with name or code that conflicts with existing region
- **THEN** system displays field-level error for the conflicting field
- **AND** region is not updated

### Requirement: Admin can delete region
The system SHALL allow Admin users to delete regions with confirmation.

#### Scenario: Successful region deletion
- **WHEN** Admin confirms deletion of a region
- **THEN** system deletes region record
- **AND** system displays success message
- **AND** region list refreshes

#### Scenario: Region deletion cascades to analysts
- **WHEN** Admin deletes a region referenced by one or more analysts
- **THEN** system deletes region record
- **AND** system sets region_id to NULL for all analysts referencing deleted region (ON DELETE SET NULL)

### Requirement: Region list supports pagination
The system SHALL paginate region list when exceeding 15 items.

#### Scenario: Region list pagination
- **WHEN** region count exceeds 15
- **THEN** system displays 15 regions per page
- **AND** system shows pagination controls

#### Scenario: Fixed page size
- **WHEN** viewing region list
- **THEN** page size is fixed at 15 items
- **AND** user cannot change page size

### Requirement: Region list supports search
The system SHALL allow Admin to search regions by name or code.

#### Scenario: Search by region name
- **WHEN** Admin enters search query for region name
- **THEN** system filters regions showing only those with name matching query (fuzzy match)

#### Scenario: Search by region code
- **WHEN** Admin enters search query for region code
- **THEN** system filters regions showing only those with code matching query (fuzzy match)

### Requirement: System provides preset regions
The system SHALL include preset region data: China, Hong Kong, Japan, Taiwan, Korea, India, Macau, US.

#### Scenario: Preset regions are available
- **WHEN** system is initialized
- **THEN** preset regions exist in database
