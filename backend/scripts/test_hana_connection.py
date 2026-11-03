"""
Standalone read-only connectivity test script for SAP HANA Cloud.
Verifies:
1. DNS resolution
2. TCP socket handshake on port 443
3. TLS encryption negotiation
4. Authentication via hdbcli dbapi
5. Read-only query execution (SELECT CURRENT_USER, CURRENT_SCHEMA FROM DUMMY)
6. Available schemas and user privileges (read-only)
7. SQLAlchemy AsyncEngine (hana+aiohdbcli) connectivity test

CRITICAL: Never logs or prints sensitive credentials/passwords.
"""

import os
import socket
import ssl
import sys
from urllib.parse import quote_plus


def test_dns(host: str) -> list[str]:
    print(f"[*] 1. Testing DNS resolution for: {host}")
    try:
        ips = socket.gethostbyname_ex(host)[2]
        print(f"    [+] DNS resolved successfully: {ips}")
        return ips
    except Exception as exc:
        print(f"    [-] DNS resolution failed: {exc}")
        raise


def test_tcp_and_tls(host: str, port: int) -> None:
    print(f"[*] 2. Testing TCP socket connectivity to {host}:{port}")
    try:
        sock = socket.create_connection((host, port), timeout=10)
        print("    [+] TCP connection established successfully.")
        
        print(f"[*] 3. Testing TLS handshake on {host}:{port}")
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # For initial handshake test
        with context.wrap_socket(sock, server_hostname=host) as ssock:
            cipher = ssock.cipher()
            version = ssock.version()
            print(f"    [+] TLS handshake established: Protocol={version}, Cipher={cipher[0] if cipher else 'unknown'}")
    except Exception as exc:
        print(f"    [-] TCP/TLS handshake failed: {exc}")
        raise


def test_hdbcli_connection(host: str, port: int, user: str, password: str) -> None:
    print(f"[*] 4. Testing hdbcli database authentication as user '{user}'...")
    try:
        from hdbcli import dbapi
    except ImportError:
        print("    [-] hdbcli is not installed in the current environment.")
        sys.exit(1)

    conn = None
    for validate_ssl in [True, False]:
        try:
            print(f"    -> Attempting connection (encrypt=True, sslValidateCertificate={validate_ssl})...")
            conn = dbapi.connect(
                address=host,
                port=port,
                user=user,
                password=password,
                encrypt=True,
                sslValidateCertificate=validate_ssl,
            )
            print(f"    [+] Connected successfully via hdbcli (sslValidateCertificate={validate_ssl})!")
            break
        except Exception as exc:
            err_msg = str(exc)
            if "certificate" in err_msg.lower() and validate_ssl:
                print("    [!] Certificate validation check failed; retrying with sslValidateCertificate=False...")
                continue
            print(f"    [-] hdbcli connection failed: {err_msg}")
            if not validate_ssl:
                raise

    if not conn:
        print("    [-] Could not establish connection.")
        return

    try:
        cursor = conn.cursor()
        print("[*] 5. Executing read-only verification query: SELECT CURRENT_USER, CURRENT_SCHEMA FROM DUMMY")
        cursor.execute("SELECT CURRENT_USER, CURRENT_SCHEMA FROM DUMMY")
        row = cursor.fetchone()
        print(f"    [+] Query Result: CURRENT_USER='{row[0]}', CURRENT_SCHEMA='{row[1]}'")

        print("[*] 6. Inspecting accessible schemas for this account...")
        cursor.execute(
            "SELECT SCHEMA_NAME, SCHEMA_OWNER FROM SYS.SCHEMAS "
            "WHERE SCHEMA_OWNER = CURRENT_USER OR SCHEMA_NAME LIKE '%HACKFEST%' OR SCHEMA_NAME = 'CLEARHIRE' "
            "ORDER BY SCHEMA_NAME"
        )
        schemas = cursor.fetchall()
        print(f"    [+] Accessible/Related Schemas found: {len(schemas)}")
        for s in schemas:
            print(f"        - Schema: {s[0]} (Owner: {s[1]})")

        cursor.close()
    finally:
        conn.close()
        print("    [+] hdbcli connection closed cleanly.")


async def test_sqlalchemy_async_connection(host: str, port: int, user: str, password: str, schema: str | None = None) -> None:
    print(f"[*] 7. Testing SQLAlchemy 2.0 AsyncEngine (hana+aiohdbcli) as '{user}'...")
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    enc_user = quote_plus(user)
    enc_pass = quote_plus(password)
    
    url = f"hana+aiohdbcli://{enc_user}:{enc_pass}@{host}:{port}/?encrypt=true&sslValidateCertificate=false"
    if schema:
        url += f"&currentSchema={schema}"

    engine = create_async_engine(url, echo=False)
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT CURRENT_USER, CURRENT_SCHEMA FROM DUMMY"))
            row = res.fetchone()
            print(f"    [+] SQLAlchemy AsyncEngine success: CURRENT_USER='{row[0]}', CURRENT_SCHEMA='{row[1]}'")
    except Exception as exc:
        print(f"    [-] SQLAlchemy AsyncEngine failed: {exc}")
        raise
    finally:
        await engine.dispose()
        print("    [+] SQLAlchemy AsyncEngine disposed cleanly.")


def main() -> None:
    from app.core.config import get_settings
    settings = get_settings()

    host = settings.HANA_HOST or os.getenv("HANA_HOST", "")
    port = settings.HANA_PORT or int(os.getenv("HANA_PORT", "443"))
    user = settings.HANA_USER or os.getenv("HANA_USER", "")
    password = settings.HANA_PASSWORD or os.getenv("HANA_PASSWORD", "")
    schema = settings.HANA_SCHEMA or os.getenv("HANA_SCHEMA", "")

    if not host or not user or not password:
        print("[-] Error: HANA_HOST, HANA_USER, and HANA_PASSWORD must be configured in .env or environment.")
        sys.exit(1)

    print("==================================================================")
    print("ClearHire — SAP HANA Cloud Read-Only Connectivity Test (Phase 2)")
    print(f"Target Host: {host}")
    print(f"Target Port: {port}")
    print(f"Target User: {user}")
    print(f"Target Schema: {schema}")
    print("==================================================================")

    # 1. DNS
    test_dns(host)
    print()

    # 2 & 3. TCP & TLS
    test_tcp_and_tls(host, port)
    print()

    # 4, 5, 6. hdbcli connection and read-only query
    test_hdbcli_connection(host, port, user, password)
    print()

    # 7. SQLAlchemy AsyncEngine test
    import asyncio
    asyncio.run(test_sqlalchemy_async_connection(host, port, user, password, schema))
    print()

    print("==================================================================")
    print("[SUCCESS] All Phase 2 Connectivity Tests Passed!")
    print("==================================================================")


if __name__ == "__main__":
    main()
