import asyncio
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import click
from rich.console import Console
from rich.table import Table
from tortoise import Tortoise
from scim.config import settings
from scim.models import APIToken, Application
from scim.services import ApplicationService

console = Console()


async def init_db():
    await Tortoise.init(config=settings.tortoise_orm_config)
    await Tortoise.generate_schemas()


async def close_db():
    await Tortoise.close_connections()


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """Generate SHA-256 hash of the token."""
    return hashlib.sha256(token.encode()).hexdigest()


async def get_or_create_default_app(tenant_id: str = "00000000-0000-0000-0000-000000000001") -> Application:
    """Get or create the default application."""
    app = await ApplicationService.get_or_create_default_application(tenant_id)
    return app


@click.group()
def tokens_group():
    """Manage SCIM API tokens"""
    pass


@tokens_group.command()
@click.option('--name', '-n', required=True, help='Name for the token (e.g., "Azure AD", "Okta")')
@click.option('--description', '-d', help='Description of the token usage')
@click.option('--expires-days', '-e', type=int, help='Number of days until token expires')
@click.option('--scopes', '-s', help='Comma-separated token scopes (default: scim:read,scim:write)')
@click.option('--app', '-a', help='Application to associate the token with (name or ID, default: default)')
def create(name: str, description: Optional[str], expires_days: Optional[int], scopes: Optional[str], app: Optional[str]):
    """Create a new API token for SCIM authentication."""
    
    async def _create():
        await init_db()
        
        try:
            # If no app specified, use default
            app_to_use = app if app else "default"
            
            # Find application by name or ID (case-insensitive)
            app_obj = None
            try:
                # Try as ID first
                app_obj = await ApplicationService.get_application(app_to_use)
            except:
                # Try by name (case-insensitive)
                from scim.models import Application as AppModel
                app_obj = await AppModel.filter(name__iexact=app_to_use).first()
            
            if not app_obj:
                # Auto-create the application
                from scim.services import TenantService
                default_tenant = await TenantService.get_or_create_default_tenant()
                
                console.print(f"[yellow]Application '{app_to_use}' not found. Creating it...[/yellow]")
                
                try:
                    app_obj = await ApplicationService.create_application(
                        tenant_id=str(default_tenant.id),
                        name=app_to_use.lower(),  # Store app names in lowercase for consistency
                        display_name=app_to_use,
                        description=f"Auto-created application for {app_to_use}",
                        metadata={
                            "created_via": "auto_created_by_token_cli",
                            "created_at": datetime.utcnow().isoformat()
                        }
                    )
                    console.print(f"[green]✓ Created application '{app_to_use}'[/green]")
                except Exception as e:
                    console.print(f"[red]Failed to create application: {e}[/red]")
                    return
            
            # Generate token
            raw_token = generate_secure_token()
            token_hash = hash_token(raw_token)
            
            # Calculate expiration
            expires_at = None
            if expires_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_days)
            
            # Parse scopes from comma-separated string or use defaults
            if scopes:
                token_scopes = [s.strip() for s in scopes.split(',')]
            else:
                token_scopes = ['scim:read', 'scim:write']
            
            # Create token record
            api_token = await APIToken.create(
                name=name,
                token_hash=token_hash,
                description=description,
                scopes=token_scopes,
                expires_at=expires_at,
                created_by="CLI",
                app=app_obj,
                metadata={
                    "created_via": "manage_tokens_cli",
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            # Display success message with token
            console.print("\n[green]✓ API Token created successfully![/green]\n")
            console.print(f"[bold]Token Name:[/bold] {name}")
            console.print(f"[bold]Token ID:[/bold] {api_token.id}")
            console.print(f"[bold]Application:[/bold] {app_obj.display_name} ({app_obj.name})")
            console.print(f"[bold]Scopes:[/bold] {', '.join(token_scopes)}")
            if expires_at:
                console.print(f"[bold]Expires:[/bold] {expires_at.isoformat()}")
            
            console.print("\n[yellow]⚠️  IMPORTANT: Save this token securely. It will not be shown again![/yellow]\n")
            console.print(f"[bold red]Token:[/bold red] {raw_token}\n")
            
            console.print("[dim]Use this token in the Authorization header:[/dim]")
            console.print(f"[dim]Authorization: Bearer {raw_token}[/dim]\n")
            
        except Exception as e:
            console.print(f"[red]Error creating token: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_create())


@tokens_group.command()
@click.option('--active-only/--all', default=True, help='Show only active tokens or all tokens')
@click.option('--app', '-a', help='Filter tokens by application (name or ID)')
@click.option('--all-apps', is_flag=True, help='Show tokens for all applications')
def list(active_only: bool, app: Optional[str], all_apps: bool):
    """List all API tokens."""
    
    async def _list():
        await init_db()
        
        try:
            # Handle app filtering
            if not all_apps and not app:
                console.print("[yellow]Please specify --app or --all-apps[/yellow]")
                return
            
            query = APIToken.all()
            
            if app:
                # Find application
                app_obj = None
                try:
                    app_obj = await ApplicationService.get_application(app)
                except:
                    # Try by name (case-insensitive)
                    app_obj = await ApplicationService.get_application_by_name_case_insensitive(None, app)
                
                if not app_obj:
                    console.print(f"[yellow]Application '{app}' not found.[/yellow]")
                    return
                
                query = APIToken.filter(app=app_obj)
            if active_only:
                query = query.filter(active=True)
            
            tokens = await query.prefetch_related('app', 'app__tenant').order_by('-created_at')
            
            if not tokens:
                console.print("[yellow]No tokens found.[/yellow]")
                return
            
            # Create table
            title = "API Tokens"
            if app and not all_apps:
                title = f"API Tokens for {app_obj.display_name}"
            
            table = Table(title=title)
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Application", style="blue")
            table.add_column("Description")
            table.add_column("Active", style="green")
            table.add_column("Created", style="yellow")
            table.add_column("Last Used")
            table.add_column("Expires")
            
            for token in tokens:
                table.add_row(
                    str(token.id)[:8],
                    token.name,
                    token.app.name if hasattr(token, 'app') and token.app else "Unknown",
                    token.description or "",
                    "✓" if token.active else "✗",
                    token.created_at.strftime("%Y-%m-%d"),
                    token.last_used_at.strftime("%Y-%m-%d %H:%M") if token.last_used_at else "Never",
                    token.expires_at.strftime("%Y-%m-%d") if token.expires_at else "Never"
                )
            
            console.print(table)
            
            # Add helpful note about partial IDs
            console.print("\n[dim]Tip: You can use the shortened ID (first 8 characters) with 'info' and 'revoke' commands[/dim]")
            
        except Exception as e:
            console.print(f"[red]Error listing tokens: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_list())


@tokens_group.command()
@click.argument('token_id')
@click.confirmation_option(prompt='Are you sure you want to revoke this token?')
def revoke(token_id: str):
    """Revoke an API token."""
    
    async def _revoke():
        await init_db()
        
        try:
            token = None
            
            # First try exact match (if it's a valid UUID)
            try:
                token = await APIToken.filter(id=token_id).prefetch_related('app').first()
            except Exception:
                # If UUID validation fails, we'll use partial matching below
                pass
            
            if not token:
                # Try partial ID match by getting all tokens and filtering in Python
                all_tokens = await APIToken.all().prefetch_related('app')
                matching_tokens = [t for t in all_tokens if str(t.id).startswith(token_id.lower())]
                
                if len(matching_tokens) == 1:
                    token = matching_tokens[0]
                elif len(matching_tokens) > 1:
                    console.print(f"[red]Multiple tokens found starting with '{token_id}'. Please be more specific.[/red]")
                    # Show the matching tokens to help user
                    console.print("\n[yellow]Matching tokens:[/yellow]")
                    for t in matching_tokens:
                        console.print(f"  - {str(t.id)[:8]}... ({t.name})")
                    return
                else:
                    console.print(f"[red]Token '{token_id}' not found.[/red]")
                    return
            
            # Revoke token
            token.active = False
            token.metadata['revoked_at'] = datetime.utcnow().isoformat()
            token.metadata['revoked_via'] = 'manage_tokens_cli'
            await token.save()
            
            console.print(f"[green]✓ Token '{token.name}' (ID: {token.id}) has been revoked.[/green]")
            
        except Exception as e:
            console.print(f"[red]Error revoking token: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_revoke())


@tokens_group.command()
@click.argument('token_id')
def info(token_id: str):
    """Show detailed information about a token."""
    
    async def _info():
        await init_db()
        
        try:
            token = None
            
            # First try exact match (if it's a valid UUID)
            try:
                token = await APIToken.filter(id=token_id).prefetch_related('app').first()
            except Exception:
                # If UUID validation fails, we'll use partial matching below
                pass
            
            if not token:
                # Try partial ID match by getting all tokens and filtering in Python
                all_tokens = await APIToken.all().prefetch_related('app')
                matching_tokens = [t for t in all_tokens if str(t.id).startswith(token_id.lower())]
                
                if len(matching_tokens) == 1:
                    token = matching_tokens[0]
                elif len(matching_tokens) > 1:
                    console.print(f"[red]Multiple tokens found starting with '{token_id}'. Please be more specific.[/red]")
                    # Show the matching tokens to help user
                    console.print("\n[yellow]Matching tokens:[/yellow]")
                    for t in matching_tokens:
                        console.print(f"  - {str(t.id)[:8]}... ({t.name})")
                    return
                else:
                    console.print(f"[red]Token '{token_id}' not found.[/red]")
                    return
            
            # Display token info
            console.print("\n[bold]Token Information[/bold]\n")
            console.print(f"[bold]ID:[/bold] {token.id}")
            console.print(f"[bold]Name:[/bold] {token.name}")
            console.print(f"[bold]Application:[/bold] {token.app.display_name} ({token.app.name})" if hasattr(token, 'app') and token.app else "Unknown")
            console.print(f"[bold]Tenant:[/bold] {token.app.tenant.name if hasattr(token.app, 'tenant') and token.app.tenant else 'Unknown'}")
            console.print(f"[bold]Description:[/bold] {token.description or 'N/A'}")
            console.print(f"[bold]Active:[/bold] {'Yes' if token.active else 'No'}")
            console.print(f"[bold]Scopes:[/bold] {', '.join(token.scopes)}")
            console.print(f"[bold]Created:[/bold] {token.created_at.isoformat()}")
            console.print(f"[bold]Created By:[/bold] {token.created_by or 'Unknown'}")
            console.print(f"[bold]Last Used:[/bold] {token.last_used_at.isoformat() if token.last_used_at else 'Never'}")
            console.print(f"[bold]Expires:[/bold] {token.expires_at.isoformat() if token.expires_at else 'Never'}")
            
            if token.metadata:
                console.print("\n[bold]Metadata:[/bold]")
                for key, value in token.metadata.items():
                    console.print(f"  {key}: {value}")
            
        except Exception as e:
            console.print(f"[red]Error getting token info: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_info())


# Remove main entry point - this will be imported as a subcommand