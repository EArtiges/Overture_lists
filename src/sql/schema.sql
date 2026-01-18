-- Schema for Overture Lists Application
-- Single SQLite database for all application data

-- Cached divisions from Overture Maps
CREATE TABLE IF NOT EXISTS divisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    system_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    subtype TEXT,
    country TEXT,
    geometry_json TEXT,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User-created lists
CREATE TABLE IF NOT EXISTS lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('division', 'client')),
    notes TEXT DEFAULT '',
    hash TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Junction table: Lists -> Divisions
CREATE TABLE IF NOT EXISTS list_divisions (
    list_id INTEGER NOT NULL,
    division_id INTEGER NOT NULL,
    FOREIGN KEY (list_id) REFERENCES lists(id) ON DELETE CASCADE,
    FOREIGN KEY (division_id) REFERENCES divisions(id) ON DELETE CASCADE,
    PRIMARY KEY (list_id, division_id)
);

-- Junction table: Lists -> CRM Clients
CREATE TABLE IF NOT EXISTS list_clients (
    list_id INTEGER NOT NULL,
    system_id TEXT NOT NULL,
    FOREIGN KEY (list_id) REFERENCES lists(id) ON DELETE CASCADE,
    FOREIGN KEY (system_id) REFERENCES crm_mappings(system_id) ON DELETE CASCADE,
    PRIMARY KEY (list_id, system_id)
);

-- CRM mappings (1:1 with divisions)
CREATE TABLE IF NOT EXISTS crm_mappings (
    system_id TEXT PRIMARY KEY,
    division_id INTEGER UNIQUE NOT NULL,
    account_name TEXT NOT NULL,
    custom_admin_level TEXT,
    division_name TEXT,
    overture_subtype TEXT,
    country TEXT,
    geometry_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (division_id) REFERENCES divisions(id) ON DELETE CASCADE
);

-- Organizational hierarchy relationships
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_division_id INTEGER NOT NULL,
    child_division_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_division_id) REFERENCES divisions(id) ON DELETE CASCADE,
    FOREIGN KEY (child_division_id) REFERENCES divisions(id) ON DELETE CASCADE,
    CHECK (parent_division_id != child_division_id),
    UNIQUE (parent_division_id, child_division_id, relationship_type)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_divisions_system_id ON divisions(system_id);
CREATE INDEX IF NOT EXISTS idx_lists_type ON lists(type);
CREATE INDEX IF NOT EXISTS idx_lists_hash ON lists(hash);
CREATE INDEX IF NOT EXISTS idx_crm_mappings_division_id ON crm_mappings(division_id);
