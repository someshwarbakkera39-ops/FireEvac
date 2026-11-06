-- ============================================================================
-- Smart Emergency Evacuation Planning & Digital Twin System
-- SQLite Relational Database Schema (Blueprint Section 11)
-- ============================================================================

-- 1. Administrative Personnel & Safety Officers
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'safety_officer', -- 'super_admin', 'safety_officer', 'floor_warden'
    full_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Building Elevation Levels
CREATE TABLE IF NOT EXISTS floors (
    id INTEGER PRIMARY KEY, -- 0 (Ground), 1, 2, 3, 4
    floor_number INTEGER UNIQUE NOT NULL,
    floor_name TEXT NOT NULL,
    map_svg TEXT,
    short_code TEXT NOT NULL,
    total_rooms INTEGER DEFAULT 0,
    has_exits BOOLEAN DEFAULT 0
);

-- 3. Waypoint Navigation Nodes (X, Y, Z Coordinate Space)
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY, -- e.g. 'N3_W_NORTH', 'NODE_ROOM_3_05', 'STAIR_A_3'
    floor_id INTEGER NOT NULL,
    x_coord REAL NOT NULL,
    y_coord REAL NOT NULL,
    type TEXT NOT NULL, -- 'corridor', 'room', 'stair', 'exit', 'assembly'
    name TEXT NOT NULL,
    code TEXT,
    metadata JSON,
    FOREIGN KEY (floor_id) REFERENCES floors(id) ON DELETE CASCADE
);

-- 4. Walkable Hallway Graph Edges Connecting Nodes
CREATE TABLE IF NOT EXISTS paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_node TEXT NOT NULL,
    to_node TEXT NOT NULL,
    weight REAL NOT NULL,
    is_blocked BOOLEAN DEFAULT 0,
    edge_type TEXT DEFAULT 'walkway', -- 'corridor', 'vertical_stair', 'room_access', 'exit_corridor', 'outdoor_egress'
    bidirectional BOOLEAN DEFAULT 1,
    FOREIGN KEY (from_node) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (to_node) REFERENCES nodes(id) ON DELETE CASCADE,
    UNIQUE(from_node, to_node)
);

-- 5. Stationary QR Code Positioning Labels
CREATE TABLE IF NOT EXISTS qr_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code_id TEXT UNIQUE NOT NULL, -- e.g. 'QR_BLOCKA_F3_N305'
    node_id TEXT NOT NULL,
    floor_id INTEGER NOT NULL,
    description TEXT,
    location_label TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (floor_id) REFERENCES floors(id) ON DELETE CASCADE
);

-- 6. Active Emergency Hazard Logs
CREATE TABLE IF NOT EXISTS hazards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    floor_id INTEGER NOT NULL,
    location_x REAL NOT NULL,
    location_y REAL NOT NULL,
    type TEXT NOT NULL DEFAULT 'fire', -- 'fire', 'smoke', 'structural_blockage', 'toxic_fumes'
    severity TEXT DEFAULT 'high', -- 'low', 'medium', 'high', 'critical'
    radius REAL DEFAULT 35.0,
    description TEXT,
    reported_by TEXT DEFAULT 'admin_simulator',
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (floor_id) REFERENCES floors(id) ON DELETE CASCADE
);

-- 7. Drill Tracking & Real-Time Occupancy Records
CREATE TABLE IF NOT EXISTS occupancy_sim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occupant_id TEXT UNIQUE NOT NULL,
    floor_id INTEGER NOT NULL,
    current_node TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'inside', -- 'inside', 'safe', 'evacuated', 'missing'
    scanned_qr TEXT,
    safe_exit TEXT,
    last_ping TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (current_node) REFERENCES nodes(id) ON DELETE SET NULL,
    FOREIGN KEY (floor_id) REFERENCES floors(id) ON DELETE CASCADE
);

-- 8. QR Scan Audit & Incident Log
CREATE TABLE IF NOT EXISTS qr_scans_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occupant_id TEXT NOT NULL,
    code_id TEXT NOT NULL,
    floor_id INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Indices for High-Frequency Spatial Lookups
CREATE INDEX IF NOT EXISTS idx_nodes_floor ON nodes(floor_id);
CREATE INDEX IF NOT EXISTS idx_paths_from ON paths(from_node);
CREATE INDEX IF NOT EXISTS idx_paths_to ON paths(to_node);
CREATE INDEX IF NOT EXISTS idx_paths_blocked ON paths(is_blocked);
CREATE INDEX IF NOT EXISTS idx_hazards_floor ON hazards(floor_id);
CREATE INDEX IF NOT EXISTS idx_qr_code_id ON qr_codes(code_id);

