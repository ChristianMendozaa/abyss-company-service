# app/services/supabase_service.py
from functools import lru_cache
from supabase import create_client, Client  # asegúrate que está en requirements

from app.config import get_settings


@lru_cache()
def get_supabase_auth_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
