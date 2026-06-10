# v2ray_auto

This branch is a destructive rewrite of the original project.

## Branch

`refactor/destructive-core-rewrite`

## What changed

- Root script `v2ray_auto.py` was removed because it conflicts with the new Python package name.
- Runtime configuration moved to environment variables.
- Legacy `config.py` no longer stores credentials.
- Core logic moved to `v2ray_auto/core/`.
- HTTP entrypoint moved to `v2ray_auto/api/app.py`.
- Old `vue_web/Python_api/config_server_api.py` is now a compatibility wrapper.
- Legacy environment-dependent tests were replaced with pure function tests.

## Runtime configuration

Copy the example file and edit values locally:

```bash
cp .env.example .env
```

Required variables:

```bash
V2RAY_AUTO_API_KEY=change-me
V2RAY_AUTO_ALLOWED_ORIGINS=http://localhost:8080
```

## Run API

```bash
pip install -r requirements.txt
python -m flask --app v2ray_auto.api.app run --host 0.0.0.0 --port 5000
```

Health check:

```bash
curl http://127.0.0.1:5000/health
```

Deploy endpoint:

```bash
POST /api/deploy
Header: X-API-Key: <your api key>
```

Payload example:

```json
{
  "host": "203.0.113.10",
  "serverPort": 22,
  "username": "root",
  "password": "<ssh password>"
}
```

## Important behavior change

The refactored deployment service does not download and execute installer scripts. It expects the target server to already have a managed service named `v2ray.service`.

The current deployment flow is:

1. Connect to the server with SSH.
2. Detect the Linux distribution.
3. Generate a new server config.
4. Back up the existing config file if present.
5. Upload the new config.
6. Restart the managed service.
7. Open the generated TCP port in common local firewall tools when available.
8. Return a generated connection URL.

## Tests

```bash
python -m pytest
```

## Remaining work

- Clean sensitive values from Git history.
- Rewrite the Vue frontend to call `/api/deploy` with `X-API-Key`.
- Decide whether to keep or remove the PyQt client.
- Add an explicit installer plugin for preparing empty servers.
