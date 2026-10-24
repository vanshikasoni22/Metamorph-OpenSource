import hashlib
import json
from typing import Optional, List, Dict, Any
from ..database import get_cached, set_cached, delete_cached
from ..config import CACHE_TTL_SECONDS

def generate_cache_key(issue_url: str, pr_urls: Optional[List[str]] = None) -> str:
    """
    Produces a deterministic SHA256 cache key based on the normalized issue URL and sorted PR URLs.
    """
    clean_issue = (issue_url or "").strip().lower()
    clean_prs = sorted([p.strip().lower() for p in (pr_urls or []) if p and p.strip()])
    raw = f"{clean_issue}|{','.join(clean_prs)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def get_maintainer_cache(issue_url: str, pr_urls: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    key = generate_cache_key(issue_url, pr_urls)
    return get_cached(key)

def set_maintainer_cache(
    issue_url: str,
    data: Dict[str, Any],
    pr_urls: Optional[List[str]] = None,
    ttl_seconds: Optional[int] = CACHE_TTL_SECONDS
):
    key = generate_cache_key(issue_url, pr_urls)
    set_cached(key, data, ttl_seconds=ttl_seconds)

def invalidate_maintainer_cache(issue_url: str, pr_urls: Optional[List[str]] = None):
    key = generate_cache_key(issue_url, pr_urls)
    delete_cached(key)

def generate_llm_cache_key(model: str, system_prompt: str, user_prompt: str, schema_name: str) -> str:
    """Deterministic hash of LLM query inputs to prevent burning rate limits."""
    raw = f"{model}|{system_prompt}|{user_prompt}|{schema_name}"
    return f"llm_{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"

def get_llm_cache(model: str, system_prompt: str, user_prompt: str, schema_name: str) -> Optional[Dict[str, Any]]:
    key = generate_llm_cache_key(model, system_prompt, user_prompt, schema_name)
    return get_cached(key)

def set_llm_cache(
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema_name: str,
    data: Dict[str, Any],
    ttl_seconds: Optional[int] = CACHE_TTL_SECONDS
):
    key = generate_llm_cache_key(model, system_prompt, user_prompt, schema_name)
    set_cached(key, data, ttl_seconds=ttl_seconds)

