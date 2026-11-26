# Railway production demo

One service serves the compiled React workspace at `/`, offline FastAPI under `/api`, and health at `/health`. The optional historical jury view lives at `/demo/`. The Docker build uses Node 24 and Python 3.12 and installs the application from locked runtime dependencies in a non-root image. Only compiled frontend assets enter the final image. The CLI runs independently with `python -m specguard`.

## Release and deploy

Railway CLI authentication is required. From an authenticated account, verify the target workspace and its plan. Obtain the owner's approval before starting a deployment or attaching a volume that could incur charges.

1. In Railway create a project and choose **Deploy from GitHub repo**. Grant access to the private **DiasRamazanov/specguard-ai** repository. Select the reviewed **codex/release-integration** branch, or **main** after its integration PR is merged. Set the root to the repository root. Use the repository Dockerfile and railway.toml. Disable PR environments and use one replica.
2. Set **SPECGUARD_LIVE=0**. The platform supplies **PORT**. **SPECGUARD_FRONTEND_DIR** defaults to frontend/dist inside the image. The public service refuses to start with live inference enabled. Keep **DEEPSEEK_API_KEY** out of the public service. No external LLM consent can override that restriction.
3. For a workspace-only demo, deploy without a volume. To publish the previously completed audit, first confirm permission to share its source with the intended viewers. Attach a volume at **/archive**. In the linked Railway project and environment, upload only the four permitted files. Set **SPECGUARD_DEMO_DIR=/archive** after uploading. The non-root process (UID 10001) must have read access to these files. If permissions need changing, adjust the files in the service volume before enabling the archive. The application validates the archive when loading.
4. Under **Settings → Networking**, generate a public domain targeting the application port. Verify health before sending the HTTPS address to jurors. Their workspace URL is the domain root. Their historical audit URL ends in **/demo/**. It identifies the prior live run and offers traceable requirements, findings, contradictions and the original Markdown download.

From the owner's Mac with the Railway CLI installed, choose the correct project, environment and service with `railway link`. Replace VOLUME_NAME with the volume name shown by Railway.

```sh
railway login
railway whoami
railway link
```

```sh
cd "/Users/diasramazanov/Downloads/MNU HACK/.worktrees/release"
archive="/Users/diasramazanov/Downloads/SpecGuard AI Review and Release/official"
for f in audit.json requirements.md verification.json report.md; do
  railway volume files --volume VOLUME_NAME upload "$archive/$f" "/$f" || break
done
```

## Verify the running service

```sh
export SPECGUARD_TEST_URL=https://YOUR-SERVICE.up.railway.app
curl -fsS "$SPECGUARD_TEST_URL/health"
curl -fsS "$SPECGUARD_TEST_URL/demo/report.md" | shasum -a 256
cd frontend
npm ci
npx playwright install chromium
npx playwright test --config playwright.production.config.ts
```

The official report digest is `3fa9cef9aef328bc6a6277b280e13c7c8ef1c3185c2a4ea173d02a9e70f93d97`. The production suite exercises real offline uploads, polling, source navigation, reports, Copilot attachments and mobile controls using synthetic documents. The error-state test injects an HTTP failure in the browser. Run the 13-state harness locally using `npm run e2e` in the development checkout. Production must return 404 for /dev/spec-states.html and /src/dev/SpecStates.tsx.

## Runtime limits and recovery

Clients receive HTTP 202 and poll the audit status. Background jobs, uploaded documents and anonymous sessions live in one process. Sessions expire after one hour. Restarting clears them and interrupts active jobs. Retry by creating a new session and uploading the originals. An individual cancellation endpoint is unavailable. Two audit slots and two parser slots bound work. The ingress accepts uploads up to 5 MiB, limits API traffic, and returns 429 under pressure. Request access logging is disabled to keep filenames, session details and uploaded text out of request logs. Anonymous users share 24 session slots for one hour. The global rate limit alone cannot guarantee availability for a jury under hostile traffic. Restrict interactive workspace traffic at the edge for an invited demo or use the read-only /demo/ archive, which uses no session slots. Keep authorized paid runs in the trusted backend environment with explicit consent and durable SQLite quota reservations. The public image needs no provider credits.

Use Railway's deployment history to redeploy the verified commit or roll back to the previous healthy deployment. Review the selected branch SHA and health response after either operation. Mounted volumes persist independently. Retain an external copy of the verified archive. Rolling back application code does not restore volume files.

## Estimated cost

At listed Railway rates, 0.25 GB average memory, 0.02 average vCPU and 0.1 GB occupied disk for one month would use about USD 2.92 before egress. Actual CPU and memory depend on document size and activity. Hobby has a USD 5 monthly minimum including usage. The Free plan includes USD 1 of usage per month. Check the workspace's actual allowance before deployment. [Railway pricing](https://docs.railway.com/pricing) · [Volumes](https://docs.railway.com/volumes/reference)

## Run the submission locally

Build from the release checkout. For the owner's Mac, this command mounts the existing archive read-only and runs as the local user so owner-only report files remain readable. On another machine, adjust the archive path. The workspace opens at http://127.0.0.1:8080/ and the recorded jury audit at http://127.0.0.1:8080/demo/.

```sh
docker build -t specguard-jury .
archive="$HOME/Downloads/SpecGuard AI Review and Release/official"
docker run --rm -p 127.0.0.1:8080:8080 --user "$(id -u):$(id -g)" \
  --mount "type=bind,source=$archive,target=/archive,readonly" \
  -e SPECGUARD_DEMO_DIR=/archive specguard-jury
```
