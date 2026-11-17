import os


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-with-at-least-thirty-two-bytes")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_STORAGE_BUCKET", "climbing-videos")
os.environ.setdefault("RESEND_API_KEY", "test-resend-api-key")
os.environ.setdefault("RESEND_FROM_EMAIL", "no-reply@example.com")
os.environ.setdefault(
    "PASSWORD_RESET_CODE_SECRET",
    "test-password-reset-code-secret-with-at-least-thirty-two-bytes",
)
