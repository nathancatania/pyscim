import logging
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback
from scim.config import settings


console = Console()

# Install rich traceback handler for better error formatting
install_rich_traceback(show_locals=settings.debug, suppress=[])


def setup_logging(
    level: Optional[str] = None,
    format: str = "%(message)s",
    datefmt: str = "[%X]",
) -> None:
    log_level = level or settings.log_level
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=format,
        datefmt=datefmt,
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                tracebacks_show_locals=settings.debug,
                show_path=settings.debug,
                enable_link_path=settings.debug,
            )
        ],
    )
    
    # Set specific log levels for libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)  # Changed from WARNING to see HTTP requests
    logging.getLogger("tortoise").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Disable noisy loggers in production
    if settings.is_production:
        logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
        logging.getLogger("tortoise.db_client").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


# Setup logging on module import
setup_logging()

# Export a default logger
logger = get_logger("scim")