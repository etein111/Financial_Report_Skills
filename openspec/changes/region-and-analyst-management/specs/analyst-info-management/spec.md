# Analyst Info Management

## ADDED Requirements

### Requirement: Admin can view analyst list
The system SHALL allow Admin users to view a list of all analysts with full name, Chinese name, email, region, and status.

#### Scenario: Admin views analyst list
- **WHEN** Admin user accesses `/analyst-info` page
- **THEN** system displays list of all analysts showing full_name, chinese_name, email, region, is_active
- **AND** analysts are sorted by created_at DESC by default

#### Scenario: Non-admin cannot access analyst info page
- **WHEN** non-Admin user attempts to access `/analyst-info` page
- **THEN** system redirects user to `/403` page

### Requirement: Admin can create analyst
The system SHALL allow Admin users to create new analyst records.

#### Scenario: Successful analyst creation
- **WHEN** Admin submits analyst creation form with valid full_name, email, and region
- **THEN** system creates new analyst record
- **AND** system displays success message
- **AND** analyst list refreshes to show new analyst

#### Scenario: Analyst creation requires mandatory fields
- **WHEN** Admin attempts to create analyst without full_name, email, or region
- **THEN** system displays field-level errors for missing required fields
- **AND** analyst is not created

#### Scenario: Analyst email uniqueness validation
- **WHEN** Admin attempts to create analyst with duplicate email
- **THEN** system displays field-level error indicating email already exists
- **AND** analyst is not created

### Requirement: Admin can edit analyst
The system SHALL allow Admin users to modify all analyst fields.

#### Scenario: Successful analyst update
- **WHEN** Admin submits analyst edit form with modified data
- **THEN** system updates analyst record
- **AND** system displays success message
- **AND** analyst list refreshes to show updated analyst

#### Scenario: Edit analyst email uniqueness validation
- **WHEN** Admin attempts to update analyst with email that conflicts with existing analyst
- **THEN** system displays field-level error for email field
- **AND** analyst is not updated

### Requirement: Admin can delete analyst
The system SHALL allow Admin users to delete analyst records with confirmation.

#### Scenario: Successful analyst deletion
- **WHEN** Admin confirms deletion of an analyst
- **THEN** system deletes analyst record
- **AND** system displays success message
- **AND** analyst list refreshes

### Requirement: Analyst list supports pagination
The system SHALL paginate analyst list when exceeding 15 items.

#### Scenario: Analyst list pagination
- **WHEN** analyst count exceeds 15
- **THEN** system displays 15 analysts per page
- **AND** system shows pagination controls

#### Scenario: Fixed page size
- **WHEN** viewing analyst list
- **THEN** page size is fixed at 15 items
- **AND** user cannot change page size

### Requirement: Analyst list supports search
The system SHALL allow Admin to search analysts by full name, Chinese name, or email.

#### Scenario: Search by full name
- **WHEN** Admin enters search query for full name
- **THEN** system filters analysts showing only those with full_name matching query (fuzzy match)

#### Scenario: Search by Chinese name
- **WHEN** Admin enters search query for Chinese name
- **THEN** system filters analysts showing only those with chinese_name matching query (fuzzy match)

#### Scenario: Search by email
- **WHEN** Admin enters search query for email
- **THEN** system filters analysts showing only those with email matching query (fuzzy match)

### Requirement: Analyst info decoupled from auth users
The system SHALL maintain analyst information independently from authentication users.

#### Scenario: Creating analyst does not create auth user
- **WHEN** Admin creates analyst record
- **THEN** system does not automatically create authentication user account

#### Scenario: Deleting analyst does not delete auth user
- **WHEN** Admin deletes analyst record
- **THEN** system does not delete associated authentication user account (if any)
