# Architecture

foremanctl is a deployment tool for Foreman and Katello that uses Podman quadlets and Ansible. It wraps [obsah](https://github.com/theforeman/obsah), which turns Ansible playbook directories into CLI subcommands with persistent parameters.

## System Overview

```
                    ┌──────────────────────────────────────┐
                    │           User Interface             │
                    │                                      │
                    │  foremanctl deploy ...                │
                    │  foremanctl checks                   │
                    │  foremanctl health                   │
                    │  foremanctl features                  │
                    │  foremanctl backup / restore          │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────┐
                    │             obsah                     │
                    │                                      │
                    │  - Discovers playbooks via            │
                    │    metadata.obsah.yaml                │
                    │  - Maps directories to CLI commands   │
                    │  - Manages parameter persistence     │
                    │  - Invokes Ansible with extra_vars   │
                    └──────────────┬───────────────────────┘
                                   │
          ┌────────────────────────▼────────────────────────┐
          │               Ansible Playbooks                 │
          │                                                 │
          │  vars_files (layered):                          │
          │    defaults → flavor → certs → images →         │
          │    tuning → database → foreman → logging → base │
          │                                                 │
          │  Roles applied in dependency order              │
          └──────┬──────────┬────────────┬─────────────────┘
                 │          │            │
       ┌─────────▼──┐  ┌───▼────┐  ┌───▼──────────┐
       │ Podman      │  │ System │  │ Native       │
       │ Quadlets    │  │ Config │  │ Packages     │
       │             │  │        │  │              │
       │ .container  │  │ certs  │  │ httpd        │
       │ .image      │  │ secrets│  │ podman       │
       │ sockets     │  │ systemd│  │ dependencies │
       └─────────────┘  └────────┘  └──────────────┘
```

## Dual CLI

Two shell scripts share the same obsah engine, inventory, and state directory but point at different Ansible data directories:

| Script | `OBSAH_DATA` | Purpose |
|---|---|---|
| `foremanctl` | `src/` | Production deployment |
| `forge` | `development/` | Development, testing, CI |

Both scripts set `OBSAH_PERSIST_PARAMS=true`, causing obsah to save CLI parameters to `.var/lib/foremanctl/parameters.yaml` across invocations. This means users only need to pass flags like `--tuning` or `--add-feature` once.

## Directory Layout

```
foremanctl-3/
├── foremanctl                 # Production CLI entry point
├── forge                      # Development CLI entry point
├── setup-environment          # Bootstrap: venv, pip deps, collections
├── src/                       # Production Ansible data
│   ├── ansible.cfg
│   ├── playbooks/             # CLI commands (one dir = one subcommand)
│   ├── roles/                 # Ansible roles
│   ├── vars/                  # Layered variable files
│   ├── features.yaml          # Feature registry
│   ├── features.d/            # Additional feature definitions
│   ├── filter_plugins/        # Jinja2 filters (feature resolution, etc.)
│   ├── callback_plugins/      # Custom Ansible output formatting
│   └── plugins/modules/       # Custom Ansible modules
├── development/               # Development Ansible data
│   ├── ansible.cfg            # roles_path includes ../src/roles
│   ├── playbooks/             # Dev-only CLI commands
│   ├── roles/                 # Dev-only roles
│   └── vars/                  # Dev overrides
├── inventories/               # Ansible inventory (localhost, broker.py)
├── tests/                     # pytest + testinfra test suite
├── .ansible-lint-rules/       # Custom lint rules
└── docs/                      # Documentation
```

## obsah Integration

obsah scans `OBSAH_DATA/playbooks/` for subdirectories. Each directory containing a `metadata.obsah.yaml` becomes a CLI subcommand. Directories prefixed with `_` are include-only and contribute parameters to other commands without being exposed as standalone subcommands.

### metadata.obsah.yaml

Metadata files define the CLI interface for each subcommand:

```yaml
help: |
  Description shown in --help output
variables:
  var_name:
    parameter: --cli-flag
    help: Help text for this parameter
    choices: [a, b, c]
    type: AbsolutePath
    action: store_true
    persist: false         # Don't save across runs
constraints:
  required_together: [[cert, key, ca]]
  required_if: [['database_mode', 'external', ['database_host']]]
include:
  - _other_playbook        # Pull in variables from another metadata file
```

### CLI Commands

**Production (`foremanctl`):**

| Command | Purpose |
|---|---|
| `deploy` | Full server installation (default flavor: katello) |
| `deploy-proxy` | Foreman proxy content installation |
| `checks` | Pre-deployment validation |
| `health` | Runtime health checks |
| `features` | List enabled and available features |
| `pull-images` | Pull container images |
| `backup` | Offline backup of databases, state, and content |
| `restore` | Restore from backup |
| `migrate` | Migrate from foreman-installer |
| `auth-bundle` | Generate authentication bundle for a proxy |

**Development (`forge`):**

| Command | Purpose |
|---|---|
| `deploy-dev` | Deploy with git-based Foreman (not containerized) |
| `test` | Generate SSH config and run pytest |
| `vms` | Manage Vagrant VMs |
| `smoker` | Run smoke tests |
| `setup-repositories` | Configure package repos on VMs |
| `custom-certs` | Generate test certificates |
| `remote-database` | Set up external database VM |
| `mock-installer` | Mock foreman-installer for migration testing |
| `fetch-bundle` | Fetch auth bundle from quadlet VM |

## Variable System

Variables are loaded as Ansible `vars_files` in a fixed order that establishes precedence (later files override earlier ones):

```
1. defaults.yml          Base defaults (database_mode, certificates_source, etc.)
2. flavors/<flavor>.yml  Feature set and checks for this deployment flavor
3. certificates.yml      Certificate file paths derived from FQDN
4. images.yml            Container image names and tags
5. tuning/<profile>.yml  Resource requirements and service tuning
6. database.yml          Database credentials (auto-generated), connection params
7. foreman.yml           Admin credentials, OAuth keys (auto-generated)
8. logging.yml           Log level mappings
9. base.yaml             Computed/derived variables (connects certs to services,
                         resolves features to plugins via filter functions)
```

### Key Computed Variables

- `enabled_features`: `flavor_features + features` (computed in `defaults.yml`)
- `all_databases`: `databases | databases_for_features(enabled_features)` (only databases needed by enabled features)
- Plugin lists: resolved from features via filter functions with transitive dependency handling

## Feature System

Features are the central configuration abstraction. They control which services, plugins, and databases get deployed.

### Feature Registry

`src/features.yaml` and `src/features.d/*.yaml` define the feature catalog:

```yaml
katello:
  description: Content and Subscription Management plugin for Foreman
  foreman:
    plugin_name: katello
  hammer: katello
  dependencies:
    - tasks
    - pulp
    - candlepin
```

Each feature can declare:
- `foreman.plugin_name` -- Foreman Rails plugin to enable
- `foreman_proxy.plugin_name` -- Smart Proxy plugin to enable
- `hammer` -- Hammer CLI plugin to enable
- `dependencies` -- other features required transitively
- `conflicts` -- mutually exclusive features
- `internal: true` -- hidden from users, used only for dependency resolution

### Feature Lifecycle

1. Flavors define `flavor_features` (base feature set for katello or foreman-proxy-content)
2. Users add/remove features via `--add-feature` / `--remove-feature` (persisted across runs)
3. `enabled_features = flavor_features + features`
4. Filter functions resolve enabled features to plugin names, handling transitive dependencies
5. Roles gate deployment with `enabled_features | has_feature('name')` conditions
6. Database creation is gated per-feature via `databases_for_features()`

### Flavors

| Flavor | Base Features |
|---|---|
| `katello` | foreman, katello, content/ansible, content/container, content/deb, content/python, content/rpm |
| `foreman-proxy-content` | foreman-proxy, content/rpm, content/deb, content/container, content/ansible, content/python, templates, registration |

### Tuning Profiles

Resource profiles set minimum CPU/RAM requirements and service-specific tuning (httpd workers, postgresql memory, candlepin JVM):

`default`, `development`, `medium`, `large`, `extra-large`, `extra-extra-large`

## Container Deployment

All services (except httpd) run as Podman containers managed via systemd quadlet units.

### Quadlet Pattern

Roles deploy containers through a consistent pattern:

1. **Image quadlet**: `.image` unit files in `/etc/containers/systemd/` define which images to pull
2. **Container quadlet**: `containers.podman.podman_container` with `state: quadlet` generates `.container` unit files that systemd converts to services
3. **Secrets**: Credentials stored as Podman secrets, mounted into containers via `type=mount` or `type=env`
4. **Ordering**: Quadlet options specify `After=` for dependency ordering and `PartOf=foreman.target` for lifecycle grouping

### Service Architecture

```
                         foreman.target
                              │
           ┌──────────────────┼──────────────────────┐
           │                  │                      │
     ┌─────▼─────┐    ┌──────▼──────┐        ┌──────▼──────┐
     │ PostgreSQL │    │   Valkey    │        │    httpd     │
     │ (quadlet)  │    │  (quadlet)  │        │  (native)   │
     └─────┬──────┘    └──────┬──────┘        └──────┬──────┘
           │                  │                      │
     ┌─────▼──────────────────▼──┐            ┌──────▼──────┐
     │       Candlepin           │            │ Reverse     │
     │       (quadlet)           │            │ proxy to    │
     └───────────────────────────┘            │ Foreman,    │
                                              │ Pulp,       │
     ┌───────────────────────────┐            │ Candlepin   │
     │       Foreman             │◄───────────┘             │
     │  - foreman (Puma)         │            └─────────────┘
     │  - dynflow-sidekiq@*      │
     │  - foreman-db-migrate     │
     │  - foreman-rake-*         │
     └───────────────────────────┘
     ┌───────────────────────────┐
     │         Pulp              │
     │  - pulp-api               │
     │  - pulp-content           │
     │  - pulp-worker@*          │
     │  - pulpcore-manager-      │
     │    migrate                │
     └───────────────────────────┘
     ┌───────────────────────────┐
     │     Foreman Proxy         │
     │       (quadlet)           │
     │  + plugin drop-ins        │
     └───────────────────────────┘
     ┌───────────────────────────┐
     │     IOP Microservices     │
     │  (dedicated network)      │
     │  kafka, ingress, puptoo,  │
     │  engine, gateway,         │
     │  inventory, advisor, ...  │
     └───────────────────────────┘
```

### Networking

- Most services use `network: host`
- IOP services communicate over a dedicated Podman network (`iop-core-network`)
- Foreman and Pulp use Unix sockets for httpd reverse proxying (e.g., `/run/httpd.foreman.sock`)
- systemd socket activation manages the socket lifecycle

### Systemd Integration

- All services belong to `foreman.target` via `WantedBy=default.target foreman.target` and `PartOf=foreman.target`
- Template units (e.g., `dynflow-sidekiq@`, `pulp-worker@`) use systemd template instances with symlinks for scaling
- Oneshot containers (e.g., `foreman-db-migrate`, `pulpcore-manager-migrate`) run database migrations before the main service starts
- Drop-in directories (e.g., `/etc/containers/systemd/foreman-proxy.container.d/`) add per-feature configuration

## Secret Management

All secrets are auto-generated on first run and persisted:

1. `ansible.builtin.password` lookup generates passwords/keys on first invocation
2. Generated values are stored as files in `.var/lib/foremanctl/` (the obsah state directory)
3. Containers receive secrets via Podman secrets (both environment variables and mounted files)

This covers database passwords, OAuth consumer key/secret, Foreman encryption key, and admin credentials.

## Role Structure

Roles follow consistent conventions:

```
roles/
└── <role_name>/
    ├── defaults/main.yml      # Role-specific defaults
    ├── tasks/
    │   ├── main.yml           # Primary task file
    │   └── image.yaml         # Image quadlet deployment (if applicable)
    ├── handlers/main.yml      # Restart handlers
    └── templates/             # Config file templates
```

### Role Categories

**Core services**: `foreman`, `candlepin`, `pulp`, `postgresql`, `valkey`, `httpd`, `foreman_proxy`, `hammer`

**IOP microservices**: `iop_core`, `iop_network`, `iop_kafka`, `iop_ingress`, `iop_puptoo`, `iop_yuptoo`, `iop_engine`, `iop_gateway`, `iop_inventory`, `iop_advisor`, `iop_remediation`, `iop_vmaas`, `iop_vulnerability`, `iop_cvemap_downloader`, `iop_vex_downloader`, `iop_advisor_frontend`, `iop_inventory_frontend`, `iop_vulnerability_frontend`, `iop_fdw`

**Infrastructure**: `pre_install`, `post_install`, `systemd_target`, `images`, `certificates`, `certificate_checks`, `auth_bundle`, `oauth_from_bundle`, `backup`, `restore`, `migrate_foreman_installer`, `debug_tools`

**Checks**: `checks`, `check_features`, `check_hostname`, `check_database_connection`, `check_database_index`, `check_system_requirements`, `check_subuid_subgid`, `check_podman_network_backend`, `check_services`, `check_foreman_api`, `check_foreman_tasks`, `check_host_facts_count`, `check_duplicate_permissions`

## Filter Plugins

`src/filter_plugins/foremanctl.py` provides Jinja2 filters used throughout playbooks and roles:

| Filter | Purpose |
|---|---|
| `features_to_foreman_plugins` | Resolve feature names to Foreman plugin names (with transitive deps) |
| `features_to_hammer_plugins` | Resolve features to Hammer CLI plugin names |
| `features_to_foreman_proxy_plugins` | Resolve features to Smart Proxy plugin names |
| `has_feature` | Check if a feature is enabled (supports prefix matching and transitive deps) |
| `databases_for_features` | Filter database list to only those needed by enabled features |
| `list_all_features` | Format feature table for CLI output |
| `invalid_features` / `conflicting_features` | Validation helpers |

## Deploy Playbook Flow

The `deploy` command applies roles in this order:

1. `pre_install` -- install podman, skopeo, dependencies
2. `checks` -- run pre-deployment checks from the flavor's `checks_to_execute` list
3. `certificates` -- generate or extract CA, server, and client certificates
4. `certificate_checks` -- validate certificate/key/CA consistency
5. `postgresql` -- deploy PostgreSQL container (internal database mode only)
6. `valkey` -- deploy Valkey container
7. `candlepin` -- deploy Candlepin container
8. `httpd` -- install and configure Apache httpd
9. `foreman` -- deploy Foreman container, Dynflow sidekiq workers, db-migrate
10. `pulp` -- deploy Pulp API/content/worker containers, db-migrate
11. `systemd_target` -- create `foreman.target` grouping
12. `iop_core` -- deploy IOP microservices (if `iop` feature enabled)
13. `foreman_proxy` -- deploy Foreman Proxy (if `foreman-proxy` feature enabled)
14. `hammer` -- configure Hammer CLI (if `hammer` feature enabled)
15. `post_install` -- display credentials, mark install complete

## Custom Ansible Lint Rules

`.ansible-lint-rules/` enforces project conventions:

| Rule | Enforcement |
|---|---|
| `no_static_secrets` | Password/secret/token variables must use Jinja expressions, not static strings |
| `use_has_feature_filter` | Conditions must use `enabled_features \| has_feature('x')` not `'x' in enabled_features` |
| `no_empty_defaults` | Role defaults must not have empty/null values |
| `explicit_volume_mode` | Container volume mounts must specify mode explicitly |
| `foreman_oauth_only` | OAuth variables must use the `foreman_` namespace prefix |

## Test Infrastructure

Tests use pytest with testinfra to validate deployed state over SSH:

```
tests/
├── conftest.py                # Fixtures, feature detection, flavor auto-deselection
├── *_test.py                  # Integration tests (playbooks, certs, health, etc.)
├── feature/                   # Per-feature tests (auto-skip when feature disabled)
│   ├── foreman/
│   ├── katello/
│   ├── iop/
│   └── ...
├── flavor/                    # Per-flavor tests (auto-deselect for non-matching flavor)
│   ├── katello/
│   └── foreman-proxy-content/
├── unit/                      # Filter plugin, check role, migration module tests
└── ansible_lint/              # Custom lint rule validation with fixtures
```

`forge test` generates `.tmp/ssh-config` from the Ansible inventory before invoking pytest. The `conftest.py` parses `foremanctl features` output to determine which features are enabled and auto-skips tests for disabled features.

## Development Workflow

The `development/` directory mirrors `src/` and extends it:

- `development/ansible.cfg` sets `roles_path = ./roles:../src/roles`, so development playbooks reuse production roles
- Development-only roles (e.g., `foreman_development` for git-based Foreman, `setup_repositories`) live in `development/roles/`
- The `forge` CLI provides commands for VM management, testing, and dev environment setup

See [Development](developer/development-environment.md) for environment setup details.
