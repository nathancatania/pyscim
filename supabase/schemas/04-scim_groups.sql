-- SCIM Groups table
CREATE TABLE IF NOT EXISTS groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    external_id TEXT,
    display_name TEXT NOT NULL,
    
    -- Metadata
    created TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    etag TEXT,
    resource_type scim_resource_type DEFAULT 'Group',
    
    -- Additional fields for Azure AD/Okta compatibility
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Unique constraints scoped to application
    UNIQUE(display_name, app_id),
    UNIQUE(external_id, app_id)
);

-- Group members table (many-to-many relationship)
CREATE TABLE IF NOT EXISTS group_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    app_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    nested_group_id UUID REFERENCES groups(id) ON DELETE CASCADE,
    display TEXT,
    type TEXT DEFAULT 'User',
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure either user_id or nested_group_id is set, but not both
    CONSTRAINT member_type_check CHECK (
        (user_id IS NOT NULL AND nested_group_id IS NULL) OR
        (user_id IS NULL AND nested_group_id IS NOT NULL)
    ),
    
    -- Prevent duplicate memberships
    UNIQUE(group_id, user_id),
    UNIQUE(group_id, nested_group_id)
);

-- Create indexes
CREATE INDEX idx_groups_app_id ON groups(app_id);
CREATE INDEX idx_groups_display_name ON groups(display_name);
CREATE INDEX idx_groups_external_id ON groups(external_id);
CREATE INDEX idx_groups_created ON groups(created);
CREATE INDEX idx_groups_modified ON groups(modified);
CREATE INDEX idx_groups_metadata ON groups USING GIN(metadata);

CREATE INDEX idx_group_members_group_id ON group_members(group_id);
CREATE INDEX idx_group_members_app_id ON group_members(app_id);
CREATE INDEX idx_group_members_user_id ON group_members(user_id);
CREATE INDEX idx_group_members_nested_group_id ON group_members(nested_group_id);

-- Triggers
CREATE TRIGGER update_groups_modified BEFORE UPDATE ON groups
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER generate_groups_etag BEFORE INSERT OR UPDATE ON groups
    FOR EACH ROW EXECUTE FUNCTION generate_etag();

-- Function to update group modification time when members change
CREATE OR REPLACE FUNCTION update_group_modified_on_member_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        UPDATE groups SET modified = CURRENT_TIMESTAMP WHERE id = NEW.group_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE groups SET modified = CURRENT_TIMESTAMP WHERE id = OLD.group_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_group_on_member_change
AFTER INSERT OR UPDATE OR DELETE ON group_members
    FOR EACH ROW EXECUTE FUNCTION update_group_modified_on_member_change();