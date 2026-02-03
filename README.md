# MIT-WPU Vyas Smart-Room Maintenance Tracker

A Flask-based web application for the Vyas Building at MIT-WPU featuring an interactive visual floor map for room selection and maintenance tracking.

## Features

- **Interactive Visual Floor Map** - Click rooms on a visual map instead of dropdowns
- **Vyas Building Specific** - 8 floors (Ground to 7th) with accurate room layouts
- **4th Floor Demo** - Detailed floor plan matching the actual building layout
- **QR Code Support** - Generate QR codes for quick room access
- **Real-time Status Map** - Admin view showing rooms with issues highlighted in red

## Tech Stack

- **Backend**: Flask 3.0+, Flask-SQLAlchemy, Werkzeug
- **Database**: SQLite (development)
- **Frontend**: Bootstrap 5, Interactive CSS Grid Map, Custom CSS
- **Tools**: Pillow, qrcode

## MIT-WPU Brand Colors

- Primary Blue: `#0b4d8c`
- Accent Red: `#c8102e`
- Lab Teal: `#20c997`

## Installation

### 1. Navigate to Project Directory

```bash
cd mitwpu_vyas_tracker
```

### 2. Create Virtual Environment (Optional)

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize Database with Vyas Building Data

```bash
python scripts/init_data.py
```

This creates:
- **Vyas Building** with 8 floors (Ground to 7th)
- **4th Floor** with detailed layout (VY401-VY429) matching the floor plan
- **Other Floors** with generic rooms
- **Assets** for each room (projectors, ACs, lights, etc.)

### 5. Run the Application

```bash
python run.py
```

The server will start at `http://localhost:5000`

## Application URLs

| Endpoint | Description |
|----------|-------------|
| `/` | Landing page with floor guide |
| `/report` | Student portal with interactive floor map |
| `/report?room=VY404` | Auto-select room VY404 via QR code |
| `/admin/login` | Admin login page |
| `/admin/` | Admin dashboard with tickets and statistics |
| `/admin/map` | Live status map of all floors |

## Admin Credentials

- **Username**: `admin`
- **Password**: `mitwpu123`

## Using the Interactive Map

### Student Portal

1. **Select Floor** - Choose a floor from the dropdown
2. **Click Room** - Tap on your room in the visual floor map
3. **Fill Form** - Enter your details and issue description
4. **Submit** - Click submit to create a ticket

### Room Colors

| Color | Room Type |
|-------|-----------|
| Dark Blue | Classroom |
| Teal/Green | Lab |
| Red | Washroom |
| Yellow Border | Selected Room |
| Pulsing Red | Room with Issues |

## QR Code Generation

Generate QR codes that link directly to the report page for each room:

```bash
# Generate QR codes for all rooms
python scripts/generate_qr.py --all

# Generate for 4th floor only
python scripts/generate_qr.py --floor 4

# Generate for a specific room
python scripts/generate_qr.py --room VY404

# Custom host/port
python scripts/generate_qr.py --all --host 192.168.1.100 --port 8080
```

QR codes are saved to the `qr_codes/` directory.

## Testing with curl

### Submit a Ticket

```bash
curl -X POST http://localhost:5000/report \
  -F "reporter_name=John Doe" \
  -F "prn=12345678" \
  -F "reporter_email=john.doe@mitwpu.edu.in" \
  -F "room_id=5" \
  -F "issue_type=electrical" \
  -F "description=Light not working in VY404"
```

### Get Rooms for Floor

```bash
curl http://localhost:5000/api/rooms/floor/5
```

### Get Room by Number

```bash
curl http://localhost:5000/api/room/VY404
```

### Get Assets for Room

```bash
curl http://localhost:5000/api/assets/5
```

## Project Structure

```
mitwpu_vyas_tracker/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models.py            # SQLAlchemy models
│   ├── routes.py            # Main routes (student portal, API)
│   ├── admin_routes.py      # Admin routes
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html       # Landing page
│   │   ├── report.html      # Student portal with map
│   │   ├── login.html       # Admin login
│   │   ├── admin.html       # Dashboard
│   │   └── status_map.html  # Live status map
│   └── static/
│       ├── css/style.css    # MIT colors + Map styles
│       ├── js/map.js        # Map interaction logic
│       └── uploads/         # Ticket images
├── scripts/
│   ├── init_data.py         # Vyas building data
│   └── generate_qr.py       # QR code generator
├── qr_codes/                # Generated QR codes
├── run.py                   # Entry point
├── requirements.txt
└── README.md
```

## Database Schema

### Building
- `id` (PK)
- `name` - 'Vyas'
- `description`

### Floor
- `id` (PK)
- `building_id` (FK)
- `level` - 0-7
- `name` - e.g., '4th Floor'

### Room
- `id` (PK)
- `floor_id` (FK)
- `number` - e.g., 'VY404'
- `name` - e.g., 'Classroom 404'
- `room_type` - class/lab/washroom/storage/other
- `map_coords` - Optional positioning data

### Asset
- `id` (PK)
- `room_id` (FK)
- `name` - e.g., 'Projector'
- `asset_type` - projector/ac/light/etc.
- `status` - working/broken/maintenance

### Ticket
- `id` (PK)
- `room_id` (FK)
- `asset_id` (FK, nullable)
- `issue_type`
- `description`
- `image_filename`
- `reporter_name`, `prn`, `reporter_email`
- `status` - open/in-progress/fixed

## 4th Floor Layout (Demo Floor)

```
        ┌─────────┐  ┌─────────┐
        │ VY424   │  │ VY422   │
        │Classroom│  │   Lab   │
        └─────────┘  └─────────┘
        ════════════════════════════  Main Corridor
┌────┐ ┌────┐ ┌────┐ ┌────┐  ┌────┐ ┌────┐ ┌────┐
│401 │ │402 │ │403 │ │404 │  │426 │ │427 │ │428 │  Center
│    │ │    │ │    │ │    │  │    │ │    │ │    │  Labs
└────┘ └────┘ └────┘ └────┘  └────┘ └────┘ └────┘
                              ┌────┐ ┌────┐ ┌────┐
                              │414 │ │413 │ │ WC │  Right Wing
                              └────┘ └────┘ └────┘
```

## Validation Rules

### Client-side
- PRN must be numeric
- Email must end with `@mitwpu.edu.in`
- Room must be selected from the map

### Server-side
- Same validations as client-side
- Image uploads limited to 16MB
- Allowed image types: PNG, JPG, JPEG, GIF, WEBP

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `vyas-secret-key-mitwpu-2024` | Flask secret key |
| `DATABASE_URL` | `sqlite:///vyas_tracker.db` | Database URL |
| `PORT` | `5000` | Server port |
| `FLASK_DEBUG` | `True` | Debug mode |

## License

MIT-WPU Internal Project
