# v2ray_auto

This branch is a destructive rewrite of the original project.

## Branch

`refactor/destructive-core-rewrite`

## Project goal

The project goal is one-click deployment on a nearly empty VPS. The deployment flow must be able to bootstrap the target machine, install the managed V2Ray service, write config, restart the service, open the port, and return a generated connection URL.

## What changed

- Root script `v2ray_auto.py` was removed because it conflicts with the new Python package name.
- Runtime configuration moved to environment variables.
- Legacy `config.py` no longer stores credentials.
- Core logic moved to `v2ray_auto/core/`.
- Empty-server bootstrap logic moved to `v2ray_auto/core/installer.py`.
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

## Deployment flow

The refactored service is still designed for one-click deployment on an empty server:

1. Connect to the server with SSH.
2. Detect the Linux distribution.
3. Install basic packages such as curl and certificates.
4. Add a small swap file when memory is too low and no swap exists.
5. Install V2Ray service when `v2ray.service` is missing.
6. Generate a new server config.
7. Back up the existing config file if present.
8. Upload the new config.
9. Restart the managed service.
10. Open the generated TCP port in common local firewall tools when available.
11. Return a generated connection URL.

## Tests

```bash
python -m pytest
```

## Remaining work

- Clean sensitive values from Git history.
- Rewrite the Vue frontend to call `/api/deploy` with `X-API-Key`.
- Decide whether to keep or remove the PyQt client.
- Add more installer tests and failure recovery for partially bootstrapped servers.
