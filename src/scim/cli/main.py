import os
import sys
import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from .manage_tokens import tokens_group
from .tenant import tenant_cli
from .application import app_group

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="PyScim")
def cli():
    """PyScim - SCIM 2.0 Server Management CLI
    
    A standards-compliant SCIM server compatible with Azure AD, Okta, and other identity providers.
    """
    pass


# Add token management commands
cli.add_command(tokens_group, name="token")

# Add tenant management commands  
cli.add_command(tenant_cli, name="tenant")

# Add application management commands
cli.add_command(app_group, name="app")


@cli.group()
def run():
    """Run the SCIM server"""
    pass


@run.command()
@click.option('--host', '-h', default='0.0.0.0', help='Host to bind to')
@click.option('--port', '-p', default=8000, type=int, help='Port to bind to')
@click.option('--reload/--no-reload', default=True, help='Enable auto-reload')
def dev(host: str, port: int, reload: bool):
    """Run server in development mode"""
    console.print(Panel.fit(
        f"[bold green]Starting PyScim Development Server[/bold green]\n\n"
        f"[yellow]Host:[/yellow] {host}:{port}\n"
        f"[yellow]Docs:[/yellow] http://localhost:{port}/docs\n"
        f"[yellow]API:[/yellow]  http://localhost:{port}/scim/v2\n\n"
        f"[dim]Press CTRL+C to stop[/dim]",
        title="🚀 PyScim Dev Server"
    ))
    
    import uvicorn
    uvicorn.run(
        "scim.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True
    )


@run.command()
@click.option('--host', '-h', default='0.0.0.0', help='Host to bind to')
@click.option('--port', '-p', default=8000, type=int, help='Port to bind to')
@click.option('--workers', '-w', default=1, type=int, help='Number of worker processes')
def prod(host: str, port: int, workers: int):
    """Run server in production mode"""
    console.print(Panel.fit(
        f"[bold green]Starting PyScim Production Server[/bold green]\n\n"
        f"[yellow]Host:[/yellow] {host}:{port}\n"
        f"[yellow]Workers:[/yellow] {workers}\n"
        f"[yellow]API:[/yellow]  http://{host}:{port}/scim/v2\n\n"
        f"[dim]Press CTRL+C to stop[/dim]",
        title="🚀 PyScim Production Server"
    ))
    
    import uvicorn
    uvicorn.run(
        "scim.main:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info",
        access_log=True
    )


@cli.command()
@click.option('--show-env', is_flag=True, help='Show environment file location')
@click.option('--show-values', is_flag=True, help='Show actual configuration values')
def config(show_env: bool, show_values: bool):
    """Display current configuration"""
    try:
        from scim.config import settings
        
        console.print("\n[bold]PyScim Configuration[/bold]\n")
        
        # Show env file location
        env_file = os.path.join(os.getcwd(), '.env')
        if os.path.exists(env_file):
            console.print(f"[green]✓[/green] Environment file: {env_file}")
        else:
            console.print(f"[yellow]⚠[/yellow]  No .env file found at: {env_file}")
        
        # Basic info always shown
        table = Table(title="Server Information")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        base_url = f"http://localhost:{settings.port}" if settings.host in ['0.0.0.0', '127.0.0.1'] else f"http://{settings.host}:{settings.port}"
        
        table.add_row("SCIM Base URL", f"{base_url}{settings.api_prefix}")
        table.add_row("Environment", settings.environment)
        table.add_row("Authentication", "Enabled" if settings.auth_enabled else "Disabled")
        table.add_row("Debug Mode", "On" if settings.debug else "Off")
        
        console.print(table)
        
        # Show detailed values if requested
        if show_values:
            console.print("\n[bold]Detailed Configuration:[/bold]\n")
            
            config_table = Table()
            config_table.add_column("Setting", style="cyan")
            config_table.add_column("Value")
            config_table.add_column("Description", style="dim")
            
            # Group settings
            settings_groups = {
                "Server": [
                    ("host", settings.host, "Server host"),
                    ("port", settings.port, "Server port"),
                    ("api_prefix", settings.api_prefix, "API route prefix"),
                ],
                "Database": [
                    ("database_url", settings.database_url if not show_values else "***", "PostgreSQL connection"),
                ],
                "Authentication": [
                    ("auth_enabled", settings.auth_enabled, "API token authentication"),
                ],
                "Application": [
                    ("app_name", settings.app_name, "Application name"),
                    ("environment", settings.environment, "Current environment"),
                    ("debug", settings.debug, "Debug mode"),
                    ("log_level", settings.log_level, "Logging level"),
                ],
                "Limits": [
                    ("default_page_size", settings.default_page_size, "Default pagination size"),
                    ("max_page_size", settings.max_page_size, "Maximum page size"),
                    ("rate_limit_enabled", settings.rate_limit_enabled, "Rate limiting"),
                    ("rate_limit_per_minute", settings.rate_limit_per_minute, "Requests per minute"),
                ],
            }
            
            for group_name, group_settings in settings_groups.items():
                config_table.add_row(f"[bold]{group_name}[/bold]", "", "")
                for setting_name, value, desc in group_settings:
                    config_table.add_row(f"  {setting_name}", str(value), desc)
            
            console.print(config_table)
        
        # Show helpful commands
        console.print("\n[dim]Tip: Use --show-values to see all configuration values[/dim]")
        console.print("[dim]Tip: Create a .env file to override default settings[/dim]\n")
        
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        console.print("[yellow]Make sure you're running this from the project root[/yellow]")


@cli.group()
def db():
    """Database management commands"""
    pass


@db.command()
def init():
    """Initialize the database schema"""
    async def _init():
        from tortoise import Tortoise
        from scim.config import settings
        
        console.print("[yellow]Initializing database...[/yellow]")
        
        try:
            await Tortoise.init(config=settings.tortoise_orm_config)
            await Tortoise.generate_schemas()
            
            console.print("[green]✓ Database initialized successfully![/green]")
            console.print(f"[dim]Connected to: {settings.database_url.split('@')[1] if '@' in settings.database_url else settings.database_url}[/dim]")
            
        except Exception as e:
            console.print(f"[red]✗ Failed to initialize database: {e}[/red]")
            sys.exit(1)
        finally:
            await Tortoise.close_connections()
    
    asyncio.run(_init())


@db.command()
def status():
    """Check database connection status"""
    async def _status():
        from tortoise import Tortoise
        from scim.config import settings
        from scim.models import User, Group, APIToken
        
        console.print("[yellow]Checking database connection...[/yellow]")
        
        try:
            await Tortoise.init(config=settings.tortoise_orm_config)
            
            # Try to count records
            user_count = await User.all().count()
            group_count = await Group.all().count()
            token_count = await APIToken.filter(active=True).count()
            
            console.print("[green]✓ Database connection successful![/green]\n")
            
            table = Table(title="Database Status")
            table.add_column("Resource", style="cyan")
            table.add_column("Count", style="green")
            
            table.add_row("Users", str(user_count))
            table.add_row("Groups", str(group_count))
            table.add_row("Active API Tokens", str(token_count))
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]✗ Database connection failed: {e}[/red]")
            console.print("[yellow]Check your DATABASE_URL in .env[/yellow]")
            sys.exit(1)
        finally:
            await Tortoise.close_connections()
    
    asyncio.run(_status())


if __name__ == '__main__':
    cli()