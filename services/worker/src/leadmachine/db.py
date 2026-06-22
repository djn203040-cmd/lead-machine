from functools import lru_cache

from supabase import Client, create_client

from .config import settings


@lru_cache
def get_client() -> Client:
    """Supabase client using the service-role key (bypasses RLS)."""
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set (see .env.example)"
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
