# PySCIM

An (experimental) standards-compliant SCIM 2.0 server implementation built with FastAPI. Tested with Identity Providers (IdPs) such as Azure AD/Entra ID, Okta, and Jumpcloud.

> [!WARNING]
> PySCIM is experimental. Some components have not been fully tested. Use at your own risk. See [License](#license) below.

## Features

- Full SCIM 2.0 compliance (RFC 7642, 7643, 7644)
- User and Group resource management
- Enterprise User Extension support
- Handles (or rather, attempts to handle) IdP-specific implementations of (or deviations from) the SCIM spec
- API token authentication for machine-to-machine communication
- PostgreSQL database storage (via Supabase or standalone Postgres)
- ETag support for optimistic concurrency control
- Pagination, filtering, and sorting (filter parser pending)
- Multi-tenancy support
- App segmentation support: Sync directory data from different sources independently in the one tenant.

## Tested IdPs
- ✅ Azure AD / Entra ID
- ✅ Okta
- ✅ Jumpcloud
- ✅ Ping
- ✅ OneLogin

Vendor specific 'quirks' handled:
- OneLogin non-standard SCIM Schema representations, e.g. `urn:scim:schemas:extension:enterprise:2.0` instead of `urn:ietf:params:scim:schemas:extension:enterprise:2.0:User`
- Okta sending the field value and not the SCIM ID when referencing other identities (e.g. manager value, group value)

## Installation (Local Testing)

This will use (all free):
- A local deploy of Supabase on your machine for the DB (using Docker or Orbstack)
- Ngrok to allow the PySCIM server running on your machine to be reached by the IdP (Entra ID, Okta, etc)

### Prerequisites
- Homebrew [[install here](https://brew.sh/)] (this guide assumes you are using macOS - change out the `brew` commands accordingly)
- uv package manager [[install here](https://docs.astral.sh/uv/getting-started/installation/#homebrew)]

### 1. Clone this Repo
```
git clone https://github.com/nathancatania/pyscim.git
```

### 2. Setup & Install Ngrok
1. Create a free Ngrok account: [ngrok.com](https://ngrok.com/)
2. Install Ngrok:
   ```bash
   brew install ngrok
   ```
3. Note down the auth token in the setup page of your Ngrok account and run the command:
   ```bash
   ngrok config add-authtoken <your_token>
   ```
4. Run Ngrok:
   ```bash
   ngrok http 8000
   ```
5. Note down the **Forwarding** URL shown, e.g. `https://eaf25b57c8e1.ngrok-free.app`
   * This will make the PySCIM server, which runs on `localhost` port `8000` available at the URL listed.
   * The SCIM server URL you give to you IdP (Entra ID, Okta, etc) will be this URL followed by `/scim/v2`, e.g. `https://eaf25b57c8e1.ngrok-free.app/scim/v2`
   * The domain changes each time Ngrok is restarted. Your free account will have a static domain associated with it that you can find in the Ngrok dashboard, e.g. `ngrok http --url=sculpin-blue-gorilla.ngrok-free.app 8000`

### 3. Setup & Install Supabase
1. Install Orbstack (not needed if you already have Docker):
   ```bash
   brew install orbstack
   ```
2. Install the Supabase CLI:
   ```bash
   brew install supabase
   ```
3. Start Supabase & the DB:
   ```bash
   supabase start
   ```
4. Note down the **DB URL** shown on screen, e.g. `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
5. Apply the DB migrations to setup all the tables (you only need to do this once):
   ```bash
   supabase db reset
   ```

Your Postgres DB will now be running using Supabase.

> [!NOTE]
> If you would like to use your own Postgres DB, you can copy and use the migrations file in the `supabase/migrations` directory and apply it to your preferred method.

### 4. Setup & Install PySCIM
1. Copy `.env.example` to `.env`.
   * If you are using Supabase as above, the existing DB URL should work for you as-is. There should be nothing left for you to modify.
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Create an API / SCIM Bearer Token (or whatever you want your token to be called):
   ```bash
   # Create an API token with the name 'okta'
   uv run pyscim token create --name "okta"

   # Alternative: Create an API token scoped to an app called 'okta'
   uv run pyscim token create --name "okta" --app "okta"

   # You can have different apps that isolate the data synced to them
   uv run pyscim token create --name "okta" --app "okta"
   uv run pyscim token create --name "okta2" --app "okta2"
   uv run pyscim token create --name "entraid" --app "entraid"
   ```
4. Copy the token displayed on screen: **It will not be shown again!**
5. Run the PySCIM server:
   ```bash
   # Development mode (with auto-reload)
   uv run pyscim run dev

   # Production mode
   uv run pyscim run prod --workers 4

   # Custom host/port
   uv run pyscim run dev --host 127.0.0.1 --port 3000
   ```

The server will start on `http://localhost:8000` by default.

### 5. Configure your IdP(s)
Instructions will vary for each IdP, however you will need the following:

|                   |                                                                                                                               |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| SCIM Server URL   | This is the Ngrok forwarding URL generated with `/scim/v2` appended to it. E.g. `https://eaf25b57c8e1.ngrok-free.app/scim/v2` |
| SCIM Bearer Token | This is the API token generated with the `uv run pyscim token create --name "tokenname"` command                              |

Most IdPs have a "test connection" button. You will know if everything is setup correctly if you see a HTTP request in the Ngrok terminal window, and if the terminal window running PySCIM shows the request was received.

```
INFO     → GET /scim/v2/Users from 13.54.131.18
INFO     Listing users (filter: username Eq "id", sort: (None, 'ascending'))
DEBUG    ListResponse: {                                                                                                               
 "schemas": [
   "urn:ietf:params:scim:api:messages:2.0:ListResponse"
 ],
 "total_results": 0,
 "Resources": [],
 "start_index": 1,
 "items_per_page": 0
}
INFO     ← 200 GET /scim/v2/Users (0.107s)
```

### API Documentation

When running in development mode, you can access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Authentication

PyScim uses Bearer token authentication with a hierarchical multi-tenant architecture designed for enterprise scenarios.

### Architecture Overview

The authentication system has three key components:

1. **Tenants**: Top-level organizational units that provide complete data isolation between different organizations
2. **Applications**: Represent different identity providers (IdPs), or IdP tenancies, within a PySCIM tenant (e.g., Okta, Azure AD/Entra ID)
3. **API Tokens**: Bearer tokens scoped to specific applications for API authentication

### How It Works

- **API Tokens** are tied to a specific **Application**
- **Applications** belong to a specific **Tenant**
- All SCIM operations (users, groups) are automatically scoped to the application identified by the API token

This design enables:
- **Multiple IdPs per tenant**: Sync data from different identity providers (e.g., both Okta and Entra ID) without conflicts
- **Multi-tenancy**: Host multiple organizations on the same PyScim instance with complete data isolation
- **Multiple tokens per app**: Issue multiple API tokens for the same application (useful for rotation, different environments)

> [!WARNING]
> Multi-tenancy support is experimental and not well tested. Use at your own risk.

### Example Use Cases

1. **Aggregating Multiple IdPs**: A company using both Okta and Azure AD can create separate applications for each, preventing user ID conflicts
2. **Development/Production Separation**: Create separate applications like "okta-dev" and "okta-prod" with different tokens
3. **Multi-tenant SaaS**: Different companies can use the same SCIM server with complete data isolation

### Managing Tenants, Applications, and Tokens

You don't need to create an app or tenant if you don't want to. If nothing is specified, a special "default" app and tenancy is used.

#### Managing API Tokens

1. **Create a token** for an application:
   ```bash
   # Create token for default application
   uv run pyscim token create --name "entraid"

   # Create a token with a description
   uv run pyscim token create --name "entraid" --description "Token for Entra ID SCIM provisioning"
   
   # Create token for specific application
   uv run pyscim token create --name "Okta Prod Token" --app "okta-prod" --expires-days 365
   ```

   If the app name specified does not exist, it will be created.
   
   **Important**: Save the generated token immediately - it won't be shown again!

2. **List tokens**:
   ```bash
   # All active tokens
   uv run pyscim token list
   
   # Tokens for a specific application
   uv run pyscim token list --app "okta-prod"
   
   # All tokens including revoked ones
   uv run pyscim token list --all
   ```

3. **View token details**:
   ```bash
   uv run pyscim token info <token-id>
   ```

4. **Revoke a token**:
   ```bash
   uv run pyscim token revoke <token-id>
   ```

#### Managing Applications

1. **Create an application** within a tenant:
   ```bash
   # For the default tenant
   uv run pyscim app create --name "okta-prod" --display-name "Okta Production"
   
   # For a specific tenant
   uv run pyscim app create --name "entra-dev" --display-name "Entra ID Development" --tenant "acme-corp"
   ```

2. **List applications**:
   ```bash
   # All applications across all tenants
   uv run pyscim app list
   
   # Applications in a specific tenant
   uv run pyscim app list --tenant "acme-corp"
   ```

3. **View application details**:
   ```bash
   uv run pyscim app info <app-name-or-id>
   ```

4. **Update an application**:
   ```bash
   uv run pyscim app update <app-name-or-id> --description "Production Okta instance"
   ```

5. **Deactivate/Delete an application**:
   ```bash
   # Deactivate (preserves data)
   uv run pyscim app deactivate <app-name-or-id>
   
   # Delete (removes all data)
   uv run pyscim app delete <app-name-or-id>
   ```

#### Managing Tenants

1. **Create a tenant**:
   ```bash
   uv run pyscim tenant create --name "acme-corp" --display-name "ACME Corporation"
   ```

2. **List all tenants**:
   ```bash
   uv run pyscim tenant list
   ```

3. **View tenant details**:
   ```bash
   uv run pyscim tenant info <tenant-name-or-id>
   ```

4. **Update a tenant**:
   ```bash
   uv run pyscim tenant update <tenant-name-or-id> --display-name "New Display Name"
   ```

5. **Delete a tenant** (WARNING: Deletes all associated data):
   ```bash
   uv run pyscim tenant delete <tenant-name-or-id> --force
   ```

### Configuring Identity Providers

When setting up SCIM provisioning in your identity provider:

1. **SCIM Base URL**: 
   ```
   https://your-domain.com/scim/v2
   ```

2. **Authentication**: 
   - Method: Bearer Token
   - Token: The token generated using the CLI tool

3. **Example for Azure AD / Entra ID**:
   - Tenant URL: `https://your-domain.com/scim/v2`
   - Secret Token: `<your-generated-token>`

4. **Example for Okta**:
   - SCIM connector base URL: `https://your-domain.com/scim/v2`
   - Unique identifier field for users: `email`
   - Authentication mode: HTTP Header
   - Authorization: `Bearer <your-generated-token>`

### Security Notes

- Tokens are stored as SHA-256 hashes in the database
- Use HTTPS in production to protect tokens in transit
- Set token expiration dates for enhanced security
- Regularly rotate tokens
- Monitor token usage via the audit logs

## Project Structure

```
src/scim/
📁 api/v2/          # API endpoints
📁 models/          # Tortoise ORM models
📁 schemas/         # Pydantic schemas
📁 services/        # Business logic
📁 middleware/      # Authentication and error handling
📁 utils/           # Utilities (logging, pagination, etc.)
📄 config.py        # Application configuration
📄 dependencies.py  # FastAPI dependencies
📄 exceptions.py    # Custom exceptions
📄 main.py          # Application entry point
```

## Configuration

Key configuration options in `.env`:

- `DATABASE_URL`: PostgreSQL connection string

## CLI Commands

PyScim provides a comprehensive CLI for managing your SCIM server:

```bash
# Show available commands
uv run pyscim --help

# Server management
uv run pyscim run dev                    # Run development server
uv run pyscim run prod                   # Run production server

# Configuration
uv run pyscim config                     # Show current configuration
uv run pyscim config --show-values       # Show all config values

# Tenant management
uv run pyscim tenant create              # Create new tenant
uv run pyscim tenant list                # List all tenants
uv run pyscim tenant info <id>           # Show tenant details
uv run pyscim tenant update <id>         # Update tenant
uv run pyscim tenant delete <id>         # Delete tenant

# Application management
uv run pyscim app create                 # Create new application
uv run pyscim app list                   # List all applications
uv run pyscim app info <id>              # Show application details
uv run pyscim app update <id>            # Update application
uv run pyscim app delete <id>            # Delete application

# Token management
uv run pyscim token create               # Create new API token
uv run pyscim token list                 # List all tokens
uv run pyscim token info <id>            # Show token details
uv run pyscim token revoke <id>          # Revoke a token

# Database
uv run pyscim db init                    # Initialize database
uv run pyscim db status                  # Check database connection
```

## Development

### Running Tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
```

### Type Checking

```bash
uv run mypy src
```

## Known Issues

- See [TODO.md](TODO.md)

## License

- See [LICENSE](LICENSE)

In short:
* You use all code in this repo at your own risk.
* There is no support or warranty of any kind.
* PySCIM is EXPERIMENTAL. Some things may not work or may not be fully secure. You should always examine and test the code yourself.
* If you use PySCIM and it somehow deletes all of your company's data, burns down your house, and nukes your dog from orbit - it'll be your own fault. That being said, I don't recall programming it to do this... 🤷‍♂️
* You can do what you want with this code (as long as it adheres to LICENSE.md); just give some acknowledgement/attribution if you do.
