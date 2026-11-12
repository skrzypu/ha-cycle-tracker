# Tasks

## 1. Home Assistant MCP prerequisites (manual, user-owned)

- [x] 1.1 In Home Assistant, open the profile page → **Security** → **Long-lived access tokens** → **Create token** with an administrator account; verify the token is shown once and copied
- [x] 1.2 Create the secrets directory and file: `mkdir -p ~/.secrets && chmod 700 ~/.secrets`, save the token to `~/.secrets/ha_mcp_token`, then `chmod 600 ~/.secrets/ha_mcp_token`; verify `stat -c '%a' ~/.secrets/ha_mcp_token` prints `600`
- [x] 1.3 Verify the token against the API: `curl -fsS -H "Authorization: Bearer $(cat ~/.secrets/ha_mcp_token)" http://192.168.0.215:8123/api/`; verify the response is the API running message
- [x] 1.4 Enable the MCP server: **Settings** → **System** → **AI** → **Model Context Protocol** → **Enable**, copy the **Main URL** (`/api/mcp`); verify the URL is reachable with the same bearer token
- [x] 1.5 Enable read-only mode: **Settings** → **Devices & services** → **Model Context Protocol** → **Configure** → **Read-only** on; verify a write tool is rejected when the server is queried with a mutating request

## 2. Docker installation (manual, user-owned)

- [x] 2.1 Install Docker Engine from the official repository (or `curl -fsSL https://get.docker.com | sh` on a disposable dev machine); verify `docker --version` prints a version
- [x] 2.2 Allow the current user to run Docker without `sudo`: `sudo usermod -aG docker $USER`, then log out and back in; verify `docker run --rm hello-world` completes without `sudo`
- [x] 2.3 Verify the daemon starts on boot: `systemctl is-enabled docker` and `systemctl is-active docker`; both must report enabled and active

## 3. OpenDesign container (manual, user-owned)

- [x] 3.1 Confirm the image's documented data directory and port from its README before the first run; record both in the README development section
- [x] 3.2 Start the container: `docker run -d --name open-design --restart unless-stopped -p 127.0.0.1:7456:7456 -v open-design-data:<documented-data-dir> ghcr.io/nexu-io/od:latest`; verify `docker ps` shows `open-design` as running and bound to `127.0.0.1:7456`
- [x] 3.3 Verify the web surface: `curl -fsS http://127.0.0.1:7456/ >/dev/null`; verify it returns success
- [x] 3.4 Verify the MCP entrypoint inside the container: `docker exec -i open-design node /app/apps/daemon/dist/cli.js --help`; verify it prints usage rather than an error
- [x] 3.5 Record the exact `docker run` command and the data volume name in `README.md`; verify the documented command reproduces the running container after `docker rm -f open-design`

## 4. opencode MCP configuration

- [x] 4.1 Add `mcp.servers.homeassistant` to `opencode.json` with `type: remote`, `url: http://192.168.0.215:8123/api/mcp`, `oauth: false`, `headers.Authorization: Bearer {file:~/.secrets/ha_mcp_token}`, and `disabled: true`; verify `python3 -c "import json;json.load(open('opencode.json'))"` succeeds and the entry uses the same shape `opencode mcp add` writes
- [x] 4.2 Add `mcp.servers.opendesign` with `type: local`, `command: ["docker","exec","-i","open-design","node","/app/apps/daemon/dist/cli.js","mcp"]`, and `disabled: true`; verify the JSON parses and no secret appears in the file
- [x] 4.3 Add permission rules that allow `homeassistant_*` and `opendesign_*` and deny mutating tools (`homeassistant_call_service` if exposed, `opendesign_delete_*`); verify the rules are ordered so the deny wins, matching the last-match-wins rule
- [x] 4.4 Verify the config is accepted: run `opencode run --standalone --agent orchestrator "reply with the word ok"`; verify it completes with no configuration warning on stderr — note that `opencode mcp list` reports only global servers in 2.1.4 and is not evidence for project entries
- [x] 4.5 Set the `homeassistant` entry to enabled and run a standalone session that calls a read tool (for example the configuration or state tool) against `http://192.168.0.215:8123`; verify it returns real Home Assistant data, then set `disabled: true` again
- [x] 4.6 With OpenDesign running, enable the `opendesign` entry and list its tools; verify the server starts, record the exact tool names in the README, then set `disabled: true` again

## 5. Secret hygiene

- [x] 5.1 Verify no token or header value is tracked: `git grep -n "Bearer "` shows only the `{file:~/.secrets/ha_mcp_token}` reference; verify `git status` lists no secret file
- [x] 5.2 Verify `~/.secrets/ha_mcp_token` is outside the repository and readable only by the owner; record the rotation procedure in the README

## 6. Documentation

- [x] 6.1 Add a "Development tooling" section to `README.md` covering: HA MCP enablement and Read-only, token creation and storage, Docker installation, the OpenDesign run command, how to enable and disable each MCP entry, and the data-exposure warning
- [x] 6.2 Verify every command in the section matches the command actually run and the `<documented-data-dir>` placeholder is explained
- [x] 6.3 Cross-link ADR-0002 and ADR-0003 from the section so the rationale is one click away

## 7. Validation

- [x] 7.1 Run `openspec validate dev-mcp-tooling --strict`; verify it passes with `skip_specs: true` and reports no missing artifacts
- [x] 7.2 Verify the change touched no file under `custom_components/` and no product spec; `git status` must show only `opencode.json` and `README.md` from this change
