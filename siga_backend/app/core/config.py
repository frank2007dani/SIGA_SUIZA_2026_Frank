from pydantic_settings import BaseSettings
from typing import List, Optional
from pydantic import Field

from .db_url import build_async_database_url, build_sync_database_url, is_production

class CoreSettings(BaseSettings):
    """Configuración centralizada del Core con resiliencia"""
    
    # Core Identity
    app_name: str = "SIGA Core"
    environment: str = "development"
    secret_key: str = "change-me-in-production"
    debug: bool = True
    frontend_url: Optional[str] = Field(default=None, description="URL pública del frontend")
    cors_origins: str = Field(default="", description="Orígenes CORS separados por coma")
    
    # Database (Solo para Identity del Core)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "dariana"
    DB_NAME: str = "siga_suiza_2026"
    DATABASE_URL: Optional[str] = None
    
    # Module Registry
    modules_auto_discover: bool = True
    modules_validate_on_start: bool = True
    modules_discovery_sources: List[str] = ["local", "database", "kubernetes"]
    
    # Communication
    http_proxy_timeout: int = 30
    
    # Security
    token_expire_minutes: int = 30
    module_token_expire_hours: int = 24
    
    # NATS Event Bus
    enable_nats: bool = Field(default=True, description="Habilitar NATS Event Bus")
    nats_url: str = Field(default="nats://localhost:4222", description="URL de NATS")
    
    # 🔄 RESILIENCIA - Configuraciones nuevas
    # Cache distribuido
    cache_enabled: bool = Field(default=True, description="Habilitar cache distribuido")
    redis_url: Optional[str] = Field(default=None, description="URL completa de Redis (sobreescribe host/port)")
    redis_host: str = Field(default="localhost", description="Host de Redis")
    redis_port: int = Field(default=6379, description="Puerto de Redis")
    redis_password: Optional[str] = Field(default=None, description="Password de Redis")
    cache_default_ttl: int = Field(default=300, description="TTL por defecto en segundos")
    
    # Health Monitoring
    health_check_enabled: bool = Field(default=True, description="Habilitar monitoreo de salud")
    health_check_interval: int = Field(default=30, description="Intervalo de health checks en segundos")
    
    # Fallback System
    fallback_enabled: bool = Field(default=True, description="Habilitar sistema de fallback")
    
    # Circuit Breaker
    circuit_breaker_enabled: bool = Field(default=True, description="Habilitar circuit breaker")
    circuit_breaker_failure_threshold: int = Field(default=5, description="Umbral de fallos para abrir circuito")
    circuit_breaker_recovery_timeout: int = Field(default=60, description="Tiempo de recuperación en segundos")
    
    @property
    def is_production(self) -> bool:
        return is_production() or self.environment.strip().lower() == "production"

    @property
    def effective_debug(self) -> bool:
        return self.debug and not self.is_production

    @property
    def database_url(self) -> str:
        if not self.DATABASE_URL and self.is_production:
            raise RuntimeError("DATABASE_URL es obligatoria cuando ENVIRONMENT=production")
        return build_async_database_url(
            self.DATABASE_URL,
            user=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=str(self.DB_PORT),
            database=self.DB_NAME,
        )

    @property
    def database_sync_url(self) -> str:
        if not self.DATABASE_URL and self.is_production:
            raise RuntimeError("DATABASE_URL es obligatoria cuando ENVIRONMENT=production")
        return build_sync_database_url(
            self.DATABASE_URL,
            user=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=str(self.DB_PORT),
            database=self.DB_NAME,
        )

    @property
    def allowed_origins(self) -> list[str]:
        dev_origins = [
            "http://localhost:5173", "http://127.0.0.1:5173",
            "http://localhost:5174", "http://127.0.0.1:5174",
            "http://localhost:3000", "http://127.0.0.1:3000",
            "http://localhost:3001", "http://127.0.0.1:3001",
        ]
        configured = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if self.frontend_url:
            configured.append(self.frontend_url.rstrip("/"))
        return configured if self.is_production else dev_origins + configured
    
    @property
    def redis_url_effective(self) -> str:
        """Retorna la URL efectiva de Redis: redis_url si está definida, o construida desde host/port"""
        if self.redis_url:
            return self.redis_url
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}"

    class Config:
        env_file = ".env"
        case_sensitive = False

# Instancia global
settings = CoreSettings()