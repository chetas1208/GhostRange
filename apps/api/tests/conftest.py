import os

# Local pytest must not require production live-only env (operators use .env with vultr flags).
os.environ.setdefault("GHOSTRANGE_SKIP_RUNTIME_VALIDATE", "true")
