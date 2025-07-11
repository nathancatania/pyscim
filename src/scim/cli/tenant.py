import asyncio
from typing import Optional
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from tortoise import Tortoise

from ..config import settings
from ..services import TenantService
from ..exceptions import ResourceAlreadyExists, ResourceNotFound, InvalidSyntax
from ..utils import logger


console = Console()


async def init_db():
    """Initialize database connection for CLI commands."""
    await Tortoise.init(
        db_url=settings.database_url,
        modules={"models": ["scim.models"]}
    )


async def close_db():
    """Close database connection."""
    await Tortoise.close_connections()


def async_command(f):
    """Decorator to run async commands."""
    def wrapper(*args, **kwargs):
        async def run():
            try:
                await init_db()
                return await f(*args, **kwargs)
            finally:
                await close_db()
        
        return asyncio.run(run())
    
    return wrapper


@click.group("tenant")
def tenant_cli():
    """Manage tenants."""
    pass


@tenant_cli.command("create")
@click.option("--name", "-n", required=True, help="Unique tenant identifier (e.g., 'acme-corp')")
@click.option("--display-name", "-d", required=True, help="Human-readable name (e.g., 'Acme Corporation')")
@click.option("--external-id", "-e", help="External system identifier")
@async_command
async def create_tenant(name: str, display_name: str, external_id: Optional[str]):
    """Create a new tenant."""
    try:
        tenant = await TenantService.create_tenant(
            name=name,
            display_name=display_name,
            external_id=external_id
        )
        
        console.print(Panel(
            f"[green]✓[/green] Tenant created successfully!\n\n"
            f"[bold]ID:[/bold] {tenant.id}\n"
            f"[bold]Name:[/bold] {tenant.name}\n"
            f"[bold]Display Name:[/bold] {tenant.display_name}\n"
            f"[bold]External ID:[/bold] {tenant.external_id or 'None'}",
            title="Tenant Created",
            border_style="green"
        ))
        
    except ResourceAlreadyExists as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise click.Abort()
    except InvalidSyntax as e:
        console.print(f"[red]✗[/red] Validation Error: {str(e)}")
        raise click.Abort()


@tenant_cli.command("list")
@click.option("--all", "-a", is_flag=True, help="Show all tenants including inactive ones")
@click.option("--limit", "-l", default=100, help="Maximum number of results")
@async_command
async def list_tenants(all: bool, limit: int):
    """List all tenants."""
    tenants = await TenantService.list_tenants(
        active_only=not all,
        limit=limit
    )
    
    if not tenants:
        console.print("[yellow]No tenants found.[/yellow]")
        return
    
    table = Table(title="Tenants", show_lines=True)
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Display Name")
    table.add_column("Active", justify="center")
    table.add_column("External ID", style="dim")
    table.add_column("Created", style="dim")
    
    for tenant in tenants:
        table.add_row(
            str(tenant.id),
            tenant.name,
            tenant.display_name,
            "✓" if tenant.active else "✗",
            tenant.external_id or "",
            tenant.created_at.strftime("%Y-%m-%d %H:%M")
        )
    
    console.print(table)
    console.print(f"\n[dim]Total: {len(tenants)} tenant(s)[/dim]")


@tenant_cli.command("info")
@click.argument("tenant_identifier")
@async_command
async def tenant_info(tenant_identifier: str):
    """Show detailed information about a tenant."""
    try:
        # Try to get by ID first, then by name
        try:
            import uuid
            tenant_id = uuid.UUID(tenant_identifier)
            tenant = await TenantService.get_tenant(tenant_id)
        except ValueError:
            # Not a valid UUID, try by name
            tenant = await TenantService.get_tenant_by_name(tenant_identifier)
        
        # Get statistics
        stats = await TenantService.get_tenant_stats(tenant.id)
        
        # Display basic info
        console.print(Panel(
            f"[bold]ID:[/bold] {tenant.id}\n"
            f"[bold]Name:[/bold] {tenant.name}\n"
            f"[bold]Display Name:[/bold] {tenant.display_name}\n"
            f"[bold]External ID:[/bold] {tenant.external_id or 'None'}\n"
            f"[bold]Active:[/bold] {'Yes' if tenant.active else 'No'}\n"
            f"[bold]Created:[/bold] {tenant.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"[bold]Modified:[/bold] {tenant.modified_at.strftime('%Y-%m-%d %H:%M:%S')}",
            title=f"Tenant: {tenant.display_name}",
            border_style="cyan"
        ))
        
        # Display resource counts
        counts_table = Table(title="Resource Counts", show_header=False)
        counts_table.add_column("Resource", style="bold")
        counts_table.add_column("Count", justify="right")
        
        counts_table.add_row("Users", str(stats['counts']['users']))
        counts_table.add_row("Groups", str(stats['counts']['groups']))
        counts_table.add_row("API Tokens", str(stats['counts']['api_tokens']))
        
        console.print(counts_table)
        
    except ResourceNotFound as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise click.Abort()


@tenant_cli.command("update")
@click.argument("tenant_identifier")
@click.option("--display-name", "-d", help="New display name")
@click.option("--external-id", "-e", help="New external ID")
@click.option("--active/--inactive", default=None, help="Set active status")
@async_command
async def update_tenant(
    tenant_identifier: str,
    display_name: Optional[str],
    external_id: Optional[str],
    active: Optional[bool]
):
    """Update tenant information."""
    try:
        # Try to get by ID first, then by name
        try:
            import uuid
            tenant_id = uuid.UUID(tenant_identifier)
            tenant = await TenantService.get_tenant(tenant_id)
        except ValueError:
            # Not a valid UUID, try by name
            tenant = await TenantService.get_tenant_by_name(tenant_identifier)
        
        # Update tenant
        updated_tenant = await TenantService.update_tenant(
            tenant_id=tenant.id,
            display_name=display_name,
            external_id=external_id,
            active=active
        )
        
        console.print(Panel(
            f"[green]✓[/green] Tenant updated successfully!\n\n"
            f"[bold]ID:[/bold] {updated_tenant.id}\n"
            f"[bold]Name:[/bold] {updated_tenant.name}\n"
            f"[bold]Display Name:[/bold] {updated_tenant.display_name}\n"
            f"[bold]External ID:[/bold] {updated_tenant.external_id or 'None'}\n"
            f"[bold]Active:[/bold] {'Yes' if updated_tenant.active else 'No'}",
            title="Tenant Updated",
            border_style="green"
        ))
        
    except ResourceNotFound as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise click.Abort()
    except ResourceAlreadyExists as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise click.Abort()


@tenant_cli.command("delete")
@click.argument("tenant_identifier")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@async_command
async def delete_tenant(tenant_identifier: str, force: bool):
    """Delete a tenant and all associated data."""
    try:
        # Try to get by ID first, then by name
        try:
            import uuid
            tenant_id = uuid.UUID(tenant_identifier)
            tenant = await TenantService.get_tenant(tenant_id)
        except ValueError:
            # Not a valid UUID, try by name
            tenant = await TenantService.get_tenant_by_name(tenant_identifier)
        
        # Get statistics to show what will be deleted
        stats = await TenantService.get_tenant_stats(tenant.id)
        
        # Show warning
        console.print(Panel(
            f"[yellow]⚠️  WARNING[/yellow]\n\n"
            f"You are about to delete tenant '[bold]{tenant.display_name}[/bold]' ({tenant.name}).\n\n"
            f"This will permanently delete:\n"
            f"  • {stats['counts']['users']} users\n"
            f"  • {stats['counts']['groups']} groups\n"
            f"  • {stats['counts']['api_tokens']} API tokens\n\n"
            f"[bold red]This action cannot be undone![/bold red]",
            title="Delete Tenant",
            border_style="red"
        ))
        
        # Confirm deletion
        if not force:
            confirm = click.confirm("Are you sure you want to proceed?", default=False)
            if not confirm:
                console.print("[yellow]Deletion cancelled.[/yellow]")
                return
        
        # Delete tenant
        await TenantService.delete_tenant(tenant.id)
        
        console.print(f"[green]✓[/green] Tenant '{tenant.display_name}' deleted successfully.")
        
    except ResourceNotFound as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise click.Abort()
    except InvalidSyntax as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        raise click.Abort()