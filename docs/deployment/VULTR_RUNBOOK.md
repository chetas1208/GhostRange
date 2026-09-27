# GhostRange production runbook

## Status

```bash
cd /opt/ghostrange && bash scripts/production-status.sh
docker compose -f docker-compose.prod.yml ps
curl -s http://127.0.0.1/health/ready | jq .
```

## Logs

```bash
docker compose -f docker-compose.prod.yml logs -f --tail=200 api
docker compose -f docker-compose.prod.yml logs -f proxy
```

## Restart

```bash
docker compose -f docker-compose.prod.yml restart api
docker compose -f docker-compose.prod.yml up -d
```

## Deploy new revision

```bash
bash scripts/deploy-vultr.sh   # from operator workstation
```

## Rollback

```bash
bash scripts/rollback-vultr.sh <previous-sha>
```

## Database connectivity

- Verify `POSTGRES_DSN` on VM; test from api container: readiness endpoint.
- If auth fails: check Trusted Sources / VPC on Managed PostgreSQL.

## Object storage

- `curl -X POST http://127.0.0.1/v1/ops/smoke/object-storage`

## Inference

- `curl -X POST http://127.0.0.1/v1/ops/smoke/inference`
- Failure should not crash API; readiness marks inference degraded.

## Disk full

- `docker system prune -f` (careful)
- Check log rotation in compose `logging.options`

## SSE issues

- Confirm Caddy `flush_interval -1` on `/v1/*`
- Increase proxy timeouts if needed

## Emergency stop

```bash
docker compose -f docker-compose.prod.yml down
```
