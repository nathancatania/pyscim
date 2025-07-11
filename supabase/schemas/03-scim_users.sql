-- SCIM Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    external_id TEXT,
    user_name TEXT NOT NULL,
    name_formatted TEXT,
    name_family_name TEXT,
    name_given_name TEXT,
    name_middle_name TEXT,
    name_honorific_prefix TEXT,
    name_honorific_suffix TEXT,
    display_name TEXT,
    nick_name TEXT,
    profile_url TEXT,
    title TEXT,
    user_type TEXT,
    preferred_language TEXT,
    locale TEXT,
    timezone TEXT,
    active BOOLEAN DEFAULT true,
    password_hash TEXT,
    
    -- Enterprise User Extension fields
    employee_number TEXT,
    cost_center TEXT,
    organization TEXT,
    division TEXT,
    department TEXT,
    manager_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Metadata
    created TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    etag TEXT,
    resource_type scim_resource_type DEFAULT 'User',
    
    -- Additional fields for Azure AD/Okta compatibility
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Unique constraints scoped to application
    UNIQUE(user_name, app_id),
    UNIQUE(external_id, app_id)
);

-- Emails table (multi-valued attribute)
CREATE TABLE IF NOT EXISTS user_emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    app_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    value TEXT NOT NULL,
    type TEXT,
    primary_email BOOLEAN DEFAULT false,
    display TEXT,
    UNIQUE(user_id, value)
);

-- Phone numbers table (multi-valued attribute)
CREATE TABLE IF NOT EXISTS user_phone_numbers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    app_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    value TEXT NOT NULL,
    type TEXT,
    primary_phone BOOLEAN DEFAULT false,
    display TEXT,
    UNIQUE(user_id, value)
);

-- IMs table (multi-valued attribute)
CREATE TABLE IF NOT EXISTS user_ims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    app_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    value TEXT NOT NULL,
    type TEXT,
    primary_im BOOLEAN DEFAULT false,
    display TEXT,
    UNIQUE(user_id, value)
);

-- Photos table (multi-valued attribute)
CREATE TABLE IF NOT EXISTS user_photos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    app_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    value TEXT NOT NULL,
    type TEXT,
    primary_photo BOOLEAN DEFAULT false,
    display TEXT,
    UNIQUE(user_id, value)
);

-- Addresses table (complex multi-valued attribute)
CREATE TABLE IF NOT EXISTS user_addresses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    app_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    formatted TEXT,
    street_address TEXT,
    locality TEXT,
    region TEXT,
    postal_code TEXT,
    country TEXT,
    type TEXT,
    primary_address BOOLEAN DEFAULT false
);

-- Entitlements table (multi-valued attribute)
CREATE TABLE IF NOT EXISTS user_entitlements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    app_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    value TEXT NOT NULL,
    display TEXT,
    type TEXT,
    primary_entitlement BOOLEAN DEFAULT false,
    UNIQUE(user_id, value)
);

-- Roles table (multi-valued attribute)
CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    app_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    value TEXT NOT NULL,
    display TEXT,
    type TEXT,
    primary_role BOOLEAN DEFAULT false,
    UNIQUE(user_id, value)
);

-- X509Certificates table (multi-valued attribute)
CREATE TABLE IF NOT EXISTS user_x509_certificates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    app_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    value TEXT NOT NULL,
    display TEXT,
    type TEXT,
    primary_certificate BOOLEAN DEFAULT false,
    UNIQUE(user_id, value)
);

-- Create indexes
CREATE INDEX idx_users_app_id ON users(app_id);
CREATE INDEX idx_users_user_name ON users(user_name);
CREATE INDEX idx_users_external_id ON users(external_id);
CREATE INDEX idx_users_active ON users(active);
CREATE INDEX idx_users_created ON users(created);
CREATE INDEX idx_users_modified ON users(modified);
CREATE INDEX idx_users_metadata ON users USING GIN(metadata);

CREATE INDEX idx_user_emails_user_id ON user_emails(user_id);
CREATE INDEX idx_user_emails_app_id ON user_emails(app_id);
CREATE INDEX idx_user_emails_value ON user_emails(value);
CREATE INDEX idx_user_emails_primary ON user_emails(user_id) WHERE primary_email = true;

-- Similar indexes for other user-related tables
CREATE INDEX idx_user_phone_numbers_app_id ON user_phone_numbers(app_id);
CREATE INDEX idx_user_ims_app_id ON user_ims(app_id);
CREATE INDEX idx_user_photos_app_id ON user_photos(app_id);
CREATE INDEX idx_user_addresses_app_id ON user_addresses(app_id);
CREATE INDEX idx_user_entitlements_app_id ON user_entitlements(app_id);
CREATE INDEX idx_user_roles_app_id ON user_roles(app_id);
CREATE INDEX idx_user_x509_certificates_app_id ON user_x509_certificates(app_id);

-- Triggers
CREATE TRIGGER update_users_modified BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER generate_users_etag BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION generate_etag();