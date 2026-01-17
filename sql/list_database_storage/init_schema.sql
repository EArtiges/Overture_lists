-- Lists Table
CREATE TABLE IF NOT EXISTS list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id TEXT NOT NULL UNIQUE,
    list_type TEXT NOT NULL CHECK(list_type IN ('boundary', 'crm_client')),
    list_name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Division Metadata Table (stores all metadata with context type)
CREATE TABLE IF NOT EXISTS division_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    division_id TEXT NOT NULL,
    metadata_type TEXT NOT NULL CHECK(metadata_type IN ('boundary', 'crm_client')),
    -- Common fields
    division_name TEXT,
    division_subtype TEXT,
    country TEXT,
    -- CRM-specific fields (NULL for boundaries)
    system_id TEXT,
    account_name TEXT,
    custom_admin_level TEXT,
    geometry TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- List Item Junction Table
CREATE TABLE IF NOT EXISTS list_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id INTEGER NOT NULL,
    metadata_id INTEGER NOT NULL,
    item_order INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (list_id) REFERENCES list(id) ON DELETE CASCADE,
    FOREIGN KEY (metadata_id) REFERENCES division_metadata(id)
);

-- Indexes for list table
CREATE INDEX IF NOT EXISTS idx_list_created_at
    ON list(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_list_type
    ON list(list_type);

-- Indexes for list_item table
CREATE INDEX IF NOT EXISTS idx_list_item_list_id
    ON list_item(list_id);

CREATE INDEX IF NOT EXISTS idx_list_item_metadata_id
    ON list_item(metadata_id);

CREATE INDEX IF NOT EXISTS idx_list_item_order
    ON list_item(list_id, item_order);

-- Indexes for division_metadata table
CREATE INDEX IF NOT EXISTS idx_division_metadata_division_id
    ON division_metadata(division_id);

CREATE INDEX IF NOT EXISTS idx_division_metadata_type
    ON division_metadata(metadata_type);
