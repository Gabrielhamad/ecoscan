"""Bound external waits without sharing an authenticated client's session."""
from contextlib import contextmanager


def create_bounded_client(url, key):
    import httpx
    from supabase import create_client
    from supabase.lib.client_options import SyncClientOptions

    # These are per-phase inactivity limits, not an end-to-end deadline.
    transport = httpx.Client(
        timeout=httpx.Timeout(connect=3., read=8., write=8., pool=3.),
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=0),
    )
    try:
        return create_client(url, key, options=SyncClientOptions(
            httpx_client=transport, auto_refresh_token=False, persist_session=True,
            postgrest_client_timeout=8, storage_client_timeout=8,
        ))
    except Exception:
        transport.close()
        raise


@contextmanager
def isolated_auth_client(factory):
    """Release auth sockets on success and failure; never cache credentials."""
    client = factory()
    try:
        yield client
    finally:
        try:
            client.auth.close()
        except Exception:
            # Closing a socket must not change the outcome of a confirmed write.
            pass
