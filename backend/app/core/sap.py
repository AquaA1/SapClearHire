"""
SAP BTP Cloud Foundry / Kyma environment credential parser.
Parses VCAP_SERVICES and SAP BTP service bindings to enable zero-config
switching from local development to SAP BTP managed cloud services.
"""

import json
import os
from typing import Any
from urllib.parse import quote_plus


def get_vcap_services() -> dict[str, Any]:
    """Parse VCAP_SERVICES environment variable if present."""
    vcap_raw = os.getenv("VCAP_SERVICES")
    if not vcap_raw:
        return {}
    try:
        return json.loads(vcap_raw)
    except Exception:
        return {}


def get_sap_postgres_uri() -> str | None:
    """
    Extracts managed PostgreSQL connection URI from SAP BTP VCAP_SERVICES.
    Supports standard SAP 'postgresql-db', 'postgres', or user-provided services.
    """
    vcap = get_vcap_services()
    if not vcap:
        return None

    # Search for PostgreSQL service instances
    candidates: list[dict[str, Any]] = []
    for service_name, instances in vcap.items():
        if any(term in service_name.lower() for term in ("postgres", "postgresql", "rds")):
            candidates.extend(instances)

    # Check user-provided services as well
    for instance in vcap.get("user-provided", []):
        creds = instance.get("credentials", {})
        if "uri" in creds or "postgres" in instance.get("name", "").lower():
            candidates.append(instance)

    if not candidates:
        return None

    primary_creds = candidates[0].get("credentials", {})

    # If full URI is provided
    if "uri" in primary_creds:
        raw_uri = primary_creds["uri"]
        # Ensure async driver for SQLAlchemy
        if raw_uri.startswith("postgres://"):
            return raw_uri.replace("postgres://", "postgresql+asyncpg://", 1)
        if raw_uri.startswith("postgresql://") and not raw_uri.startswith("postgresql+"):
            return raw_uri.replace("postgresql://", "postgresql+asyncpg://", 1)
        return raw_uri

    # Reconstruct from discrete parameters
    host = primary_creds.get("hostname") or primary_creds.get("host")
    port = primary_creds.get("port", 5432)
    user = primary_creds.get("username") or primary_creds.get("user")
    password = primary_creds.get("password")
    dbname = primary_creds.get("dbname") or primary_creds.get("database") or "clearhire_db"
    ssl = primary_creds.get("sslmode", "require")

    if host and user and password:
        encoded_user = quote_plus(str(user))
        encoded_pass = quote_plus(str(password))
        return f"postgresql+asyncpg://{encoded_user}:{encoded_pass}@{host}:{port}/{dbname}?ssl={ssl}"

    return None


def get_sap_objectstore_credentials() -> dict[str, Any] | None:
    """
    Extracts SAP BTP Object Store (S3-compatible) credentials from VCAP_SERVICES.
    """
    vcap = get_vcap_services()
    if not vcap:
        return None

    candidates: list[dict[str, Any]] = []
    for service_name, instances in vcap.items():
        if any(term in service_name.lower() for term in ("objectstore", "s3", "blob")):
            candidates.extend(instances)

    for instance in vcap.get("user-provided", []):
        if "s3" in instance.get("name", "").lower() or "object" in instance.get("name", "").lower():
            candidates.append(instance)

    if not candidates:
        return None

    creds = candidates[0].get("credentials", {})
    return {
        "bucket": creds.get("bucket"),
        "access_key": creds.get("access_key_id") or creds.get("access_key"),
        "secret_key": creds.get("secret_access_key") or creds.get("secret_key"),
        "endpoint_url": creds.get("endpoint") or creds.get("host"),
        "region": creds.get("region", "us-east-1"),
    }


def get_sap_redis_url() -> str | None:
    """
    Extracts Redis credentials from SAP BTP VCAP_SERVICES.
    """
    vcap = get_vcap_services()
    if not vcap:
        return None

    for service_name, instances in vcap.items():
        if "redis" in service_name.lower():
            creds = instances[0].get("credentials", {})
            if "uri" in creds:
                return creds["uri"]
            host = creds.get("hostname") or creds.get("host")
            port = creds.get("port", 6379)
            password = creds.get("password")
            if host:
                auth = f":{quote_plus(str(password))}@" if password else ""
                scheme = "rediss" if creds.get("ssl", False) else "redis"
                return f"{scheme}://{auth}{host}:{port}/0"

    return None
