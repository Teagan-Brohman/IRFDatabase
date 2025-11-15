# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IRF Database is a Django-based web application for managing Irradiation Request Forms (IRFs) and Sample Irradiation Logs for the Missouri S&T Nuclear Reactor. The system implements Missouri S&T SOP 702 (Standard Operating Procedure 702) for tracking nuclear reactor sample irradiations spanning 30+ years of historical data.

## Python Version Compatibility

**IMPORTANT:** This project requires **Python 3.8-3.9** for PyNE compatibility.

- **Python Version:** 3.8.x - 3.9.x (required for PyNE)
- **Django Version:** 3.2 LTS (supports Python 3.6-3.10)
- **PyNE Version:** 0.7.5 (last updated 2021, works best with Python 3.8-3.9)

### Why Python 3.8-3.9?

PyNE (Python for Nuclear Engineering) is a critical dependency for neutron activation analysis calculations. PyNE was last updated in 2021 (v0.7.5) and works most reliably with Python 3.8-3.9. While PyNE may work with newer Python versions, compatibility is not guaranteed.

**Key Compatibility Notes:**
- Django 5.0+ requires Python 3.10+, so we use Django 3.2 LTS for Python 3.8-3.9 support
- Scientific packages (NumPy, SciPy) are pinned to versions compatible with Python 3.8-3.9
- Use conda for installing PyNE: `conda install -c conda-forge pyne`

### Setting Up the Environment

**Using Conda (Recommended):**
```bash
# Create environment from environment.yml (includes Python 3.8-3.9)
conda env create -f environment.yml

# Activate environment
conda activate irfdatabase
```

**Using pip with existing Python 3.8-3.9:**
```bash
# Ensure you're using Python 3.8 or 3.9
python --version

# Install dependencies
pip install -r requirements.txt

# Install PyNE via conda (recommended even in pip environments)
conda install -c conda-forge pyne
```

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

**Sample**: Tracks individual samples with composition and irradiation history
- Supports both base samples and combo samples (assemblies of multiple samples)
- Links to `SampleIrradiationLog` entries for complete irradiation history
- `SampleComposition` model stores elemental/isotopic composition
- Used for neutron activation analysis calculations
- Key fields:
  - `is_combo`: Boolean flag for combo samples
  - `material_type`: Description of material
  - `mass`/`mass_unit`: Sample mass with units (g, mg, kg)

**FluxConfiguration**: Stores neutron flux data for each irradiation location
- Thermal flux (E < 0.5 eV), Fast flux (E > 0.1 MeV), Intermediate flux (optional)
- Reference power for flux measurements (default 200 kW)
- `get_scaled_fluxes(power_kw)`: Linearly scales flux to different power levels
- **Scientific Notation Input**: Admin form provides mantissa/exponent fields
  - Enter "2.5" and "12" instead of "2500000000000.00"
  - Required for thermal and fast flux, optional for intermediate
  - Automatic conversion on save

### View Architecture (irradiation/views.py)

The application uses Django's class-based views:
- `IRFListView`: Search/filter interface with pagination
- `IRFDetailView`: Tabbed detail view (IRF Details + Sample Logs)
- `IRFCreateView`/`IRFUpdateView`: Form handling for IRFs
- `IRFUpdateView` handles both amendments and fixes:
  - Amendment: Creates new version (new pk, increments version_number)
  - Fix: Updates in-place without versioning
- `SampleLogCreateView`: Add irradiation logs
- `SampleDetailView`: Displays sample with composition and activation results
- `SampleCreateView`/`SampleUpdateView`: Sample management
- `ComboSampleCreateView`: Create combo samples with component selection

**API Endpoints**:
- `irf_autocomplete`: JSON autocomplete for IRF selection
- `sample_autocomplete`: JSON autocomplete for sample selection
- `calculate_sample_isotopics`: Neutron activation analysis calculation
  - Query params: `use_multigroup`, `min_fraction`, `use_cache`
  - Returns isotopic inventory, activities, dose rates
  - Includes warning for skipped irradiations due to missing flux configs

### URL Structure (irradiation/urls.py)
- `/` - Home dashboard
- `/irfs/` - IRF list/search
- `/irf/<pk>/` - IRF detail (with tabs)
- `/irf/new/` - Create IRF
- `/irf/<pk>/edit/` - Edit IRF
- `/sample-log/new/` - Create sample log
- `/sample/<pk>/` - Sample detail with activation analysis
- `/sample/new/` - Create base sample
- `/sample/<pk>/edit/` - Edit sample
- `/sample/combo/new/` - Create combo sample
- `/api/irf-autocomplete/` - JSON endpoint for IRF autocomplete
- `/api/sample-autocomplete/` - JSON endpoint for sample autocomplete
- `/api/sample/<pk>/calculate-isotopics/` - Neutron activation calculation API

### Templates

Key templates in `irradiation/templates/irradiation/`:
- `base.html`: Bootstrap 5 layout with navigation
- `irf_form.html`: Complex form with JavaScript for dynamic field visibility
  - Contains extensive JavaScript for conditional field display
  - Uses Django template syntax: `{% if %}...{% endif %}` NOT Python ternary operators
- `irf_detail.html`: Tabbed interface for IRF details and logs
- `irf_list.html`: Search/filter interface with pagination
- `sample_detail.html`: Sample view with activation analysis results
  - Displays sample composition and irradiation history
  - "Calculate Isotopics" button triggers AJAX request to API
  - Shows warning banner for skipped irradiations (missing flux configs)
  - Interactive isotope table with activity filtering
  - Plotly.js graphs for decay curves
  - Unit toggle (Bq/Ci) for activities

**CRITICAL**: When editing templates, always use Django template syntax:
- Correct: `{% if object %}true{% else %}false{% endif %}`
- Wrong: `{{ 'true' if object else 'false' }}`

### Admin Interface (irradiation/admin.py)

Custom admin with:
- Inline editing of SampleIrradiationLogs within IRF
- Organized fieldsets matching SOP 702 structure
- Color-coded status badges
- Advanced filtering and search
- **FluxConfigurationAdmin**: Custom form with scientific notation input
  - `FluxConfigurationAdminForm` with mantissa/exponent fields
  - Automatic pre-population when editing existing values
  - `clean()` method calculates full decimal from M×10^E
  - Readonly display of calculated flux values
- **SampleAdmin**: Inline composition editing
  - Shows `SampleComponentInline` for combo samples
  - `SampleCompositionInline` for elemental composition

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

### Neutron Activation Analysis (irradiation/activation.py)

**NeutronActivationCalculator**: Calculates isotopic inventory and activities
- Processes complete irradiation history for a sample
- Accounts for:
  - Neutron activation during irradiation (φ × σ × t)
  - Radioactive decay between irradiations
  - Sequential chaining of multiple irradiations
  - Multi-group neutron spectrum (thermal/fast/intermediate)

**Key Features**:
- **PyNE Integration**: Uses PyNE nuclear data library for cross-sections when available
- **Spectrum-averaged cross-sections**: Flux-weighted average across energy groups
- **Decay chains**: Uses radioactivedecay library for proper decay calculations
- **Fallback mode**: Simplified cross-section database for common elements (Au, Co, etc.)
- **Caching**: SHA256 hash-based caching to avoid redundant calculations
  - Hash includes sample composition + all irradiation parameters
  - Cached results stored in `ActivationResult` model

**Warning System for Missing Flux Configurations**:
- Tracks irradiations skipped due to missing flux data
- Returns list of skipped irradiations with details (date, location, power, time)
- Frontend displays prominent warning banner
- Shows "Results based on X of Y irradiations"
- Guides user to configure flux in Admin → Flux configurations

**Dependencies**:
- `radioactivedecay`: Decay chain calculations
- `PyNE` (optional): Multi-group cross-sections from nuclear data libraries
- `numpy`, `scipy`: Numerical calculations

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

- **Framework**: Django 3.2 LTS (for Python 3.8-3.9 compatibility)
- **Python**: 3.8.x - 3.9.x (required for PyNE)
- **Database**: SQLite (db.sqlite3)
- **Frontend**: Bootstrap 5 with custom JavaScript
- **Visualization**: Plotly.js for interactive decay curves
- **File Uploads**: Pillow for image handling
- **Admin Tools**: django-import-export for bulk operations
- **Scientific Computing**:
  - `numpy` (≥1.20.0, <1.27.0): Numerical calculations (Python 3.8+ compatible)
  - `scipy` (≥1.5.0, <1.12.0): Advanced numerical methods (Python 3.8+ compatible)
  - `radioactivedecay` (≥0.4.0): Decay chain calculations
  - `PyNE` (v0.7.5): Multi-group neutron cross-sections and nuclear data
    - **Required for neutron activation analysis**
    - Best installed via conda: `conda install -c conda-forge pyne`
    - pip installation requires Fortran compilers
    - Works best with Python 3.8-3.9

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

### Flux Configuration and Scientific Notation
**Admin Form Design** (irradiation/admin.py:362-525):
- `FluxConfigurationAdminForm` provides user-friendly scientific notation input
- Mantissa and exponent fields for each flux type (thermal, fast, intermediate)
- Thermal and fast flux are **required** (database constraint)
- Intermediate flux is **optional**
- `__init__` method pre-populates fields when editing:
  - Converts stored decimal (e.g., 2500000000000.00) to mantissa=2.5, exponent=12
  - Uses `_decimal_to_scientific()` helper with log10 calculation
- `clean()` method converts user input to decimal:
  - Calculates: mantissa × 10^exponent
  - Stores full decimal value in database
- Actual flux fields shown as readonly for verification
- **IMPORTANT**: If mantissa/exponent not provided, database will fail with NOT NULL constraint
  - This is by design to ensure required flux values are always set

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

### Neutron Activation Analysis Workflow
1. **Configure Flux Values** (Admin → Flux configurations):
   - Select irradiation location (bare rabbit, cad rabbit, beam port, thermal column, other)
   - Enter thermal flux: mantissa (e.g., 2.5) and exponent (e.g., 12) for 2.5×10¹² n/cm²/s
   - Enter fast flux: mantissa and exponent
   - Optionally enter intermediate flux
   - System calculates full decimal value automatically
2. **Create Sample** with composition:
   - Define elemental/isotopic composition via `SampleComposition` inline
   - For combo samples, link component samples
3. **Link Irradiations**:
   - Sample irradiation logs reference the sample
   - Complete irradiation history tracked (location, power, time, date)
4. **Calculate Isotopics**:
   - Navigate to sample detail page
   - Click "Calculate Isotopics" button
   - System processes irradiation history sequentially
   - If flux config missing for any location, warning displayed
   - Results show:
     - Total activity (Bq/Ci with toggle)
     - Estimated dose rate at 1 foot
     - Isotope table with activities, half-lives, fractions
     - Interactive decay curves (Plotly)
5. **Results Caching**:
   - Hash calculated from composition + irradiation history
   - Cached in `ActivationResult` model
   - Subsequent requests use cache if irradiation history unchanged

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
