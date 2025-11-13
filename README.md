# IRF Database - Irradiation Request Form Management System

A comprehensive Django-based web application for managing Irradiation Request Forms (IRFs) and Sample Irradiation Logs for the Missouri S&T Nuclear Reactor, based on SOP 702.

## Features

### User-Friendly Frontend
- **Home Dashboard**: Quick overview with statistics and recent activity
- **Search & Filter**: Powerful search by IRF number, sample description, or requester with filters for status, physical form, and year
- **Detail View with Tabs**:
  - Tab 1: Complete IRF details with all fields from SOP 702
  - Tab 2: Associated Sample Irradiation Logs
- **Responsive Design**: Bootstrap 5-based UI that works on all devices

### Django Admin Backend
- **Comprehensive Admin Interface**: Full CRUD operations for IRFs and logs
- **Inline Editing**: Add/edit sample logs directly from IRF admin page
- **Color-Coded Status Badges**: Visual indicators for draft, pending, approved, rejected, and archived IRFs
- **Organized Fieldsets**: Groups fields logically matching SOP 702 structure
- **Validation**: Automatic checks for within-limits irradiations

### Data Models Based on SOP 702

#### Irradiation Request Form (IRF)
Complete implementation of all fields:
- IRF identification and status tracking
- Sample information (description, physical form, encapsulation)
- Irradiation parameters (location, power, time, mass limits)
- Expected dose rate and reactivity worth
- Hazard analysis (reactivity, dose rate, equipment, other)
- Dual approval signatures (Director, Manager, SRO, or Health Physicist)

#### Sample Irradiation Log
Records each individual irradiation:
- Date, sample ID, experimenter
- Actual location and parameters used
- Time in/out and total time
- Measured dose rate and decay time
- Operator initials and notes
- Automatic calculation of fluence (kW-hrs)
- Validation against IRF limits

## Installation

### Prerequisites
- Python 3.11+
- pip

### Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Migrations** (already done)
   ```bash
   python manage.py migrate
   ```

3. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

4. **Access the Application**
   - Main Interface: http://localhost:8000/
   - Admin Panel: http://localhost:8000/admin/

## Login Credentials

**Admin User:**
- Username: `admin`
- Password: `admin123`

**IMPORTANT**: Change this password in production!

## Usage

### For Reactor Staff (Main Interface)

#### Searching for IRFs
1. Go to the home page
2. Use the search bar to find IRFs by number, sample description, or requester
3. Or click "All IRFs" to browse with filters (status, physical form, year)

#### Viewing IRF Details
1. Click on any IRF from the search results
2. **Details Tab**: View complete IRF information including:
   - Sample description and physical properties
   - Irradiation limits
   - Dose rate and reactivity calculations
   - Hazard analysis
   - Approval signatures
3. **Sample Logs Tab**: View all irradiations performed under this IRF

#### Creating New IRF
1. Click "New IRF" in the navigation
2. Fill in all required fields following SOP 702 guidelines
3. Save as draft or submit for review

#### Adding Sample Irradiation Logs
1. From IRF detail page, click "Add New Log" in the Logs tab
2. OR click "New Sample Log" in navigation
3. Fill in irradiation details (date, power, time, dose rate, etc.)
4. System automatically validates against IRF limits

### For Administrators (Admin Panel)

#### Bulk Data Entry
1. Go to http://localhost:8000/admin/
2. Login with admin credentials
3. Use "Irradiation Request Forms" for IRF management
4. Sample logs can be added inline when editing an IRF

#### Approving IRFs
1. Open IRF in admin
2. Scroll to "Review and Approval" section
3. Complete hazard analysis
4. Add two approver signatures with dates
5. Change status to "Approved"

## Sample Data

The system includes 5 sample IRFs demonstrating various scenarios:
- **24-001**: Gold foil samples (Approved, with 2 logs)
- **24-002**: Soil samples (Approved, with 1 log)
- **24-003**: Medical isotope production (Approved, with special restrictions)
- **24-004**: Silicon wafers (Pending review)
- **24-005**: Biological samples (Draft)

## Data Entry Tips for 30+ Years of Paper Files

### Recommended Workflow

1. **Start with Recent Years**: Enter IRFs from newest to oldest
2. **Use Status Field**: Mark historical IRFs as "Archived"
3. **Batch Entry**: Use admin interface for faster data entry
4. **Validation**: Double-check IRF numbers follow YY-### format
5. **Sample Logs**: Add logs after IRF is created (can be done later)

### IRF Numbering Convention
- Format: `YY-NNN` (e.g., 95-1, 95-2, 24-001)
- First two digits = year
- Dash separator
- Sequential number

### Optional Fields
Many fields are optional to accommodate incomplete historical records:
- Physical form "other" specification
- Dose rate calculation notes
- Reference IRF numbers
- Approval dates (if unknown)

## Database Structure

**Database File**: `db.sqlite3` (SQLite)

To backup your data:
```bash
cp db.sqlite3 db.sqlite3.backup
```

## Technical Details

### Project Structure
```
IRFDatabase/
├── irfdb/              # Django project settings
├── irradiation/        # Main app
│   ├── models.py       # Data models
│   ├── views.py        # Frontend views
│   ├── admin.py        # Admin configuration
│   ├── urls.py         # URL routing
│   └── templates/      # HTML templates
├── manage.py           # Django management script
└── db.sqlite3          # Database file
```

### Key Features Implemented
- Search with multiple filters
- Tabbed detail view (matching your requirements!)
- Color-coded status badges
- Inline sample log editing
- Automatic validation (limits, approvals)
- Responsive Bootstrap 5 design
- Pagination for large datasets

## Compliance with SOP 702

This system implements:
- ✅ Section C: Complete IRF form with all required fields
- ✅ Section D: Sample Irradiation Log with all tracking fields
- ✅ Two-signature approval requirement
- ✅ Hazard analysis (reactivity, dose rate, equipment, other)
- ✅ Limits validation (power, time, mass)
- ✅ Status tracking (draft → pending → approved)

## Future Enhancements (Not Implemented Yet)

Consider adding:
- PDF export of IRFs
- Dose rate calculations (DR=6CE rule)
- Reactivity worth calculations (SOP 306)
- Reports and statistics
- Email notifications for approvals
- Barcode/QR code generation for samples
- Import from CSV/Excel
- User roles and permissions
- Audit trail of changes

## Support

For questions about:
- **SOP 702**: Refer to the included PDF
- **Django**: https://docs.djangoproject.com/
- **Bootstrap**: https://getbootstrap.com/docs/

## License

Internal use for Missouri S&T MSTR facility.

---

**Revised By**: Claude Code Assistant
**Date**: November 13, 2025
**Based On**: SOP 702 - Revised August 9, 2016
