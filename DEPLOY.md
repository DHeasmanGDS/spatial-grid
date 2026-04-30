# Deploying spatial-grid

Target: `https://tools.smcg-services.com`, on the same k3s cluster as `app.terra-datasystems.com`. Pattern mirrors `geo_nlp_portal/k8s/geonlp-deployment.yaml`.

## Architecture

```
internet
   │
   ▼
Cloudflare edge (TLS terminates here)
   │
   ▼
cloudflared tunnel  (running on / near the NUC)
   │
   ▼  http://localhost:30090
NodePort 30090  →  Service spatial-grid-service  →  Pod (Streamlit on 8501)
```

No image registry, no ingress controller, no cert-manager — Cloudflare Tunnel does the routing and TLS.

## First-time deploy (do once)

### 1. Build and import the image on the NUC

```bash
git clone https://github.com/DHeasmanGDS/spatial-grid.git
cd spatial-grid
docker build -t spatial-grid:latest .
docker save spatial-grid:latest | sudo k3s ctr images import -
```

`docker save | k3s ctr images import` is the same trick `~/deploy.sh` uses for geonlp-portal — it's how local images become available to k3s without a registry.

### 2. Apply the manifest

```bash
kubectl apply -f k8s/spatial-grid-deployment.yaml
kubectl rollout status deployment/spatial-grid-deployment
```

Verify it's serving on the NodePort:

```bash
curl -sI http://localhost:30090/_stcore/health
# expect: HTTP/1.1 200 OK
```

### 3. Add the Cloudflare Tunnel public hostname

In the Cloudflare dashboard:

- **Zero Trust → Networks → Tunnels → `<your tunnel>` → Public Hostname → Add a public hostname**
- Subdomain: `tools`
- Domain: `smcg-services.com`
- Service: `HTTP` → `localhost:30090`
- **Additional application settings → HTTP Settings → Disable Chunked Encoding: off** (default fine)
- **Additional application settings → Connection: HTTP2 origin: off** (Streamlit's websocket prefers HTTP/1.1; if the map doesn't render, this is the first knob to check)

Cloudflare auto-creates the DNS record. Browse to `https://tools.smcg-services.com` — should land on the Streamlit app.

## Subsequent deploys

Once `~/deploy.sh` on the NUC is extended to watch this repo (see below), pushing to `main` is enough — the cron-driven loop rebuilds, re-imports, and rolls out within ~5 min.

## Wire into ~/deploy.sh

Your existing `~/deploy.sh` watches `geo_nlp_portal`. Add a parallel block:

```bash
# (sketch — paste into ~/deploy.sh, adapt paths)

REPO_DIR=~/repos/spatial-grid
SHA_FILE=~/.spatial_grid_deployed_sha
IMAGE=spatial-grid:latest
DEPLOYMENT=spatial-grid-deployment

cd "$REPO_DIR"
git pull origin main --quiet

CURRENT_SHA=$(git rev-parse HEAD)
DEPLOYED_SHA=$(cat "$SHA_FILE" 2>/dev/null || echo "")

if [ "$CURRENT_SHA" != "$DEPLOYED_SHA" ]; then
    echo "[$(date)] spatial-grid: deploying $CURRENT_SHA"
    docker build -t "$IMAGE" . \
        && docker save "$IMAGE" | sudo k3s ctr images import - \
        && kubectl rollout restart deployment "$DEPLOYMENT" \
        && echo "$CURRENT_SHA" > "$SHA_FILE"
else
    echo "[$(date)] spatial-grid: no change ($CURRENT_SHA)"
fi
```

## Manual rollback

```bash
# Roll back to the previous ReplicaSet:
kubectl rollout undo deployment/spatial-grid-deployment

# Or to a specific image (if you rebuilt locally with a tag):
kubectl set image deployment/spatial-grid-deployment spatial-grid=spatial-grid:<sha>
```

## Operations

```bash
kubectl get pods -l app=spatial-grid                         # check pod status
kubectl logs -l app=spatial-grid,component=web --tail=100    # tail logs
kubectl logs -l app=spatial-grid,component=web -f            # follow
kubectl describe deployment spatial-grid-deployment          # events / probe / scale
```

If a request reaches the pod but the page doesn't render, suspect:
1. **Cloudflare Tunnel HTTP/2 origin** — Streamlit websockets need HTTP/1.1 origin.
2. **CORS / XSRF** — if you change the Dockerfile to drop `--server.enableCORS=false` or `--server.enableXsrfProtection=false`, Cloudflare's host rewrite will block the websocket.
3. **NodePort collision** — `kubectl get svc` to confirm 30090 is free.

## Resource sizing

The defaults (150m / 384Mi requests, 1000m / 768Mi limits) are conservative. Streamlit holds the rendered map + dataframes in session memory; a 21×41 grid (the example) is well under 100MB. If you launch a UI session that generates a 100×500 grid, expect a few hundred MB.

## Future tools at tools.smcg-services.com

The plan is for this subdomain to host a small fleet of geo tools. Convention:

- One Deployment + one Service per tool.
- NodePorts incrementing from 30090 (this one): 30091, 30092, ...
- Each tool gets its own Cloudflare Tunnel public hostname under `tools.smcg-services.com/<tool>` *or* its own subdomain `<tool>.smcg-services.com`.
- For path-based routing (`tools.smcg-services.com/grid`, `/something-else`), Cloudflare Tunnel doesn't do path rewriting natively — you'd want a small reverse proxy (Caddy, Traefik in tunnel-only mode) on the NUC, or stick with subdomain-per-tool, which is simpler.

For v0.1 the simplest play is `tools.smcg-services.com` = spatial-grid; later either move spatial-grid to `grid.smcg-services.com` and put a landing page at `tools.smcg-services.com`, or do path routing with a sidecar proxy.
