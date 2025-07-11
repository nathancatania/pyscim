-- Applications table for multi-IdP support within tenants
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    external_id VARCHAR(255),
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    modified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    settings JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Unique constraints
    CONSTRAINT applications_name_tenant_unique UNIQUE (name, tenant_id),
    CONSTRAINT applications_external_id_unique UNIQUE (external_id)
);

-- Create indexes for performance
CREATE INDEX idx_applications_tenant_id ON applications(tenant_id);
CREATE INDEX idx_applications_name ON applications(name);
CREATE INDEX idx_applications_active ON applications(active);
CREATE INDEX idx_applications_external_id ON applications(external_id) WHERE external_id IS NOT NULL;

-- Create trigger to update modified_at
CREATE TRIGGER update_applications_modified_at 
    BEFORE UPDATE ON applications
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- Add comment explaining the purpose
COMMENT ON TABLE applications IS 'Represents different IdP sources (e.g., Entra ID, Okta) within a tenant that can sync SCIM resources';
COMMENT ON COLUMN applications.name IS 'Unique identifier name within the tenant (e.g., "entra-prod", "okta-dev")';
COMMENT ON COLUMN applications.display_name IS 'Human-readable name (e.g., "Entra ID Production")';