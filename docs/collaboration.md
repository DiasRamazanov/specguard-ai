# Working from separate computers

The team’s private remote is [DiasRamazanov/specguard-ai](https://github.com/DiasRamazanov/specguard-ai). Each developer uses their own GitHub account and local clone.

## Teammate access

The owner opens [repository access settings](https://github.com/DiasRamazanov/specguard-ai/settings/access), chooses **Collaborators → Add people**, selects the teammate’s GitHub username and sends the invitation. Accept it with that account, then authenticate Git through your usual credential manager. [GitHub instructions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository)

## Frontend checkout

```bash
git clone --branch feat/frontend https://github.com/DiasRamazanov/specguard-ai.git
cd specguard-ai
git status --short --branch
claude
```

Start Claude Code in the clone root. Open [the REST contract](../contracts/openapi.json), [schemas and fixtures](../contracts), [architecture](architecture.md), [engineering handoff](handoffs/codex.md), and [design references](../references). The offline backend starts without a provider key. See [installation and run commands](../README.md). On Windows use a Linux environment such as WSL for the PDF worker.

## Daily synchronization

Before editing, on the branch you own:

```bash
git fetch --prune origin
git pull --ff-only
```

Commit your changes locally and use `git push origin feat/frontend` for frontend work or `git push origin feat/core-engine` for backend work. If a push is rejected, fetch and inspect the incoming commits; integrate them before an ordinary push. Preserve all published commits. The lead integrates reviewed work into main through a pull request. Shared contract changes should include regenerated JSON files, a fixture or test, and handoff notes. A frontend clone can inspect pending backend changes with `git diff origin/main...origin/feat/core-engine -- contracts/`.

Keep API keys in the backend process environment and local reports outside the Git working tree. The offline mode is sufficient for frontend wiring and demo development. The official issued input and final generated report are separate submission artifacts.
