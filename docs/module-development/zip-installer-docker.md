# Install and upgrade third-party ZIP modules (Docker and self-hosted)

This branch extends the upstream ZIP installer in **Modules → System Modules**
and exposes the same admin-only panel in **Settings → Modules**.

## How the workflow behaves

1. An administrator selects a ZIP containing a single Python package directory
   (for example `production_register/`) with `__init__.py` and `manifest.py`.
2. The backend checks archive paths, symlinks, archive size and compression ratio,
   manifest identity, dependencies and compatibility, without executing code.
3. The administrator reviews the complete file list and confirms trust.
4. A new module can be installed and enabled in the running server.
5. A higher-version ZIP can **update only an already ZIP-managed module**.
   Bundled or manually installed modules cannot be overwritten.
6. An update replaces files on disk but **does not reload Python in process**.
   Restart the backend/container to activate the new version. Old files are
   preserved under `.<module>.rollback` in the runtime modules directory.

The installer cannot safely sandbox Python. Trust and independently audit a
module before installation. Never install unreviewed third-party code.

## Docker persistence (required)

Set `OE_RUNTIME_MODULES_DIR` to a **writable path backed by a persistent
volume**, for example `/data/modules`, on the **OCERP application container**.
If `/data` is already mounted as a named volume, reuse that mount and set the
environment variable to `/data/modules`. Otherwise add a volume mount for
that path in the deployment configuration. Do not rely on the container's
ephemeral filesystem. `OE_DATA_DIR` does not itself override the module
root; this feature reads `OE_RUNTIME_MODULES_DIR`.

On installations using the default path, runtime modules are stored below
`~/.openestimator/modules`, which may not be persistent in Docker.

Use `docker compose restart <application-service>` after an upgrade, replacing
`<application-service>` with the actual service name. A restart of Redis
or the database does not reload the Python module.

The ZIP payload can contain a `module.json` with `requires_platform`
and an optional hosted UI definition, as documented by the upstream installer.
A frontend page compiled in TypeScript cannot be dynamically injected from a
ZIP without rebuilding the frontend; use the supported hosted-page descriptor
for runtime UI contributions.

## Rollback

If the upgraded module fails after restart, stop the application container,
restore `.<module>.rollback` to `<module>` in the persistent runtime module
directory (first move the failed new directory aside), then start the service.
Do not delete module database tables. Database schema changes require separately
reviewed migrations; ZIP upgrades do not automatically perform destructive
migrations.

Do not upgrade core modules using this feature. In multi-replica deployments
coordinate the rollout and restart **all** application replicas using the same
persistent module artifact and compatible database schema.
