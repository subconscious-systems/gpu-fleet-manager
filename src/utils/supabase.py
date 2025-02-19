from supabase import create_client, Client
import os
from typing import Optional
from functools import lru_cache

@lru_cache()
def get_supabase() -> Client:
    """
    Create and return a cached Supabase client instance.
    Uses the same environment variables as the main subconscious-systems project.
    """
    supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase URL and key must be set in environment variables")
    
    return create_client(supabase_url, supabase_key)

@lru_cache()
def get_supabase_admin() -> Client:
    """
    Create and return a cached Supabase admin client instance.
    Uses service role key for admin operations.
    """
    supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_service_key:
        raise ValueError("Supabase URL and service key must be set in environment variables")
    
    return create_client(supabase_url, supabase_service_key)

# Convenience function to get authenticated user's ID
async def get_user_id(supabase: Client) -> Optional[str]:
    """Get the current authenticated user's ID"""
    try:
        response = await supabase.auth.get_user()
        return response.user.id if response.user else None
    except Exception:
        return None
