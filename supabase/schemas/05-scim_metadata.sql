-- Schema metadata table for tracking available schemas
CREATE TABLE IF NOT EXISTS schema_metadata (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    attributes JSONB NOT NULL,
    meta JSONB DEFAULT '{}'::jsonb
);

-- Insert core schemas
INSERT INTO schema_metadata (id, name, description, attributes) VALUES
(
    'urn:ietf:params:scim:schemas:core:2.0:User',
    'User',
    'User Account',
    '{
        "userName": {"type": "string", "required": true, "uniqueness": "server"},
        "name": {"type": "complex"},
        "displayName": {"type": "string"},
        "active": {"type": "boolean"},
        "emails": {"type": "complex", "multiValued": true},
        "phoneNumbers": {"type": "complex", "multiValued": true},
        "ims": {"type": "complex", "multiValued": true},
        "photos": {"type": "complex", "multiValued": true},
        "addresses": {"type": "complex", "multiValued": true},
        "entitlements": {"type": "complex", "multiValued": true},
        "roles": {"type": "complex", "multiValued": true},
        "x509Certificates": {"type": "complex", "multiValued": true}
    }'::jsonb
),
(
    'urn:ietf:params:scim:schemas:core:2.0:Group',
    'Group',
    'Group',
    '{
        "displayName": {"type": "string", "required": true},
        "members": {"type": "complex", "multiValued": true}
    }'::jsonb
),
(
    'urn:ietf:params:scim:schemas:extension:enterprise:2.0:User',
    'EnterpriseUser',
    'Enterprise User',
    '{
        "employeeNumber": {"type": "string"},
        "costCenter": {"type": "string"},
        "organization": {"type": "string"},
        "division": {"type": "string"},
        "department": {"type": "string"},
        "manager": {"type": "complex"}
    }'::jsonb
);

-- Service provider configuration
CREATE TABLE IF NOT EXISTS service_provider_config (
    id INTEGER PRIMARY KEY DEFAULT 1,
    documentation_uri TEXT DEFAULT 'https://example.com/scim/docs',
    patch_supported BOOLEAN DEFAULT true,
    bulk_supported BOOLEAN DEFAULT true,
    bulk_max_operations INTEGER DEFAULT 1000,
    bulk_max_payload_size INTEGER DEFAULT 1048576,
    filter_supported BOOLEAN DEFAULT true,
    filter_max_results INTEGER DEFAULT 1000,
    change_password_supported BOOLEAN DEFAULT true,
    sort_supported BOOLEAN DEFAULT true,
    etag_supported BOOLEAN DEFAULT true,
    authentication_schemes JSONB DEFAULT '[
        {
            "type": "oauthbearertoken",
            "name": "OAuth Bearer Token",
            "description": "Authentication scheme using the OAuth Bearer Token Standard",
            "specUri": "http://www.rfc-editor.org/info/rfc6750",
            "documentationUri": "https://example.com/scim/docs/auth"
        }
    ]'::jsonb,
    meta JSONB DEFAULT '{}'::jsonb,
    
    -- Ensure only one configuration exists
    CONSTRAINT single_config CHECK (id = 1)
);

-- Insert default configuration
INSERT INTO service_provider_config DEFAULT VALUES ON CONFLICT (id) DO NOTHING;

-- Audit log table for tracking all SCIM operations
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    operation TEXT NOT NULL,
    resource_type scim_resource_type,
    resource_id UUID,
    resource_external_id TEXT,
    actor_id TEXT,
    ip_address INET,
    user_agent TEXT,
    request_id TEXT,
    status_code INTEGER,
    error_message TEXT,
    request_body JSONB,
    response_body JSONB,
    duration_ms INTEGER
);

-- Create indexes for audit log
CREATE INDEX idx_audit_log_app_id ON audit_log(app_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_log_actor ON audit_log(actor_id);
CREATE INDEX idx_audit_log_operation ON audit_log(operation);

-- API tokens table for authentication
CREATE TABLE IF NOT EXISTS api_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,  -- Globally unique
    description TEXT,
    scopes TEXT[] DEFAULT ARRAY['scim:read', 'scim:write'],
    active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_by TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_api_tokens_app_id ON api_tokens(app_id);
CREATE INDEX idx_api_tokens_hash ON api_tokens(token_hash);
CREATE INDEX idx_api_tokens_active ON api_tokens(active) WHERE active = true;

-- Row Level Security (RLS) policies can be added here based on requirements