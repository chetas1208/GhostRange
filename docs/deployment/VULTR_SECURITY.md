# Production security checklist

- [ ] Managed PostgreSQL **not** open to `0.0.0.0/0` (Trusted Sources or VPC)
- [ ] Postgres client uses TLS (`sslmode=require` or CA file)
- [ ] Object Storage bucket **private** (anonymous GET fails)
- [ ] No `S3_SECRET`, inference key, or `POSTGRES_DSN` in frontend bundle
- [ ] Only ports **22, 80, 443** on VM public interface
- [ ] Redis/Valkey **not** published to host
- [ ] API **not** published to host (only via Caddy)
- [ ] `.env.production` mode **600**, not in git
- [ ] Rotate credentials exposed in chat/logs
