-- CRM Mappings Table
CREATE TABLE IF NOT EXISTS mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    system_id TEXT NOT NULL UNIQUE,
    account_name TEXT NOT NULL,
    custom_admin_level TEXT NOT NULL,
    division_id TEXT NOT NULL UNIQUE,
    division_name TEXT NOT NULL,
    overture_subtype TEXT,
    country TEXT NOT NULL,
    geometry TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for mappings
CREATE INDEX IF NOT EXISTS idx_country
    ON mappings(country);

CREATE INDEX IF NOT EXISTS idx_system_id
    ON mappings(system_id);

-- Division Info Table (shared metadata repository)
CREATE TABLE IF NOT EXISTS division_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    division_id TEXT NOT NULL UNIQUE,
    division_name TEXT,
    division_subtype TEXT,
    country TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relationships Table (organizational hierarchy)
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    child_division_id TEXT NOT NULL,
    parent_division_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL DEFAULT 'reports_to',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(child_division_id, parent_division_id, relationship_type),
    CHECK(child_division_id != parent_division_id)
);

-- Indexes for division_info
CREATE INDEX IF NOT EXISTS idx_division_info_division_id
    ON division_info(division_id);

-- Indexes for relationships
CREATE INDEX IF NOT EXISTS idx_child_division
    ON relationships(child_division_id);

CREATE INDEX IF NOT EXISTS idx_parent_division
    ON relationships(parent_division_id);
