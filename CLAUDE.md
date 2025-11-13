# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IRF Database is a Django-based web application for managing Irradiation Request Forms (IRFs) and Sample Irradiation Logs for the Missouri S&T Nuclear Reactor. The system implements Missouri S&T SOP 702 (Standard Operating Procedure 702) for tracking nuclear reactor sample irradiations spanning 30+ years of historical data.

## Development Commands

### Running the Development Server
```bash
python manage.py runserver
```
Access at http://127.0.0.1:8000/

### Database Operations
```bash
# Apply migrations
python manage.py migrate

# Create new migrations after model changes
python manage.py makemigrations

# Create superuser
python manage.py createsuperuser
```

### Data Management
```bash
# Backup database
cp db.sqlite3 db.sqlite3.backup

# Load sample data (if script exists)
python create_sample_data.py
```

### Accessing the Application
- Main Interface: http://localhost:8000/
- Admin Panel: http://localhost:8000/admin/ (credentials: admin/admin123)

## Architecture

### Core Data Models (irradiation/models.py)

**IrradiationRequestForm**: The primary model representing an IRF
- Implements all fields from SOP 702 Section C
- Supports version tracking and amendments through `parent_version` foreign key
- Version history is tracked via recursive parent-child relationships
- Key methods:
  - `get_version_history()`: Returns all versions in chronological order
  - `is_latest_version()`: Checks if this is the most recent version
  - `has_amendments()`: Checks for child versions
- Status workflow: draft → pending_review → approved/rejected → archived

**SampleIrradiationLog**: Records individual irradiations
- Links to parent IRF via ForeignKey (`related_name='irradiation_logs'`)
- Implements SOP 702 Section D fields
- Automatically validates against IRF limits via `within_limits()` method
- Calculates neutron fluence (kW-hrs) via `fluence()` method

### View Architecture (irradiation/views.py)

The application uses Django's class-based views:
- `IRFListView`: Search/filter interface with pagination
- `IRFDetailView`: Tabbed detail view (IRF Details + Sample Logs)
- `IRFCreateView`/`IRFUpdateView`: Form handling for IRFs
- `IRFUpdateView` handles both amendments and fixes:
  - Amendment: Creates new version (new pk, increments version_number)
  - Fix: Updates in-place without versioning
- `SampleLogCreateView`: Add irradiation logs

### URL Structure (irradiation/urls.py)
- `/` - Home dashboard
- `/irfs/` - IRF list/search
- `/irf/<pk>/` - IRF detail (with tabs)
- `/irf/new/` - Create IRF
- `/irf/<pk>/edit/` - Edit IRF
- `/sample-log/new/` - Create sample log
- `/api/irf-autocomplete/` - JSON endpoint for autocomplete

### Templates

Key templates in `irradiation/templates/irradiation/`:
- `base.html`: Bootstrap 5 layout with navigation
- `irf_form.html`: Complex form with JavaScript for dynamic field visibility
  - Contains extensive JavaScript for conditional field display
  - Uses Django template syntax: `{% if %}...{% endif %}` NOT Python ternary operators
- `irf_detail.html`: Tabbed interface for IRF details and logs
- `irf_list.html`: Search/filter interface with pagination

**CRITICAL**: When editing templates, always use Django template syntax:
- Correct: `{% if object %}true{% else %}false{% endif %}`
- Wrong: `{{ 'true' if object else 'false' }}`

### Admin Interface (irradiation/admin.py)

Custom admin with:
- Inline editing of SampleIrradiationLogs within IRF
- Organized fieldsets matching SOP 702 structure
- Color-coded status badges
- Advanced filtering and search

## Key Business Logic

### Version Control System
IRFs support amendments via a parent-child relationship:
- Original IRF: `version_number=1`, `parent_version=None`
- Amendment: New object with incremented `version_number`, `parent_version` pointing to previous version
- Amendments create a tree structure that can be traversed
- Always check `is_latest_version()` when displaying IRFs

### Two-Signature Approval
SOP 702 requires two approvals from:
- Director, Manager, SRO, or Health Physicist
- Both `approver1_date` and `approver2_date` must be set
- Check via `is_approved()` method

### Validation Rules
- Sample logs must stay within IRF limits (power, time, mass)
- Total reactivity worth across all experiments limited to 1.2% Δk/k
- Reactivity calculations may reference SOP 306
- Dose rate calculations may use "6CE rule"

### IRF Number Convention
Format: `YY-NNN` (e.g., `95-1`, `24-001`)
- First two digits: year
- Sequential number after dash
- Used for historical data spanning 30+ years

## Technology Stack

- **Framework**: Django 5.0
- **Database**: SQLite (db.sqlite3)
- **Frontend**: Bootstrap 5 with custom JavaScript
- **File Uploads**: Pillow for image handling
- **Admin Tools**: django-import-export for bulk operations

## Special Considerations

### SOP 702 Compliance
The system must maintain compliance with Missouri S&T Nuclear Reactor SOP 702:
- All required fields from Section C (IRF)
- All required fields from Section D (Sample Logs)
- Two-signature approval workflow
- Hazard analysis for reactivity, dose rate, equipment, and other concerns

### Conditional Field Display
The IRF form (`irf_form.html`) has extensive JavaScript for showing/hiding fields based on selections:
- Physical form "other" → show specification field
- Dose rate basis "calculations" → show calculation notes
- Reactivity basis "sop306" → show SOP 306 file upload
- Hazard analysis "other" → show notes fields

### Historical Data Entry
The system is designed to accommodate incomplete historical records:
- Many fields are optional to handle 30+ years of paper forms
- Status can be set to "archived" for historical IRFs
- Reference IRF numbers link related experiments

## Common Workflows

### Creating an Amendment
1. User clicks "Edit" on existing IRF
2. In IRFUpdateView, checks `change_type` from POST data
3. If `change_type='amendment'`:
   - Clones IRF with new pk
   - Sets `parent_version` to old IRF
   - Increments `version_number`
   - Saves `change_notes`
4. If `change_type='fix'`:
   - Updates existing IRF in-place

### Adding Sample Logs
1. Can be added via admin (inline) or frontend form
2. Automatically linked to parent IRF
3. Validation checks limits on save
4. Fluence auto-calculated from power × time

### Search and Filtering
IRFListView supports:
- Text search: IRF number, sample description, requester name
- Filters: status, physical form, year (parsed from IRF number)
- Pagination (25 per page)
- Results annotated with log count

## Database Schema Notes

- SQLite database location: `db.sqlite3` (root directory)
- Migrations in `irradiation/migrations/`
- Important migrations:
  - `0001_initial.py`: Creates base models
  - `0002_*`: Adds unit fields for measurements
  - `0003_*`: Adds version tracking fields

## Admin Credentials

Default superuser (MUST be changed in production):
- Username: `admin`
- Password: `admin123`
