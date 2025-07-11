create type "public"."scim_resource_type" as enum ('User', 'Group');

create table "public"."api_tokens" (
    "id" uuid not null default uuid_generate_v4(),
    "app_id" uuid not null,
    "name" text not null,
    "token_hash" text not null,
    "description" text,
    "scopes" text[] default ARRAY['scim:read'::text, 'scim:write'::text],
    "active" boolean default true,
    "expires_at" timestamp with time zone,
    "created_at" timestamp with time zone default CURRENT_TIMESTAMP,
    "last_used_at" timestamp with time zone,
    "created_by" text,
    "metadata" jsonb default '{}'::jsonb
);


create table "public"."applications" (
    "id" uuid not null default gen_random_uuid(),
    "tenant_id" uuid not null,
    "name" character varying(255) not null,
    "display_name" character varying(255) not null,
    "description" text,
    "external_id" character varying(255),
    "active" boolean not null default true,
    "created_at" timestamp with time zone not null default now(),
    "modified_at" timestamp with time zone not null default now(),
    "settings" jsonb default '{}'::jsonb,
    "metadata" jsonb default '{}'::jsonb
);


create table "public"."audit_log" (
    "id" uuid not null default uuid_generate_v4(),
    "app_id" uuid not null,
    "timestamp" timestamp with time zone default CURRENT_TIMESTAMP,
    "operation" text not null,
    "resource_type" scim_resource_type,
    "resource_id" uuid,
    "resource_external_id" text,
    "actor_id" text,
    "ip_address" inet,
    "user_agent" text,
    "request_id" text,
    "status_code" integer,
    "error_message" text,
    "request_body" jsonb,
    "response_body" jsonb,
    "duration_ms" integer
);


create table "public"."group_members" (
    "id" uuid not null default uuid_generate_v4(),
    "group_id" uuid not null,
    "app_id" uuid not null,
    "user_id" uuid,
    "nested_group_id" uuid,
    "display" text,
    "type" text default 'User'::text,
    "added_at" timestamp with time zone default CURRENT_TIMESTAMP
);


create table "public"."groups" (
    "id" uuid not null default uuid_generate_v4(),
    "app_id" uuid not null,
    "external_id" text,
    "display_name" text not null,
    "created" timestamp with time zone default CURRENT_TIMESTAMP,
    "modified" timestamp with time zone default CURRENT_TIMESTAMP,
    "etag" text,
    "resource_type" scim_resource_type default 'Group'::scim_resource_type,
    "metadata" jsonb default '{}'::jsonb
);


create table "public"."schema_metadata" (
    "id" text not null,
    "name" text not null,
    "description" text,
    "attributes" jsonb not null,
    "meta" jsonb default '{}'::jsonb
);


create table "public"."service_provider_config" (
    "id" integer not null default 1,
    "documentation_uri" text default 'https://example.com/scim/docs'::text,
    "patch_supported" boolean default true,
    "bulk_supported" boolean default true,
    "bulk_max_operations" integer default 1000,
    "bulk_max_payload_size" integer default 1048576,
    "filter_supported" boolean default true,
    "filter_max_results" integer default 1000,
    "change_password_supported" boolean default true,
    "sort_supported" boolean default true,
    "etag_supported" boolean default true,
    "authentication_schemes" jsonb default '[{"name": "OAuth Bearer Token", "type": "oauthbearertoken", "specUri": "http://www.rfc-editor.org/info/rfc6750", "description": "Authentication scheme using the OAuth Bearer Token Standard", "documentationUri": "https://example.com/scim/docs/auth"}]'::jsonb,
    "meta" jsonb default '{}'::jsonb
);


create table "public"."tenants" (
    "id" uuid not null default gen_random_uuid(),
    "name" character varying(255) not null,
    "display_name" character varying(255) not null,
    "external_id" character varying(255),
    "active" boolean not null default true,
    "created_at" timestamp with time zone not null default now(),
    "modified_at" timestamp with time zone not null default now(),
    "settings" jsonb default '{}'::jsonb,
    "metadata" jsonb default '{}'::jsonb
);


create table "public"."user_addresses" (
    "id" uuid not null default uuid_generate_v4(),
    "user_id" uuid not null,
    "app_id" uuid not null,
    "formatted" text,
    "street_address" text,
    "locality" text,
    "region" text,
    "postal_code" text,
    "country" text,
    "type" text,
    "primary_address" boolean default false
);


create table "public"."user_emails" (
    "id" uuid not null default uuid_generate_v4(),
    "user_id" uuid not null,
    "app_id" uuid not null,
    "value" text not null,
    "type" text,
    "primary_email" boolean default false,
    "display" text
);


create table "public"."user_entitlements" (
    "id" uuid not null default uuid_generate_v4(),
    "user_id" uuid not null,
    "app_id" uuid not null,
    "value" text not null,
    "display" text,
    "type" text,
    "primary_entitlement" boolean default false
);


create table "public"."user_ims" (
    "id" uuid not null default uuid_generate_v4(),
    "user_id" uuid not null,
    "app_id" uuid not null,
    "value" text not null,
    "type" text,
    "primary_im" boolean default false,
    "display" text
);


create table "public"."user_phone_numbers" (
    "id" uuid not null default uuid_generate_v4(),
    "user_id" uuid not null,
    "app_id" uuid not null,
    "value" text not null,
    "type" text,
    "primary_phone" boolean default false,
    "display" text
);


create table "public"."user_photos" (
    "id" uuid not null default uuid_generate_v4(),
    "user_id" uuid not null,
    "app_id" uuid not null,
    "value" text not null,
    "type" text,
    "primary_photo" boolean default false,
    "display" text
);


create table "public"."user_roles" (
    "id" uuid not null default uuid_generate_v4(),
    "user_id" uuid not null,
    "app_id" uuid not null,
    "value" text not null,
    "display" text,
    "type" text,
    "primary_role" boolean default false
);


create table "public"."user_x509_certificates" (
    "id" uuid not null default uuid_generate_v4(),
    "user_id" uuid not null,
    "app_id" uuid not null,
    "value" text not null,
    "display" text,
    "type" text,
    "primary_certificate" boolean default false
);


create table "public"."users" (
    "id" uuid not null default uuid_generate_v4(),
    "app_id" uuid not null,
    "external_id" text,
    "user_name" text not null,
    "name_formatted" text,
    "name_family_name" text,
    "name_given_name" text,
    "name_middle_name" text,
    "name_honorific_prefix" text,
    "name_honorific_suffix" text,
    "display_name" text,
    "nick_name" text,
    "profile_url" text,
    "title" text,
    "user_type" text,
    "preferred_language" text,
    "locale" text,
    "timezone" text,
    "active" boolean default true,
    "password_hash" text,
    "employee_number" text,
    "cost_center" text,
    "organization" text,
    "division" text,
    "department" text,
    "manager_id" uuid,
    "created" timestamp with time zone default CURRENT_TIMESTAMP,
    "modified" timestamp with time zone default CURRENT_TIMESTAMP,
    "etag" text,
    "resource_type" scim_resource_type default 'User'::scim_resource_type,
    "metadata" jsonb default '{}'::jsonb
);


CREATE UNIQUE INDEX api_tokens_pkey ON public.api_tokens USING btree (id);

CREATE UNIQUE INDEX api_tokens_token_hash_key ON public.api_tokens USING btree (token_hash);

CREATE UNIQUE INDEX applications_external_id_unique ON public.applications USING btree (external_id);

CREATE UNIQUE INDEX applications_name_tenant_unique ON public.applications USING btree (name, tenant_id);

CREATE UNIQUE INDEX applications_pkey ON public.applications USING btree (id);

CREATE UNIQUE INDEX audit_log_pkey ON public.audit_log USING btree (id);

CREATE UNIQUE INDEX group_members_group_id_nested_group_id_key ON public.group_members USING btree (group_id, nested_group_id);

CREATE UNIQUE INDEX group_members_group_id_user_id_key ON public.group_members USING btree (group_id, user_id);

CREATE UNIQUE INDEX group_members_pkey ON public.group_members USING btree (id);

CREATE UNIQUE INDEX groups_display_name_app_id_key ON public.groups USING btree (display_name, app_id);

CREATE UNIQUE INDEX groups_external_id_app_id_key ON public.groups USING btree (external_id, app_id);

CREATE UNIQUE INDEX groups_pkey ON public.groups USING btree (id);

CREATE INDEX idx_api_tokens_active ON public.api_tokens USING btree (active) WHERE (active = true);

CREATE INDEX idx_api_tokens_app_id ON public.api_tokens USING btree (app_id);

CREATE INDEX idx_api_tokens_hash ON public.api_tokens USING btree (token_hash);

CREATE INDEX idx_applications_active ON public.applications USING btree (active);

CREATE INDEX idx_applications_external_id ON public.applications USING btree (external_id) WHERE (external_id IS NOT NULL);

CREATE INDEX idx_applications_name ON public.applications USING btree (name);

CREATE INDEX idx_applications_tenant_id ON public.applications USING btree (tenant_id);

CREATE INDEX idx_audit_log_actor ON public.audit_log USING btree (actor_id);

CREATE INDEX idx_audit_log_app_id ON public.audit_log USING btree (app_id);

CREATE INDEX idx_audit_log_operation ON public.audit_log USING btree (operation);

CREATE INDEX idx_audit_log_resource ON public.audit_log USING btree (resource_type, resource_id);

CREATE INDEX idx_audit_log_timestamp ON public.audit_log USING btree ("timestamp" DESC);

CREATE INDEX idx_group_members_app_id ON public.group_members USING btree (app_id);

CREATE INDEX idx_group_members_group_id ON public.group_members USING btree (group_id);

CREATE INDEX idx_group_members_nested_group_id ON public.group_members USING btree (nested_group_id);

CREATE INDEX idx_group_members_user_id ON public.group_members USING btree (user_id);

CREATE INDEX idx_groups_app_id ON public.groups USING btree (app_id);

CREATE INDEX idx_groups_created ON public.groups USING btree (created);

CREATE INDEX idx_groups_display_name ON public.groups USING btree (display_name);

CREATE INDEX idx_groups_external_id ON public.groups USING btree (external_id);

CREATE INDEX idx_groups_metadata ON public.groups USING gin (metadata);

CREATE INDEX idx_groups_modified ON public.groups USING btree (modified);

CREATE INDEX idx_tenants_active ON public.tenants USING btree (active);

CREATE INDEX idx_tenants_external_id ON public.tenants USING btree (external_id) WHERE (external_id IS NOT NULL);

CREATE INDEX idx_tenants_name ON public.tenants USING btree (name);

CREATE INDEX idx_user_addresses_app_id ON public.user_addresses USING btree (app_id);

CREATE INDEX idx_user_emails_app_id ON public.user_emails USING btree (app_id);

CREATE INDEX idx_user_emails_primary ON public.user_emails USING btree (user_id) WHERE (primary_email = true);

CREATE INDEX idx_user_emails_user_id ON public.user_emails USING btree (user_id);

CREATE INDEX idx_user_emails_value ON public.user_emails USING btree (value);

CREATE INDEX idx_user_entitlements_app_id ON public.user_entitlements USING btree (app_id);

CREATE INDEX idx_user_ims_app_id ON public.user_ims USING btree (app_id);

CREATE INDEX idx_user_phone_numbers_app_id ON public.user_phone_numbers USING btree (app_id);

CREATE INDEX idx_user_photos_app_id ON public.user_photos USING btree (app_id);

CREATE INDEX idx_user_roles_app_id ON public.user_roles USING btree (app_id);

CREATE INDEX idx_user_x509_certificates_app_id ON public.user_x509_certificates USING btree (app_id);

CREATE INDEX idx_users_active ON public.users USING btree (active);

CREATE INDEX idx_users_app_id ON public.users USING btree (app_id);

CREATE INDEX idx_users_created ON public.users USING btree (created);

CREATE INDEX idx_users_external_id ON public.users USING btree (external_id);

CREATE INDEX idx_users_metadata ON public.users USING gin (metadata);

CREATE INDEX idx_users_modified ON public.users USING btree (modified);

CREATE INDEX idx_users_user_name ON public.users USING btree (user_name);

CREATE UNIQUE INDEX schema_metadata_pkey ON public.schema_metadata USING btree (id);

CREATE UNIQUE INDEX service_provider_config_pkey ON public.service_provider_config USING btree (id);

CREATE UNIQUE INDEX tenants_external_id_unique ON public.tenants USING btree (external_id);

CREATE UNIQUE INDEX tenants_name_key ON public.tenants USING btree (name);

CREATE UNIQUE INDEX tenants_pkey ON public.tenants USING btree (id);

CREATE UNIQUE INDEX user_addresses_pkey ON public.user_addresses USING btree (id);

CREATE UNIQUE INDEX user_emails_pkey ON public.user_emails USING btree (id);

CREATE UNIQUE INDEX user_emails_user_id_value_key ON public.user_emails USING btree (user_id, value);

CREATE UNIQUE INDEX user_entitlements_pkey ON public.user_entitlements USING btree (id);

CREATE UNIQUE INDEX user_entitlements_user_id_value_key ON public.user_entitlements USING btree (user_id, value);

CREATE UNIQUE INDEX user_ims_pkey ON public.user_ims USING btree (id);

CREATE UNIQUE INDEX user_ims_user_id_value_key ON public.user_ims USING btree (user_id, value);

CREATE UNIQUE INDEX user_phone_numbers_pkey ON public.user_phone_numbers USING btree (id);

CREATE UNIQUE INDEX user_phone_numbers_user_id_value_key ON public.user_phone_numbers USING btree (user_id, value);

CREATE UNIQUE INDEX user_photos_pkey ON public.user_photos USING btree (id);

CREATE UNIQUE INDEX user_photos_user_id_value_key ON public.user_photos USING btree (user_id, value);

CREATE UNIQUE INDEX user_roles_pkey ON public.user_roles USING btree (id);

CREATE UNIQUE INDEX user_roles_user_id_value_key ON public.user_roles USING btree (user_id, value);

CREATE UNIQUE INDEX user_x509_certificates_pkey ON public.user_x509_certificates USING btree (id);

CREATE UNIQUE INDEX user_x509_certificates_user_id_value_key ON public.user_x509_certificates USING btree (user_id, value);

CREATE UNIQUE INDEX users_external_id_app_id_key ON public.users USING btree (external_id, app_id);

CREATE UNIQUE INDEX users_pkey ON public.users USING btree (id);

CREATE UNIQUE INDEX users_user_name_app_id_key ON public.users USING btree (user_name, app_id);

alter table "public"."api_tokens" add constraint "api_tokens_pkey" PRIMARY KEY using index "api_tokens_pkey";

alter table "public"."applications" add constraint "applications_pkey" PRIMARY KEY using index "applications_pkey";

alter table "public"."audit_log" add constraint "audit_log_pkey" PRIMARY KEY using index "audit_log_pkey";

alter table "public"."group_members" add constraint "group_members_pkey" PRIMARY KEY using index "group_members_pkey";

alter table "public"."groups" add constraint "groups_pkey" PRIMARY KEY using index "groups_pkey";

alter table "public"."schema_metadata" add constraint "schema_metadata_pkey" PRIMARY KEY using index "schema_metadata_pkey";

alter table "public"."service_provider_config" add constraint "service_provider_config_pkey" PRIMARY KEY using index "service_provider_config_pkey";

alter table "public"."tenants" add constraint "tenants_pkey" PRIMARY KEY using index "tenants_pkey";

alter table "public"."user_addresses" add constraint "user_addresses_pkey" PRIMARY KEY using index "user_addresses_pkey";

alter table "public"."user_emails" add constraint "user_emails_pkey" PRIMARY KEY using index "user_emails_pkey";

alter table "public"."user_entitlements" add constraint "user_entitlements_pkey" PRIMARY KEY using index "user_entitlements_pkey";

alter table "public"."user_ims" add constraint "user_ims_pkey" PRIMARY KEY using index "user_ims_pkey";

alter table "public"."user_phone_numbers" add constraint "user_phone_numbers_pkey" PRIMARY KEY using index "user_phone_numbers_pkey";

alter table "public"."user_photos" add constraint "user_photos_pkey" PRIMARY KEY using index "user_photos_pkey";

alter table "public"."user_roles" add constraint "user_roles_pkey" PRIMARY KEY using index "user_roles_pkey";

alter table "public"."user_x509_certificates" add constraint "user_x509_certificates_pkey" PRIMARY KEY using index "user_x509_certificates_pkey";

alter table "public"."users" add constraint "users_pkey" PRIMARY KEY using index "users_pkey";

alter table "public"."api_tokens" add constraint "api_tokens_app_id_fkey" FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE not valid;

alter table "public"."api_tokens" validate constraint "api_tokens_app_id_fkey";

alter table "public"."api_tokens" add constraint "api_tokens_token_hash_key" UNIQUE using index "api_tokens_token_hash_key";

alter table "public"."applications" add constraint "applications_external_id_unique" UNIQUE using index "applications_external_id_unique";

alter table "public"."applications" add constraint "applications_name_tenant_unique" UNIQUE using index "applications_name_tenant_unique";

alter table "public"."applications" add constraint "applications_tenant_id_fkey" FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE not valid;

alter table "public"."applications" validate constraint "applications_tenant_id_fkey";

alter table "public"."audit_log" add constraint "audit_log_app_id_fkey" FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE not valid;

alter table "public"."audit_log" validate constraint "audit_log_app_id_fkey";

alter table "public"."group_members" add constraint "group_members_app_id_fkey" FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE not valid;

alter table "public"."group_members" validate constraint "group_members_app_id_fkey";

alter table "public"."group_members" add constraint "group_members_group_id_fkey" FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE not valid;

alter table "public"."group_members" validate constraint "group_members_group_id_fkey";

alter table "public"."group_members" add constraint "group_members_group_id_nested_group_id_key" UNIQUE using index "group_members_group_id_nested_group_id_key";

alter table "public"."group_members" add constraint "group_members_group_id_user_id_key" UNIQUE using index "group_members_group_id_user_id_key";

alter table "public"."group_members" add constraint "group_members_nested_group_id_fkey" FOREIGN KEY (nested_group_id) REFERENCES groups(id) ON DELETE CASCADE not valid;

alter table "public"."group_members" validate constraint "group_members_nested_group_id_fkey";

alter table "public"."group_members" add constraint "group_members_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."group_members" validate constraint "group_members_user_id_fkey";

alter table "public"."group_members" add constraint "member_type_check" CHECK ((((user_id IS NOT NULL) AND (nested_group_id IS NULL)) OR ((user_id IS NULL) AND (nested_group_id IS NOT NULL)))) not valid;

alter table "public"."group_members" validate constraint "member_type_check";

alter table "public"."groups" add constraint "groups_app_id_fkey" FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE not valid;

alter table "public"."groups" validate constraint "groups_app_id_fkey";

alter table "public"."groups" add constraint "groups_display_name_app_id_key" UNIQUE using index "groups_display_name_app_id_key";

alter table "public"."groups" add constraint "groups_external_id_app_id_key" UNIQUE using index "groups_external_id_app_id_key";

alter table "public"."service_provider_config" add constraint "single_config" CHECK ((id = 1)) not valid;

alter table "public"."service_provider_config" validate constraint "single_config";

alter table "public"."tenants" add constraint "tenants_external_id_unique" UNIQUE using index "tenants_external_id_unique";

alter table "public"."tenants" add constraint "tenants_name_key" UNIQUE using index "tenants_name_key";

alter table "public"."user_addresses" add constraint "user_addresses_app_id_fkey" FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE not valid;

alter table "public"."user_addresses" validate constraint "user_addresses_app_id_fkey";

alter table "public"."user_addresses" add constraint "user_addresses_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."user_addresses" validate constraint "user_addresses_user_id_fkey";

alter table "public"."user_emails" add constraint "user_emails_app_id_fkey" FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE not valid;

alter table "public"."user_emails" validate constraint "user_emails_app_id_fkey";

alter table "public"."user_emails" add constraint "user_emails_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."user_emails" validate constraint "user_emails_user_id_fkey";

alter table "public"."user_emails" add constraint "user_emails_user_id_value_key" UNIQUE using index "user_emails_user_id_value_key";

alter table "public"."user_entitlements" add constraint "user_entitlements_app_id_fkey" FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE not valid;

alter table "public"."user_entitlements" validate constraint "user_entitlements_app_id_fkey";

alter table "public"."user_entitlements" add constraint "user_entitlements_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."user_entitlements" validate constraint "user_entitlements_user_id_fkey";

alter table "public"."user_entitlements" add constraint "user_entitlements_user_id_value_key" UNIQUE using index "user_entitlements_user_id_value_key";

alter table "public"."user_ims" add constraint "user_ims_app_id_fkey" FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE not valid;

alter table "public"."user_ims" validate constraint "user_ims_app_id_fkey";

alter table "public"."user_ims" add constraint "user_ims_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."user_ims" validate constraint "user_ims_user_id_fkey";

alter table "public"."user_ims" add constraint "user_ims_user_id_value_key" UNIQUE using index "user_ims_user_id_value_key";

alter table "public"."user_phone_numbers" add constraint "user_phone_numbers_app_id_fkey" FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE not valid;

alter table "public"."user_phone_numbers" validate constraint "user_phone_numbers_app_id_fkey";

alter table "public"."user_phone_numbers" add constraint "user_phone_numbers_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."user_phone_numbers" validate constraint "user_phone_numbers_user_id_fkey";

alter table "public"."user_phone_numbers" add constraint "user_phone_numbers_user_id_value_key" UNIQUE using index "user_phone_numbers_user_id_value_key";

alter table "public"."user_photos" add constraint "user_photos_app_id_fkey" FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE not valid;

alter table "public"."user_photos" validate constraint "user_photos_app_id_fkey";

alter table "public"."user_photos" add constraint "user_photos_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."user_photos" validate constraint "user_photos_user_id_fkey";

alter table "public"."user_photos" add constraint "user_photos_user_id_value_key" UNIQUE using index "user_photos_user_id_value_key";

alter table "public"."user_roles" add constraint "user_roles_app_id_fkey" FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE not valid;

alter table "public"."user_roles" validate constraint "user_roles_app_id_fkey";

alter table "public"."user_roles" add constraint "user_roles_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."user_roles" validate constraint "user_roles_user_id_fkey";

alter table "public"."user_roles" add constraint "user_roles_user_id_value_key" UNIQUE using index "user_roles_user_id_value_key";

alter table "public"."user_x509_certificates" add constraint "user_x509_certificates_app_id_fkey" FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE not valid;

alter table "public"."user_x509_certificates" validate constraint "user_x509_certificates_app_id_fkey";

alter table "public"."user_x509_certificates" add constraint "user_x509_certificates_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."user_x509_certificates" validate constraint "user_x509_certificates_user_id_fkey";

alter table "public"."user_x509_certificates" add constraint "user_x509_certificates_user_id_value_key" UNIQUE using index "user_x509_certificates_user_id_value_key";

alter table "public"."users" add constraint "users_app_id_fkey" FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE not valid;

alter table "public"."users" validate constraint "users_app_id_fkey";

alter table "public"."users" add constraint "users_external_id_app_id_key" UNIQUE using index "users_external_id_app_id_key";

alter table "public"."users" add constraint "users_manager_id_fkey" FOREIGN KEY (manager_id) REFERENCES users(id) ON DELETE SET NULL not valid;

alter table "public"."users" validate constraint "users_manager_id_fkey";

alter table "public"."users" add constraint "users_user_name_app_id_key" UNIQUE using index "users_user_name_app_id_key";

set check_function_bodies = off;

CREATE OR REPLACE FUNCTION public.generate_etag()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.etag = encode(digest(NEW::text, 'md5'), 'hex');
    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.update_group_modified_on_member_change()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        UPDATE groups SET modified = CURRENT_TIMESTAMP WHERE id = NEW.group_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE groups SET modified = CURRENT_TIMESTAMP WHERE id = OLD.group_id;
    END IF;
    RETURN NULL;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.update_modified_column()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.modified = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$function$
;

grant delete on table "public"."api_tokens" to "anon";

grant insert on table "public"."api_tokens" to "anon";

grant references on table "public"."api_tokens" to "anon";

grant select on table "public"."api_tokens" to "anon";

grant trigger on table "public"."api_tokens" to "anon";

grant truncate on table "public"."api_tokens" to "anon";

grant update on table "public"."api_tokens" to "anon";

grant delete on table "public"."api_tokens" to "authenticated";

grant insert on table "public"."api_tokens" to "authenticated";

grant references on table "public"."api_tokens" to "authenticated";

grant select on table "public"."api_tokens" to "authenticated";

grant trigger on table "public"."api_tokens" to "authenticated";

grant truncate on table "public"."api_tokens" to "authenticated";

grant update on table "public"."api_tokens" to "authenticated";

grant delete on table "public"."api_tokens" to "service_role";

grant insert on table "public"."api_tokens" to "service_role";

grant references on table "public"."api_tokens" to "service_role";

grant select on table "public"."api_tokens" to "service_role";

grant trigger on table "public"."api_tokens" to "service_role";

grant truncate on table "public"."api_tokens" to "service_role";

grant update on table "public"."api_tokens" to "service_role";

grant delete on table "public"."applications" to "anon";

grant insert on table "public"."applications" to "anon";

grant references on table "public"."applications" to "anon";

grant select on table "public"."applications" to "anon";

grant trigger on table "public"."applications" to "anon";

grant truncate on table "public"."applications" to "anon";

grant update on table "public"."applications" to "anon";

grant delete on table "public"."applications" to "authenticated";

grant insert on table "public"."applications" to "authenticated";

grant references on table "public"."applications" to "authenticated";

grant select on table "public"."applications" to "authenticated";

grant trigger on table "public"."applications" to "authenticated";

grant truncate on table "public"."applications" to "authenticated";

grant update on table "public"."applications" to "authenticated";

grant delete on table "public"."applications" to "service_role";

grant insert on table "public"."applications" to "service_role";

grant references on table "public"."applications" to "service_role";

grant select on table "public"."applications" to "service_role";

grant trigger on table "public"."applications" to "service_role";

grant truncate on table "public"."applications" to "service_role";

grant update on table "public"."applications" to "service_role";

grant delete on table "public"."audit_log" to "anon";

grant insert on table "public"."audit_log" to "anon";

grant references on table "public"."audit_log" to "anon";

grant select on table "public"."audit_log" to "anon";

grant trigger on table "public"."audit_log" to "anon";

grant truncate on table "public"."audit_log" to "anon";

grant update on table "public"."audit_log" to "anon";

grant delete on table "public"."audit_log" to "authenticated";

grant insert on table "public"."audit_log" to "authenticated";

grant references on table "public"."audit_log" to "authenticated";

grant select on table "public"."audit_log" to "authenticated";

grant trigger on table "public"."audit_log" to "authenticated";

grant truncate on table "public"."audit_log" to "authenticated";

grant update on table "public"."audit_log" to "authenticated";

grant delete on table "public"."audit_log" to "service_role";

grant insert on table "public"."audit_log" to "service_role";

grant references on table "public"."audit_log" to "service_role";

grant select on table "public"."audit_log" to "service_role";

grant trigger on table "public"."audit_log" to "service_role";

grant truncate on table "public"."audit_log" to "service_role";

grant update on table "public"."audit_log" to "service_role";

grant delete on table "public"."group_members" to "anon";

grant insert on table "public"."group_members" to "anon";

grant references on table "public"."group_members" to "anon";

grant select on table "public"."group_members" to "anon";

grant trigger on table "public"."group_members" to "anon";

grant truncate on table "public"."group_members" to "anon";

grant update on table "public"."group_members" to "anon";

grant delete on table "public"."group_members" to "authenticated";

grant insert on table "public"."group_members" to "authenticated";

grant references on table "public"."group_members" to "authenticated";

grant select on table "public"."group_members" to "authenticated";

grant trigger on table "public"."group_members" to "authenticated";

grant truncate on table "public"."group_members" to "authenticated";

grant update on table "public"."group_members" to "authenticated";

grant delete on table "public"."group_members" to "service_role";

grant insert on table "public"."group_members" to "service_role";

grant references on table "public"."group_members" to "service_role";

grant select on table "public"."group_members" to "service_role";

grant trigger on table "public"."group_members" to "service_role";

grant truncate on table "public"."group_members" to "service_role";

grant update on table "public"."group_members" to "service_role";

grant delete on table "public"."groups" to "anon";

grant insert on table "public"."groups" to "anon";

grant references on table "public"."groups" to "anon";

grant select on table "public"."groups" to "anon";

grant trigger on table "public"."groups" to "anon";

grant truncate on table "public"."groups" to "anon";

grant update on table "public"."groups" to "anon";

grant delete on table "public"."groups" to "authenticated";

grant insert on table "public"."groups" to "authenticated";

grant references on table "public"."groups" to "authenticated";

grant select on table "public"."groups" to "authenticated";

grant trigger on table "public"."groups" to "authenticated";

grant truncate on table "public"."groups" to "authenticated";

grant update on table "public"."groups" to "authenticated";

grant delete on table "public"."groups" to "service_role";

grant insert on table "public"."groups" to "service_role";

grant references on table "public"."groups" to "service_role";

grant select on table "public"."groups" to "service_role";

grant trigger on table "public"."groups" to "service_role";

grant truncate on table "public"."groups" to "service_role";

grant update on table "public"."groups" to "service_role";

grant delete on table "public"."schema_metadata" to "anon";

grant insert on table "public"."schema_metadata" to "anon";

grant references on table "public"."schema_metadata" to "anon";

grant select on table "public"."schema_metadata" to "anon";

grant trigger on table "public"."schema_metadata" to "anon";

grant truncate on table "public"."schema_metadata" to "anon";

grant update on table "public"."schema_metadata" to "anon";

grant delete on table "public"."schema_metadata" to "authenticated";

grant insert on table "public"."schema_metadata" to "authenticated";

grant references on table "public"."schema_metadata" to "authenticated";

grant select on table "public"."schema_metadata" to "authenticated";

grant trigger on table "public"."schema_metadata" to "authenticated";

grant truncate on table "public"."schema_metadata" to "authenticated";

grant update on table "public"."schema_metadata" to "authenticated";

grant delete on table "public"."schema_metadata" to "service_role";

grant insert on table "public"."schema_metadata" to "service_role";

grant references on table "public"."schema_metadata" to "service_role";

grant select on table "public"."schema_metadata" to "service_role";

grant trigger on table "public"."schema_metadata" to "service_role";

grant truncate on table "public"."schema_metadata" to "service_role";

grant update on table "public"."schema_metadata" to "service_role";

grant delete on table "public"."service_provider_config" to "anon";

grant insert on table "public"."service_provider_config" to "anon";

grant references on table "public"."service_provider_config" to "anon";

grant select on table "public"."service_provider_config" to "anon";

grant trigger on table "public"."service_provider_config" to "anon";

grant truncate on table "public"."service_provider_config" to "anon";

grant update on table "public"."service_provider_config" to "anon";

grant delete on table "public"."service_provider_config" to "authenticated";

grant insert on table "public"."service_provider_config" to "authenticated";

grant references on table "public"."service_provider_config" to "authenticated";

grant select on table "public"."service_provider_config" to "authenticated";

grant trigger on table "public"."service_provider_config" to "authenticated";

grant truncate on table "public"."service_provider_config" to "authenticated";

grant update on table "public"."service_provider_config" to "authenticated";

grant delete on table "public"."service_provider_config" to "service_role";

grant insert on table "public"."service_provider_config" to "service_role";

grant references on table "public"."service_provider_config" to "service_role";

grant select on table "public"."service_provider_config" to "service_role";

grant trigger on table "public"."service_provider_config" to "service_role";

grant truncate on table "public"."service_provider_config" to "service_role";

grant update on table "public"."service_provider_config" to "service_role";

grant delete on table "public"."tenants" to "anon";

grant insert on table "public"."tenants" to "anon";

grant references on table "public"."tenants" to "anon";

grant select on table "public"."tenants" to "anon";

grant trigger on table "public"."tenants" to "anon";

grant truncate on table "public"."tenants" to "anon";

grant update on table "public"."tenants" to "anon";

grant delete on table "public"."tenants" to "authenticated";

grant insert on table "public"."tenants" to "authenticated";

grant references on table "public"."tenants" to "authenticated";

grant select on table "public"."tenants" to "authenticated";

grant trigger on table "public"."tenants" to "authenticated";

grant truncate on table "public"."tenants" to "authenticated";

grant update on table "public"."tenants" to "authenticated";

grant delete on table "public"."tenants" to "service_role";

grant insert on table "public"."tenants" to "service_role";

grant references on table "public"."tenants" to "service_role";

grant select on table "public"."tenants" to "service_role";

grant trigger on table "public"."tenants" to "service_role";

grant truncate on table "public"."tenants" to "service_role";

grant update on table "public"."tenants" to "service_role";

grant delete on table "public"."user_addresses" to "anon";

grant insert on table "public"."user_addresses" to "anon";

grant references on table "public"."user_addresses" to "anon";

grant select on table "public"."user_addresses" to "anon";

grant trigger on table "public"."user_addresses" to "anon";

grant truncate on table "public"."user_addresses" to "anon";

grant update on table "public"."user_addresses" to "anon";

grant delete on table "public"."user_addresses" to "authenticated";

grant insert on table "public"."user_addresses" to "authenticated";

grant references on table "public"."user_addresses" to "authenticated";

grant select on table "public"."user_addresses" to "authenticated";

grant trigger on table "public"."user_addresses" to "authenticated";

grant truncate on table "public"."user_addresses" to "authenticated";

grant update on table "public"."user_addresses" to "authenticated";

grant delete on table "public"."user_addresses" to "service_role";

grant insert on table "public"."user_addresses" to "service_role";

grant references on table "public"."user_addresses" to "service_role";

grant select on table "public"."user_addresses" to "service_role";

grant trigger on table "public"."user_addresses" to "service_role";

grant truncate on table "public"."user_addresses" to "service_role";

grant update on table "public"."user_addresses" to "service_role";

grant delete on table "public"."user_emails" to "anon";

grant insert on table "public"."user_emails" to "anon";

grant references on table "public"."user_emails" to "anon";

grant select on table "public"."user_emails" to "anon";

grant trigger on table "public"."user_emails" to "anon";

grant truncate on table "public"."user_emails" to "anon";

grant update on table "public"."user_emails" to "anon";

grant delete on table "public"."user_emails" to "authenticated";

grant insert on table "public"."user_emails" to "authenticated";

grant references on table "public"."user_emails" to "authenticated";

grant select on table "public"."user_emails" to "authenticated";

grant trigger on table "public"."user_emails" to "authenticated";

grant truncate on table "public"."user_emails" to "authenticated";

grant update on table "public"."user_emails" to "authenticated";

grant delete on table "public"."user_emails" to "service_role";

grant insert on table "public"."user_emails" to "service_role";

grant references on table "public"."user_emails" to "service_role";

grant select on table "public"."user_emails" to "service_role";

grant trigger on table "public"."user_emails" to "service_role";

grant truncate on table "public"."user_emails" to "service_role";

grant update on table "public"."user_emails" to "service_role";

grant delete on table "public"."user_entitlements" to "anon";

grant insert on table "public"."user_entitlements" to "anon";

grant references on table "public"."user_entitlements" to "anon";

grant select on table "public"."user_entitlements" to "anon";

grant trigger on table "public"."user_entitlements" to "anon";

grant truncate on table "public"."user_entitlements" to "anon";

grant update on table "public"."user_entitlements" to "anon";

grant delete on table "public"."user_entitlements" to "authenticated";

grant insert on table "public"."user_entitlements" to "authenticated";

grant references on table "public"."user_entitlements" to "authenticated";

grant select on table "public"."user_entitlements" to "authenticated";

grant trigger on table "public"."user_entitlements" to "authenticated";

grant truncate on table "public"."user_entitlements" to "authenticated";

grant update on table "public"."user_entitlements" to "authenticated";

grant delete on table "public"."user_entitlements" to "service_role";

grant insert on table "public"."user_entitlements" to "service_role";

grant references on table "public"."user_entitlements" to "service_role";

grant select on table "public"."user_entitlements" to "service_role";

grant trigger on table "public"."user_entitlements" to "service_role";

grant truncate on table "public"."user_entitlements" to "service_role";

grant update on table "public"."user_entitlements" to "service_role";

grant delete on table "public"."user_ims" to "anon";

grant insert on table "public"."user_ims" to "anon";

grant references on table "public"."user_ims" to "anon";

grant select on table "public"."user_ims" to "anon";

grant trigger on table "public"."user_ims" to "anon";

grant truncate on table "public"."user_ims" to "anon";

grant update on table "public"."user_ims" to "anon";

grant delete on table "public"."user_ims" to "authenticated";

grant insert on table "public"."user_ims" to "authenticated";

grant references on table "public"."user_ims" to "authenticated";

grant select on table "public"."user_ims" to "authenticated";

grant trigger on table "public"."user_ims" to "authenticated";

grant truncate on table "public"."user_ims" to "authenticated";

grant update on table "public"."user_ims" to "authenticated";

grant delete on table "public"."user_ims" to "service_role";

grant insert on table "public"."user_ims" to "service_role";

grant references on table "public"."user_ims" to "service_role";

grant select on table "public"."user_ims" to "service_role";

grant trigger on table "public"."user_ims" to "service_role";

grant truncate on table "public"."user_ims" to "service_role";

grant update on table "public"."user_ims" to "service_role";

grant delete on table "public"."user_phone_numbers" to "anon";

grant insert on table "public"."user_phone_numbers" to "anon";

grant references on table "public"."user_phone_numbers" to "anon";

grant select on table "public"."user_phone_numbers" to "anon";

grant trigger on table "public"."user_phone_numbers" to "anon";

grant truncate on table "public"."user_phone_numbers" to "anon";

grant update on table "public"."user_phone_numbers" to "anon";

grant delete on table "public"."user_phone_numbers" to "authenticated";

grant insert on table "public"."user_phone_numbers" to "authenticated";

grant references on table "public"."user_phone_numbers" to "authenticated";

grant select on table "public"."user_phone_numbers" to "authenticated";

grant trigger on table "public"."user_phone_numbers" to "authenticated";

grant truncate on table "public"."user_phone_numbers" to "authenticated";

grant update on table "public"."user_phone_numbers" to "authenticated";

grant delete on table "public"."user_phone_numbers" to "service_role";

grant insert on table "public"."user_phone_numbers" to "service_role";

grant references on table "public"."user_phone_numbers" to "service_role";

grant select on table "public"."user_phone_numbers" to "service_role";

grant trigger on table "public"."user_phone_numbers" to "service_role";

grant truncate on table "public"."user_phone_numbers" to "service_role";

grant update on table "public"."user_phone_numbers" to "service_role";

grant delete on table "public"."user_photos" to "anon";

grant insert on table "public"."user_photos" to "anon";

grant references on table "public"."user_photos" to "anon";

grant select on table "public"."user_photos" to "anon";

grant trigger on table "public"."user_photos" to "anon";

grant truncate on table "public"."user_photos" to "anon";

grant update on table "public"."user_photos" to "anon";

grant delete on table "public"."user_photos" to "authenticated";

grant insert on table "public"."user_photos" to "authenticated";

grant references on table "public"."user_photos" to "authenticated";

grant select on table "public"."user_photos" to "authenticated";

grant trigger on table "public"."user_photos" to "authenticated";

grant truncate on table "public"."user_photos" to "authenticated";

grant update on table "public"."user_photos" to "authenticated";

grant delete on table "public"."user_photos" to "service_role";

grant insert on table "public"."user_photos" to "service_role";

grant references on table "public"."user_photos" to "service_role";

grant select on table "public"."user_photos" to "service_role";

grant trigger on table "public"."user_photos" to "service_role";

grant truncate on table "public"."user_photos" to "service_role";

grant update on table "public"."user_photos" to "service_role";

grant delete on table "public"."user_roles" to "anon";

grant insert on table "public"."user_roles" to "anon";

grant references on table "public"."user_roles" to "anon";

grant select on table "public"."user_roles" to "anon";

grant trigger on table "public"."user_roles" to "anon";

grant truncate on table "public"."user_roles" to "anon";

grant update on table "public"."user_roles" to "anon";

grant delete on table "public"."user_roles" to "authenticated";

grant insert on table "public"."user_roles" to "authenticated";

grant references on table "public"."user_roles" to "authenticated";

grant select on table "public"."user_roles" to "authenticated";

grant trigger on table "public"."user_roles" to "authenticated";

grant truncate on table "public"."user_roles" to "authenticated";

grant update on table "public"."user_roles" to "authenticated";

grant delete on table "public"."user_roles" to "service_role";

grant insert on table "public"."user_roles" to "service_role";

grant references on table "public"."user_roles" to "service_role";

grant select on table "public"."user_roles" to "service_role";

grant trigger on table "public"."user_roles" to "service_role";

grant truncate on table "public"."user_roles" to "service_role";

grant update on table "public"."user_roles" to "service_role";

grant delete on table "public"."user_x509_certificates" to "anon";

grant insert on table "public"."user_x509_certificates" to "anon";

grant references on table "public"."user_x509_certificates" to "anon";

grant select on table "public"."user_x509_certificates" to "anon";

grant trigger on table "public"."user_x509_certificates" to "anon";

grant truncate on table "public"."user_x509_certificates" to "anon";

grant update on table "public"."user_x509_certificates" to "anon";

grant delete on table "public"."user_x509_certificates" to "authenticated";

grant insert on table "public"."user_x509_certificates" to "authenticated";

grant references on table "public"."user_x509_certificates" to "authenticated";

grant select on table "public"."user_x509_certificates" to "authenticated";

grant trigger on table "public"."user_x509_certificates" to "authenticated";

grant truncate on table "public"."user_x509_certificates" to "authenticated";

grant update on table "public"."user_x509_certificates" to "authenticated";

grant delete on table "public"."user_x509_certificates" to "service_role";

grant insert on table "public"."user_x509_certificates" to "service_role";

grant references on table "public"."user_x509_certificates" to "service_role";

grant select on table "public"."user_x509_certificates" to "service_role";

grant trigger on table "public"."user_x509_certificates" to "service_role";

grant truncate on table "public"."user_x509_certificates" to "service_role";

grant update on table "public"."user_x509_certificates" to "service_role";

grant delete on table "public"."users" to "anon";

grant insert on table "public"."users" to "anon";

grant references on table "public"."users" to "anon";

grant select on table "public"."users" to "anon";

grant trigger on table "public"."users" to "anon";

grant truncate on table "public"."users" to "anon";

grant update on table "public"."users" to "anon";

grant delete on table "public"."users" to "authenticated";

grant insert on table "public"."users" to "authenticated";

grant references on table "public"."users" to "authenticated";

grant select on table "public"."users" to "authenticated";

grant trigger on table "public"."users" to "authenticated";

grant truncate on table "public"."users" to "authenticated";

grant update on table "public"."users" to "authenticated";

grant delete on table "public"."users" to "service_role";

grant insert on table "public"."users" to "service_role";

grant references on table "public"."users" to "service_role";

grant select on table "public"."users" to "service_role";

grant trigger on table "public"."users" to "service_role";

grant truncate on table "public"."users" to "service_role";

grant update on table "public"."users" to "service_role";

CREATE TRIGGER update_applications_modified_at BEFORE UPDATE ON public.applications FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_group_on_member_change AFTER INSERT OR DELETE OR UPDATE ON public.group_members FOR EACH ROW EXECUTE FUNCTION update_group_modified_on_member_change();

CREATE TRIGGER generate_groups_etag BEFORE INSERT OR UPDATE ON public.groups FOR EACH ROW EXECUTE FUNCTION generate_etag();

CREATE TRIGGER update_groups_modified BEFORE UPDATE ON public.groups FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_tenants_modified_at BEFORE UPDATE ON public.tenants FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER generate_users_etag BEFORE INSERT OR UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION generate_etag();

CREATE TRIGGER update_users_modified BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION update_modified_column();


