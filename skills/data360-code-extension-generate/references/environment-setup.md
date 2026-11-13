# Environment Setup for Data 360 Code Extensions

Follow only the sections that `scripts/check_env.sh` reported as ❌. Every block checks first and skips anything that's already installed.

Commands are shown for **macOS (Homebrew)**. Linux and Windows notes follow each section. Section 3 covers both single-Python environments (no venv) and machines that need a venv.

**Steps the user must do themselves (the agent stops and asks):**

- installing Homebrew
- `sudo` commands
- installing or starting Docker Desktop
- browser login
- enabling the Code Extension feature

---

## 1. Base tools

### Homebrew (macOS)

```bash
command -v brew >/dev/null 2>&1 && echo "brew present, skipping" || echo "USER ACTION: install Homebrew from https://brew.sh"
```

The Homebrew installer is interactive and asks for a password, so the user has to run it themselves.

### git, Node.js, jq

```bash
for pair in git:git node:node jq:jq; do
  cmd=${pair%%:*}; pkg=${pair##*:}
  command -v "$cmd" >/dev/null 2>&1 && echo "$cmd present, skipping" || brew install "$pkg"
done
```

- Node.js LTS or newer is needed if you install `sf` through npm.
- macOS 15 and later ship `/usr/bin/jq`.
- **Linux:** use `apt`/`dnf install git nodejs jq`. **Windows:** use `winget install Git.Git OpenJS.NodeJS.LTS jqlang.jq`.

### Java

PySpark (used by local `run`) needs a JDK. **JDK 17 is recommended**; PySpark 3.5 also supports 11.

**JDK 21** isn't officially supported by PySpark 3.5 (Spark 4.0 added it), but it's often the only JDK on Ubuntu-based cloud workspaces. Tested with PySpark 3.5.1 on JDK 21:

| Works | Fails |
|---|---|
| The SDK's local read path (`read_dlo`/`read_dmo`, which builds Spark DataFrames from pandas with Arrow), PySpark column functions, Python UDFs, and the printed output of local `run` | `toPandas()` with Arrow fails with `sun.misc.Unsafe or java.nio.DirectByteBuffer.<init>(long, int) not available`. `-Dio.netty.tryReflectionSetAccessible=true` doesn't fix it. pandas UDFs also use Arrow and are likely affected (not tested) |

So on a JDK 21 machine, keep it unless the code needs `toPandas()` or pandas UDFs. Otherwise either install JDK 17 (Linux: `sudo apt install openjdk-17-jdk`, a user action, then `export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64` in the same block as `<PY_ENV>`), or turn Arrow off just before the call: `spark.conf.set("spark.sql.execution.arrow.pyspark.enabled", "false")`. This affects local `run` only; the deployed package doesn't include your local JDK.

```bash
if /usr/libexec/java_home -v 17 >/dev/null 2>&1 || /usr/libexec/java_home -v 11 >/dev/null 2>&1; then
  echo "JDK present: $(/usr/libexec/java_home), skipping"
else
  brew install openjdk@17
  echo "USER ACTION (sudo): sudo ln -sfn \"$(brew --prefix)/opt/openjdk@17/libexec/openjdk.jdk\" /Library/Java/JavaVirtualMachines/openjdk-17.jdk"
fi
```

- PySpark finds Java through `JAVA_HOME`, or else `java` on `PATH`. On macOS, the `/Library/Java/JavaVirtualMachines` symlink above makes `/usr/bin/java` resolve the JDK, so nothing else is needed. To pin a version, add `export JAVA_HOME="$(/usr/libexec/java_home -v 17)"` to the shell profile.
- **Linux:** `apt install openjdk-17-jdk` puts `java` on `PATH`. Cloud workspaces often have no JDK; check with `java -version`.
- **Windows:** install Temurin 17 and set `JAVA_HOME`.

### Docker (deploy only)

```bash
docker info --format '{{.ServerVersion}}' 2>/dev/null || echo "USER ACTION: install/start Docker Desktop (https://www.docker.com/products/docker-desktop/)"
```

Some cloud workspaces can't run Docker. There you can still init, scan and run locally; deploy from a machine that has Docker.

---

## 2. Salesforce CLI

### Install `sf`

```bash
command -v sf >/dev/null 2>&1 && echo "sf present: $(sf --version), skipping" || npm install --global @salesforce/cli
```

Alternatives: `brew install sf`, or the installers at https://developer.salesforce.com/tools/salesforcecli

### Code extension plugin

```bash
sf plugins | grep -q data-code-extension && echo "plugin present, skipping" \
  || sf plugins install @salesforce/plugin-data-code-extension
sf plugins | grep data-code-extension   # expect 1.4.x or newer
```

### Log in to the org (user action)

```bash
sf org display --target-org <ORG_ALIAS> --json 2>/dev/null | jq -e '.result.connectedStatus == "Connected"' >/dev/null \
  && echo "<ORG_ALIAS> connected, skipping" \
  || echo "USER ACTION: sf org login web --instance-url <ORG_URL> --alias <ORG_ALIAS>"
```

- Use the org's My Domain URL (`https://<mydomain>.my.salesforce.com`), or `https://test.salesforce.com` for sandboxes.
- Don't use `--set-default`. Every command passes `--target-org`. (If an org already is the CLI default and Connected, as in Code Builder, `check_env.sh` picks it and the agent writes it explicitly into each command.)
- Verify with `sf org display --target-org <ORG_ALIAS> --json 2>/dev/null | jq '.result | {connectedStatus, username, instanceUrl}'`. Never print `accessToken`.

---

## 3. Python 3.11: system mode or venv mode

The plugin requires **exactly Python 3.11** (any 3.11.x, including pre-releases such as `3.11.0rc1`). It runs whatever `python3` is on `PATH` (falling back to `python`), finds packages through `pip3`/`pip`/`python3 -m pip`, and calls `pipreqs` from `PATH`. PySpark workers also default to `python3`.

So the only question is whether `python3` is already 3.11 and can take package installs:

| | **3a. System mode** | **3b. Venv mode** |
|---|---|---|
| Use when | `python3` is 3.11, `python3 -m pip` works, and the Python isn't externally managed (PEP 668). Typical: cloud dev workspaces, containers, Ubuntu 22.04 images with a single 3.11 | `python3` is another version (typical macOS: 3.12+ from Homebrew), system pip is blocked (Debian 12+, Ubuntu 23.04+), or the user wants isolation |
| Install target | User site-packages (`--user`) | `<PROJECT_DIR>/.venv` |
| `PYSPARK_*` | Not needed (driver and workers are both `python3`) | Added to `.venv/bin/activate` by `scripts/venv_hook.sh` |
| `<PY_ENV>` | `export PATH="<user-base>/bin:$PATH"`, with the literal folder `check_env.sh` prints (for example `/home/codebuilder/.local/bin`) | `source <PROJECT_DIR>/.venv/bin/activate` |

`scripts/check_env.sh` picks the mode automatically and prints `MODE=` and `PY_ENV=`. An existing `.venv` always means venv mode. To force a mode, pass it as the third argument: `bash check_env.sh <PROJECT_DIR> <ORG_ALIAS> venv`.

`PROJECT_DIR` can be an existing, non-empty folder. An SFDX project isn't required for code extensions.

### 3a. System mode (no venv)

```bash
python3 --version                                   # must be 3.11.x
python3 -m pip --version || echo "USER ACTION: install pip for this Python (apt install python3-pip, or python3 -m ensurepip --user)"
<PY_ENV>
python3 -m pip install --user --upgrade salesforce-data-customcode pipreqs
```

- **Always use `python3 -m pip`**, never bare `pip3`. On some images `pip3` belongs to a different Python (for example the distro's 3.10), so packages would land where `python3` can't import them. The plugin's check would still pass, because it accepts the package from any pip, and `run` fails later.
- `--user` installs console scripts such as `pipreqs` into the user-base `bin` folder (`python3 -m site --user-base`, plus `/bin`; usually `~/.local/bin`). `check_env.sh` prints it as a literal path in `PY_ENV`. Agent and non-login shells often don't have it on `PATH`, which is why `<PY_ENV>` adds it. If you install as root or into a writable system Python, drop `--user`; `<PY_ENV>` is then harmless.
- If pip refuses with `externally-managed-environment`, switch to venv mode. Don't use `--break-system-packages`.
- A pre-release such as `3.11.0rc1` passes the plugin's version check and PySpark 3.5 supports 3.11, but it isn't a tested SDK configuration. If you see unexplained interpreter errors, install a final 3.11 release.

Verify:

```bash
<PY_ENV>
python3 -c "import datacustomcode; print(datacustomcode.__file__)"
command -v pipreqs
```

### 3b. Venv mode

Install Python 3.11 alongside the default `python3`. Don't change the system or default `python3`.

```bash
command -v python3.11 >/dev/null 2>&1 && echo "python3.11 present, skipping" || brew install python@3.11
python3.11 --version
```

- **Linux:** use `apt install python3.11 python3.11-venv`, or `pyenv install 3.11`.
- **Windows:** use `py -3.11` from the python.org installer.

Create the venv, pin PySpark to it, and install:

```bash
mkdir -p "<PROJECT_DIR>" && cd "<PROJECT_DIR>"
[ -x .venv/bin/python ] && echo "venv present, skipping" || python3.11 -m venv .venv
bash <SKILL_DIR>/scripts/venv_hook.sh "<PROJECT_DIR>"
source <PROJECT_DIR>/.venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install --upgrade salesforce-data-customcode pipreqs
```

- Use `python3.11 -m venv`, **not `uv venv`**. A `uv` venv has no `pip`, so `pip install` silently installs into the global Python. `uv pip install` has also been seen to hang.
- `venv_hook.sh` appends `PYSPARK_PYTHON` and `PYSPARK_DRIVER_PYTHON` exports to `.venv/bin/activate`, once. Without them, Spark workers pick up the global `python3` and `run` fails with `PYTHON_VERSION_MISMATCH`. Because the hook lives in `activate`, a developer who activates the venv by hand in a terminal gets it too.
- **Recreating the venv regenerates `activate` and drops the hook.** Rerun `venv_hook.sh` afterwards. `check_env.sh` reports it if it's missing.
- **Windows:** `venv_hook.sh` doesn't cover `.venv\Scripts\Activate.ps1` or `activate.bat`. Add `$env:PYSPARK_PYTHON = "$env:VIRTUAL_ENV\Scripts\python.exe"` (and the same for `PYSPARK_DRIVER_PYTHON`) to `Activate.ps1`, or `set` lines to `activate.bat`.
- Add `.venv/` to `.gitignore`.

Verify:

```bash
source <PROJECT_DIR>/.venv/bin/activate
python3 --version                                                   # 3.11.x
python3 -c "import datacustomcode; print(datacustomcode.__file__)"  # path under .venv/
echo "$PYSPARK_PYTHON"                                              # .../.venv/bin/python
```

---

## 4. Org feature: Code Extension (user action, UI only)

There is no API for this. Ask the user to:

1. Open **Data Cloud Setup → Feature Manager**.
2. Turn on **Code Extension**.
3. Confirm back that it's enabled.

## 5. Finish

Rerun `bash <SKILL_DIR>/scripts/check_env.sh "<PROJECT_DIR>" "<ORG_ALIAS>"`. Every line should show ✅. Docker can stay ⚠️ until you deploy. Note the `PY_ENV=` line it prints: that is the `<PY_ENV>` that starts every shell block in SKILL.md.

Optional: connect the hosted Data 360 MCP server (https://developer.salesforce.com/docs/platform/hosted-mcp-servers/overview).
