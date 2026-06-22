from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Worker configuration, loaded from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # CVR Elasticsearch (free creds via cvrselvbetjening@erst.dk)
    cvr_es_url: str = "http://distribution.virk.dk/cvr-permanent/virksomhed/_search"
    cvr_es_user: str = ""
    cvr_es_password: str = ""

    # Enrichment / AI
    pagespeed_api_key: str = ""
    anthropic_api_key: str = ""


settings = Settings()
