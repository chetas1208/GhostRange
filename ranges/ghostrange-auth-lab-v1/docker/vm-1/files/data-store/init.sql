-- ghostrange-auth-lab-v1 data store (db01) — minimal schema.
--
-- Not yet written to by auth01's app code (see files/auth/app.py's docstring) --
-- present so the schema exists and is ready for the wave-2 scenario owner to wire
-- real credential storage / audit persistence into, without touching provisioning.

CREATE TABLE IF NOT EXISTS login_attempts (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    -- Lab-only placeholder; the real scenario owner decides the actual credential
    -- storage/hashing scheme (and any deliberate weaknesses) for ghostrange-auth-lab-v1.
    password_placeholder TEXT NOT NULL
);

INSERT INTO users (username, password_placeholder)
VALUES ('demo', 'ghostrange-lab-only')
ON CONFLICT (username) DO NOTHING;
