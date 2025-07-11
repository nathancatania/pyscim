-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom types
CREATE TYPE scim_resource_type AS ENUM ('User', 'Group');

-- Function to update modified timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to generate etag from resource data
CREATE OR REPLACE FUNCTION generate_etag()
RETURNS TRIGGER AS $$
BEGIN
    NEW.etag = encode(digest(NEW::text, 'md5'), 'hex');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;