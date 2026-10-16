import os


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-with-at-least-thirty-two-bytes")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_STORAGE_BUCKET", "climbing-videos")
