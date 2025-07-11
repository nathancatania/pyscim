import asyncio
from typing import Optional
import click
from rich.console import Console
from rich.table import Table
from tortoise import Tortoise
from scim.config import settings
from scim.services import ApplicationService, TenantService

console = Console()


async def init_db():
    await Tortoise.init(config=settings.tortoise_orm_config)
    await Tortoise.generate_schemas()


async def close_db():
    await Tortoise.close_connections()


@click.group()
def app_group():
    """Manage SCIM applications"""
    pass


@app_group.command()
@click.option('--name', '-n', required=True, help='Unique name for the application (e.g., "entra-prod")')
@click.option('--display-name', '-d', help='Display name (e.g., "Entra ID Production"), defaults to name')
@click.option('--description', help='Description of the application')
@click.option('--external-id', help='External identifier for the application')
@click.option('--tenant', '-t', default='default', help='Tenant to create the application in (default: default)')
def create(name: str, display_name: Optional[str], description: Optional[str], external_id: Optional[str], tenant: str):
    """Create a new SCIM application."""
    
    async def _create():
        await init_db()
        
        try:
            # Get or create tenant
            if tenant == 'default':
                tenant_obj = await TenantService.get_or_create_default_tenant()
            else:
                try:
                    tenant_obj = await TenantService.get_tenant_by_name(tenant)
                except:
                    console.print(f"[red]Tenant '{tenant}' not found.[/red]")
                    return
            
            # Use name as display_name if not provided
            if not display_name:
                display_name = name
            
            # Create application
            app = await ApplicationService.create_application(
                tenant_id=str(tenant_obj.id),
                name=name,
                display_name=display_name,
                description=description,
                external_id=external_id,
                metadata={
                    "created_via": "cli",
                }
            )
            
            console.print(f"\n[green]✓ Application created successfully![/green]\n")
            console.print(f"[bold]Application ID:[/bold] {app.id}")
            console.print(f"[bold]Name:[/bold] {app.name}")
            console.print(f"[bold]Display Name:[/bold] {app.display_name}")
            console.print(f"[bold]Tenant:[/bold] {tenant}")
            if description:
                console.print(f"[bold]Description:[/bold] {description}")
            if external_id:
                console.print(f"[bold]External ID:[/bold] {external_id}")
            
            console.print(f"\n[dim]Use 'pyscim token create --app {name}' to create API tokens for this application.[/dim]")
            
        except Exception as e:
            console.print(f"[red]Error creating application: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_create())


@app_group.command()
@click.option('--tenant', '-t', help='Filter applications by tenant')
@click.option('--active-only/--all', default=True, help='Show only active applications or all')
def list(tenant: Optional[str], active_only: bool):
    """List all applications."""
    
    async def _list():
        await init_db()
        
        try:
            # Get tenant ID if specified
            tenant_id = None
            if tenant:
                tenant_obj = await TenantService.get_tenant_by_name(tenant)
                if not tenant_obj:
                    console.print(f"[yellow]Tenant '{tenant}' not found.[/yellow]")
                    return
                tenant_id = str(tenant_obj.id)
            
            # List applications
            apps, total = await ApplicationService.list_applications(
                tenant_id=tenant_id,
                active_only=active_only
            )
            
            if not apps:
                console.print("[yellow]No applications found.[/yellow]")
                return
            
            # Create table
            title = "Applications"
            if tenant:
                title += f" for Tenant: {tenant}"
            
            table = Table(title=title)
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Display Name")
            table.add_column("Tenant", style="blue")
            table.add_column("Active", style="green")
            table.add_column("Created", style="yellow")
            table.add_column("Description")
            
            for app in apps:
                table.add_row(
                    str(app.id)[:8],
                    app.name,
                    app.display_name,
                    app.tenant.name if hasattr(app, 'tenant') and app.tenant else "Unknown",
                    "✓" if app.active else "✗",
                    app.created_at.strftime("%Y-%m-%d") if app.created_at else "",
                    (app.description[:30] + "...") if app.description and len(app.description) > 30 else app.description or ""
                )
            
            console.print(table)
            console.print(f"\n[dim]Total: {total} applications[/dim]")
            
        except Exception as e:
            console.print(f"[red]Error listing applications: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_list())


@app_group.command()
@click.argument('app_identifier')
def info(app_identifier: str):
    """Show detailed information about an application."""
    
    async def _info():
        await init_db()
        
        try:
            # Try to find by ID or name
            app = None
            try:
                # First try as ID
                app = await ApplicationService.get_application(app_identifier)
            except:
                # Try by name across all tenants (case-insensitive)
                app = await ApplicationService.get_application_by_name_case_insensitive(None, app_identifier)
                
            if not app:
                console.print(f"[red]Application '{app_identifier}' not found.[/red]")
                return
            
            # Get stats
            stats = await ApplicationService.get_application_stats(str(app.id))
            
            # Display info
            console.print("\n[bold]Application Information[/bold]\n")
            console.print(f"[bold]ID:[/bold] {app.id}")
            console.print(f"[bold]Name:[/bold] {app.name}")
            console.print(f"[bold]Display Name:[/bold] {app.display_name}")
            console.print(f"[bold]Tenant:[/bold] {app.tenant.name if hasattr(app, 'tenant') and app.tenant else 'Unknown'}")
            console.print(f"[bold]Active:[/bold] {'Yes' if app.active else 'No'}")
            console.print(f"[bold]Description:[/bold] {app.description or 'N/A'}")
            console.print(f"[bold]External ID:[/bold] {app.external_id or 'N/A'}")
            console.print(f"[bold]Created:[/bold] {app.created_at.isoformat() if app.created_at else 'Unknown'}")
            console.print(f"[bold]Modified:[/bold] {app.modified_at.isoformat() if app.modified_at else 'Unknown'}")
            
            console.print("\n[bold]Resource Statistics[/bold]\n")
            console.print(f"[bold]Users:[/bold] {stats['users_count']}")
            console.print(f"[bold]Groups:[/bold] {stats['groups_count']}")
            console.print(f"[bold]API Tokens:[/bold] {stats['api_tokens_count']} ({stats['active_tokens_count']} active)")
            console.print(f"[bold]Audit Events:[/bold] {stats['recent_activity_count']}")
            
            if app.settings:
                console.print("\n[bold]Settings:[/bold]")
                for key, value in app.settings.items():
                    console.print(f"  {key}: {value}")
            
            if app.metadata:
                console.print("\n[bold]Metadata:[/bold]")
                for key, value in app.metadata.items():
                    console.print(f"  {key}: {value}")
            
        except Exception as e:
            console.print(f"[red]Error getting application info: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_info())


@app_group.command()
@click.argument('app_identifier')
@click.option('--display-name', '-d', help='New display name')
@click.option('--description', help='New description')
@click.option('--external-id', help='New external ID')
@click.option('--active/--inactive', help='Set active status')
def update(app_identifier: str, display_name: Optional[str], description: Optional[str], 
          external_id: Optional[str], active: Optional[bool]):
    """Update an application's properties."""
    
    async def _update():
        await init_db()
        
        try:
            # Try to find by ID or name
            app = None
            try:
                # First try as ID
                app = await ApplicationService.get_application(app_identifier)
            except:
                # Try by name across all tenants
                app = await ApplicationService.get_application_by_name_case_insensitive(None, app_identifier)
                
            if not app:
                console.print(f"[red]Application '{app_identifier}' not found.[/red]")
                return
            
            # Update application
            updated_app = await ApplicationService.update_application(
                app_id=str(app.id),
                display_name=display_name,
                description=description,
                external_id=external_id,
                active=active
            )
            
            console.print(f"[green]✓ Application '{updated_app.name}' updated successfully![/green]")
            
        except Exception as e:
            console.print(f"[red]Error updating application: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_update())


@app_group.command()
@click.argument('app_identifier')
@click.confirmation_option(prompt='This will DELETE all associated users, groups, and tokens. Are you sure?')
def delete(app_identifier: str):
    """Delete an application and all its resources."""
    
    async def _delete():
        await init_db()
        
        try:
            # Try to find by ID or name
            app = None
            try:
                # First try as ID
                app = await ApplicationService.get_application(app_identifier)
            except:
                # Try by name across all tenants
                app = await ApplicationService.get_application_by_name_case_insensitive(None, app_identifier)
                
            if not app:
                console.print(f"[red]Application '{app_identifier}' not found.[/red]")
                return
            
            # Get stats before deletion
            stats = await ApplicationService.get_application_stats(str(app.id))
            
            # Show what will be deleted
            console.print("\n[yellow]Warning: The following will be deleted:[/yellow]")
            console.print(f"  - {stats['users_count']} users")
            console.print(f"  - {stats['groups_count']} groups")
            console.print(f"  - {stats['api_tokens_count']} API tokens")
            console.print(f"  - {stats['recent_activity_count']} audit events")
            
            # Delete application
            await ApplicationService.delete_application(str(app.id))
            
            console.print(f"\n[green]✓ Application '{app.name}' and all associated resources have been deleted.[/green]")
            
        except Exception as e:
            console.print(f"[red]Error deleting application: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_delete())


@app_group.command()
@click.argument('app_identifier')
def deactivate(app_identifier: str):
    """Deactivate an application without deleting it."""
    
    async def _deactivate():
        await init_db()
        
        try:
            # Try to find by ID or name
            app = None
            try:
                # First try as ID
                app = await ApplicationService.get_application(app_identifier)
            except:
                # Try by name across all tenants
                app = await ApplicationService.get_application_by_name_case_insensitive(None, app_identifier)
                
            if not app:
                console.print(f"[red]Application '{app_identifier}' not found.[/red]")
                return
            
            # Deactivate application
            updated_app = await ApplicationService.deactivate_application(str(app.id))
            
            console.print(f"[green]✓ Application '{updated_app.name}' has been deactivated.[/green]")
            console.print("\n[dim]Note: Existing API tokens will continue to work. Deactivation prevents new resources from being created.[/dim]")
            
        except Exception as e:
            console.print(f"[red]Error deactivating application: {e}[/red]")
        finally:
            await close_db()
    
    asyncio.run(_deactivate())