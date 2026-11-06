# Smart Emergency Evacuation Planning & Digital Twin System
### Dynamic Path Optimization Using Dijkstra Algorithm, QR Indoor Localization, and Multi-Floor Navigation for Actual Block A Building

---

## 1. Project Titles & Identification
- **Primary Title**: Smart Emergency Evacuation Planning and Digital Twin System Using Dynamic Path Optimization
- **Alternative Academic Title**: Smart Emergency Evacuation System for Multi-Floor Buildings Using QR-Based Indoor Localization and Dynamic Route Optimization
- **Facility Scope**: Actual Block A Facility (Ground + Four Upper Floors, G+4)

---

## 2. Problem Statement
During emergencies such as fires, structural hazards, or acute safety threats, occupants inside multi-floor architectural facilities struggle to identify their exact location, rapidly reach the nearest safe exit, and avoid hazardous or smoke-blocked corridors. Traditional wall-mounted evacuation maps are static and inherently fail to update when a path or staircase is rendered hazardous.

This system solves these limitations by implementing a digital evacuation platform using actual architectural floor plans. It establishes an interactive 2D Digital Twin, utilizes stationary QR codes for instantaneous indoor positioning, leverages browser GPS outdoors, and executes Dijkstra's shortest-path algorithm to dynamically compute and adjust safe paths around simulated hazards.

---

## 3. High-Level System Architecture

```
                       [ Public Mobile Web Client ]              [ Admin Management Console ]
                                (/public, /sos)                             (/admin)
                                      |                                         |
                                      +--------------------+--------------------+
                                                           |
                                                [ Flask REST Backend ]
                                                (app.py / wsgi.py)
                                                           |
                           +-------------------------------+-------------------------------+
                           |                               |                               |
             [ Dijkstra Routing Engine ]        [ SQLite Relational Store ]      [ 2D Digital Twin Vector Engine ]
              (engine/dijkstra.py)               (digital_twin.db)                (static/js/map_renderer.js)
              - Min-Heap Priority Queue          - admin_users (Credentials)      - Ground through 4th floor SVG
              - Real-time Edge Exclusion         - floors, nodes, paths           - Interactive Pan & Zoom
              - Multi-Floor Descent Cost         - hazards, qr_codes, occupancy   - Section 9 Visual Safety Palette
```

---

## 4. Visual Safety Ergonomics Palette (Blueprint Section 9)

| Element / State | Visual Representation | Hex Code | Functional Meaning |
| :--- | :--- | :--- | :--- |
| **Safe Evacuation Path** | Bright Green | `#16a34a` | Cleared, verified route calculated by Dijkstra algorithm |
| **Hazard / Fire Zone** | Vivid Red | `#dc2626` | Simulated fire, smoke obstruction, or impassable corridor |
| **Current User Location** | Electric Blue | `#2563eb` | Exact indoor node resolved via QR code scan or GPS |
| **Warning / Stairwell Zone** | Amber / Orange | `#f59e0b` | Continuous fire-rated stairwell cores (Staircase A & B) |
| **Building Geometry** | Neutral Slate | `#64748b` | Architectural room outlines, non-walkable barriers, walls |

---

## 5. Relational Database Design (Blueprint Section 11)

The SQLite database (`database/digital_twin.db`) encapsulates 7 core schemas:
1. `admin_users`: `id`, `username`, `password_hash`, `role`, `full_name`, `created_at`
2. `floors`: `id`, `floor_number`, `floor_name`, `short_code`, `total_rooms`, `has_exits`
3. `nodes`: `id`, `floor_id`, `x_coord`, `y_coord`, `type`, `name`, `code`, `metadata`
4. `paths`: `id`, `from_node`, `to_node`, `weight`, `is_blocked`, `edge_type`, `bidirectional`
5. `qr_codes`: `id`, `code_id`, `node_id`, `floor_id`, `description`, `location_label`
6. `hazards`: `id`, `floor_id`, `location_x`, `location_y`, `type`, `severity`, `radius`, `reported_by`
7. `occupancy_sim`: `id`, `occupant_id`, `floor_id`, `current_node`, `status`, `safe_exit`, `last_ping`

---

## 6. The 6 Consolidated Engineering Phases

- **Phase 1: Architectural Analysis & 2D Floor Digitization**: Digitize Block A CAD blueprints for Ground through 4th floor ($1200 \times 750$ coordinate space), mapping all 48 rooms, corridors, stairwells, and exits.
- **Phase 2: Spatial Graph Modeling & Routing Engine**: Model graph $G = (V, E)$ with 129 nodes, 133 edges, and calibrated vertical staircase descent costs ($w = 28$); implement priority queue Dijkstra with dynamic hazard exclusion.
- **Phase 3: Backend Architecture & Database Design**: Develop Python Flask REST backend, implement SQLite database schemas, seed data, and build session authentication and state management APIs.
- **Phase 4: Admin Emergency Management Portal**: High-contrast operations dashboard (`/admin`) with point-and-click hazard placement (fire, smoke, barricade), live occupancy drill status cards, and printable QR generator.
- **Phase 5: Public User Panel, QR & GPS Integration**: Zero-login mobile web client (`/public`, `/sos`), in-browser camera QR indoor positioning, and HTML5 Geolocation outdoor assembly grounds handoff.
- **Phase 6: System Integration, Testing & Deployment**: End-to-end validation of all 5 mandatory emergency scenarios, generation of physical QR test kit, WSGI production deployment configuration, and test suite verification.

---

## 7. Mandatory Emergency Scenarios (Blueprint Section 13)

All 5 core evaluation scenarios are validated with automated test cases:
1. **Standard Baseline Evacuation**: Normal conditions; computes shortest path from Floor 4 Auditorium to Ground Exit.
2. **Ground Floor Incident**: Exit 1 Main South blocked; system dynamically redirects occupants to West Fire Exit 2 or East Fire Exit 3.
3. **Vertical Corridor Blockage**: Staircase B engulfed on Floor 2; East wing occupants are seamlessly rerouted across the Central Bridge Spine to Staircase A (West).
4. **Live In-Transit Rerouting**: A corridor is blocked while an occupant is navigating; system recalculates route in real time.
5. **Multi-Hazard Complex Scenario**: Multiple corridors and stairwells blocked concurrently; algorithm extracts verified secondary egress.

---

## 8. Physical QR Code Testing Kit (Blueprint Section 14)

A complete printable physical test kit with 15 stationary indoor checkpoints has been generated at:
> `static/qr_testkit.html`

Formatted for A4 printout with high-contrast vector QR matrices, floor identifiers, target coordinate nodes, and cutting guidelines for prototype drill testing.

---

## 9. Prototype Limitations (Explicitly Stated - Section 15)

The current system is a software-based digital twin prototype. It cannot independently:
- Detect physical fires automatically without external IoT smoke sensors or cameras.
- Detect physical corridor blockages without manual admin marking or simulation reports.
- Continuously track occupants across rooms in real time using stationary QR codes.
- Replace legally certified building fire safety panels or statutory fire warden procedures.

> **Safety Disclaimer**: In an actual occupied architectural facility, all designated evacuation pathways must undergo rigorous validation by certified fire safety engineers before live operational reliance.

---

## 10. Future Engineering Enhancements (Section 16)
1. **IoT Smoke & Heat Sensors**: Direct hardware telemetry integration for automatic hazard placement via MQTT / CoAP.
2. **Computer Vision CCTV**: Automatic detection of corridor crowd density and physical obstructions via OpenCV.
3. **Bluetooth Low Energy (BLE) Beacons**: Continuous real-time indoor positioning without manual scanning.
4. **Automated Emergency Broadcasting**: Automated SMS and cellular broadcast alerts to building occupants.
5. **AI Predictive Evacuation Modeling**: Machine-learning algorithms for smoke dispersion forecasting.
6. **Native Mobile Applications & Voice Guidance**: Hands-free turn-by-turn auditory evacuation directions.

---

## 11. Quick Start & Execution

### Running the Local Web Server
```powershell
python app.py
```
Open your browser at:
- **Root 2D Digital Twin Viewer**: `http://localhost:5000/`
- **Dynamic Routing Studio**: `http://localhost:5000/routing`
- **Admin Management Portal**: `http://localhost:5000/admin`
- **Public Mobile SOS Client**: `http://localhost:5000/public`
- **Relational Database Explorer**: `http://localhost:5000/backend-explorer`
- **Printable QR Test Kit**: `http://localhost:5000/static/qr_testkit.html`

### Running the Complete Test Suite
```powershell
python -m pytest tests/ -v
```
All **33 automated unit and scenario tests** will execute and pass.

### Standalone Zero-Setup Browser Previews
All phases have dedicated standalone HTML files that can be opened directly without a running server:
- `preview_phase1.html` (2D Floor Digitization)
- `preview_phase2.html` (Dijkstra Routing & Hazards)
- `preview_phase3.html` (SQLite Database Explorer)
- `preview_phase4_admin.html` (Admin Portal & Simulation Center)
- `preview_phase5_public.html` (Public Mobile SOS & QR)
- `preview_final_system_demo.html` (Master All-In-One Demonstration)

