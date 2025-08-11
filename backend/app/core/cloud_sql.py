"""Cloud SQL Database Connection Configuration

This module handles proper Cloud SQL connection for both Cloud Run and local development.
It supports Unix socket connections for production and TCP connections for local development.
"""

import os
import logging
from typing import Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


def get_cloud_sql_connection_string(
    user: str,
    password: str,
    database: str,
    instance_connection_name: Optional[str] = None,
    use_unix_socket: bool = False,
    host: Optional[str] = None,
    port: int = 5432,
) -> tuple[str, str]:
    """
    Generate proper Cloud SQL connection strings for async and sync connections.
    
    Args:
        user: Database username
        password: Database password
        database: Database name
        instance_connection_name: Cloud SQL instance connection name (PROJECT:REGION:INSTANCE)
        use_unix_socket: Whether to use Unix socket (for Cloud Run) or TCP
        host: Database host (for TCP connections)
        port: Database port (for TCP connections)
    
    Returns:
        Tuple of (async_url, sync_url)
    """
    # URL-encode password to handle special characters
    encoded_password = quote_plus(password)
    
    if use_unix_socket and instance_connection_name:
        # Unix socket connection for Cloud Run
        # Format: postgresql://USER:PASSWORD@/DATABASE?host=/cloudsql/INSTANCE_CONNECTION_NAME
        socket_path = f"/cloudsql/{instance_connection_name}"
        
        async_url = (
            f"postgresql+asyncpg://{user}:{encoded_password}@/{database}"
            f"?host={socket_path}"
        )
        sync_url = (
            f"postgresql://{user}:{encoded_password}@/{database}"
            f"?host={socket_path}"
        )
        
        logger.info(f"Using Unix socket connection: {socket_path}")
    else:
        # TCP connection for local development or when using Cloud SQL Proxy
        if not host:
            host = "localhost"
        
        async_url = (
            f"postgresql+asyncpg://{user}:{encoded_password}@{host}:{port}/{database}"
        )
        sync_url = (
            f"postgresql://{user}:{encoded_password}@{host}:{port}/{database}"
        )
        
        logger.info(f"Using TCP connection: {host}:{port}")
    
    return async_url, sync_url


def get_database_urls() -> tuple[str, str]:
    """
    Get database URLs based on environment configuration.
    
    Returns:
        Tuple of (async_url, sync_url)
    """
    # Check if running on Cloud Run
    is_cloud_run = os.getenv("K_SERVICE") is not None
    
    # Get database credentials from environment
    db_user = os.getenv("DB_USER", "luckygas")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "luckygas")
    
    # Cloud SQL instance connection name
    instance_connection_name = os.getenv(
        "CLOUD_SQL_CONNECTION_NAME",
        "vast-tributary-466619-m8:asia-east1:luckygas-staging"
    )
    
    # For local development
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", "5432"))
    
    # Use Unix socket on Cloud Run, TCP otherwise
    use_unix_socket = is_cloud_run or os.getenv("USE_CLOUD_SQL_SOCKET", "").lower() == "true"
    
    # If DB_PASSWORD is not set (e.g., local development), try Secret Manager
    # Note: On Cloud Run, DB_PASSWORD is already set from Secret Manager mount
    if not db_password and not is_cloud_run:
        # Try to get password from Secret Manager for local development
        db_password = get_secret_value("db-password-luckygas") or ""
    
    # Log connection type (without exposing password)
    logger.info(f"Database connection - User: {db_user}, DB: {db_name}, Unix Socket: {use_unix_socket}")
    if not db_password:
        logger.error("No database password found in environment or Secret Manager!")
    
    return get_cloud_sql_connection_string(
        user=db_user,
        password=db_password,
        database=db_name,
        instance_connection_name=instance_connection_name,
        use_unix_socket=use_unix_socket,
        host=db_host,
        port=db_port,
    )


def get_secret_value(secret_id: str) -> Optional[str]:
    """
    Get secret value from Google Secret Manager.
    
    Args:
        secret_id: The secret ID in Secret Manager
    
    Returns:
        Secret value or None if not found
    """
    try:
        from google.cloud import secretmanager
        
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GCP_PROJECT", "vast-tributary-466619-m8")
        
        # Build the resource name
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        
        # Access the secret version
        response = client.access_secret_version(request={"name": name})
        
        # Return the decoded payload
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.warning(f"Could not retrieve secret {secret_id}: {e}")
        return None