# Engine Prerequisites

Detailed installation instructions for each Code Analyzer engine's dependencies.

## Summary Table

| Engine | Required Dependencies | Optional |
|--------|----------------------|----------|
| PMD | Java 11+ | Custom ruleset JARs |
| CPD | Java 11+ | — |
| ESLint | Node.js 18+ | Project ESLint config |
| RetireJS | Node.js 18+ | — |
| Regex | None (built-in) | — |
| Flow | Python 3 | — |
| SFGE | Java 11+ (4g+ heap recommended) | — |
| ApexGuru | Authenticated Salesforce org | — |

## Core: Salesforce CLI

**Required for ALL engines.**

### macOS

```bash
# Via Homebrew (recommended)
brew install sf

# Or via npm
npm install -g @salesforce/cli
```

### Windows

```bash
# Via npm
npm install -g @salesforce/cli

# Or download installer from:
# https://developer.salesforce.com/tools/salesforcecli
```

### Linux

```bash
# Via npm
npm install -g @salesforce/cli

# Or via tarball:
# https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_setup_install_cli.htm
```

### Verify

```bash
sf --version
# Expected: @salesforce/cli/2.x.x ...
```

## Code Analyzer Plugin

**Required: sf CLI must be installed first.**

```bash
# Install
sf plugins install @salesforce/plugin-code-analyzer

# Verify
sf code-analyzer --help

# Update to latest
sf plugins install @salesforce/plugin-code-analyzer@latest

# Check version
sf plugins --core | grep code-analyzer
```

## Java 11+ (for PMD, CPD, SFGE)

### macOS

```bash
# Via Homebrew
brew install openjdk@11

# Add to PATH (add to ~/.zshrc or ~/.bash_profile)
export PATH="/opt/homebrew/opt/openjdk@11/bin:$PATH"
export JAVA_HOME="/opt/homebrew/opt/openjdk@11"

# Or via SDKMAN (manages multiple Java versions)
curl -s "https://get.sdkman.io" | bash
sdk install java 11.0.21-tem
```

### Windows

```bash
# Via winget
winget install EclipseAdoptium.Temurin.11.JDK

# Or via Chocolatey
choco install temurin11
```

### Linux

```bash
# Ubuntu/Debian
sudo apt install openjdk-11-jdk

# RHEL/CentOS/Fedora
sudo dnf install java-11-openjdk-devel

# Via SDKMAN (any Linux)
curl -s "https://get.sdkman.io" | bash
sdk install java 11.0.21-tem
```

### Verify

```bash
java -version
# Expected: openjdk version "11.x.x" or higher

echo $JAVA_HOME
# Should point to JDK installation
```

### Troubleshooting Java

| Issue | Solution |
|-------|----------|
| `java: command not found` | Add Java bin dir to PATH |
| Wrong Java version | Set JAVA_HOME explicitly |
| Multiple Java versions | Use `sdk use java 11.x.x` or update PATH order |
| SFGE heap errors | Increase `java_max_heap_size` in config |

## Node.js 18+ (for ESLint, RetireJS)

### macOS

```bash
# Via Homebrew
brew install node@20

# Or via nvm (recommended for version management)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
nvm install 20
nvm use 20
```

### Windows

```bash
# Via winget
winget install OpenJS.NodeJS.LTS

# Or via nvm-windows
# Download from: https://github.com/coreybutler/nvm-windows/releases
nvm install 20
nvm use 20
```

### Linux

```bash
# Via nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
nvm install 20
nvm use 20

# Or via package manager (may be outdated)
# Ubuntu/Debian (use NodeSource for latest):
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### Verify

```bash
node --version
# Expected: v20.x.x or v18.x.x (minimum v18)

npm --version
# Expected: 9.x.x or 10.x.x
```

## Python 3 (for Flow Engine)

**Only needed if you scan Flow files (*.flow-meta.xml).**

### macOS

```bash
# Via Homebrew
brew install python3

# macOS may already have python3 via Xcode Command Line Tools
xcode-select --install
```

### Windows

```bash
# Via winget
winget install Python.Python.3.12

# Or from python.org
# https://www.python.org/downloads/windows/
```

### Linux

```bash
# Usually pre-installed. If not:
# Ubuntu/Debian
sudo apt install python3

# RHEL/CentOS/Fedora
sudo dnf install python3
```

### Verify

```bash
python3 --version
# Expected: Python 3.x.x
```

## Authenticated Org (for ApexGuru)

**Only needed for ApexGuru performance analysis.**

```bash
# Login to a Salesforce org
sf org login web --alias my-org

# Or login with JWT (CI/CD)
sf org login jwt --client-id <id> --jwt-key-file <key> --username <user> --alias my-org

# Verify
sf org display --target-org my-org
```

### Troubleshooting ApexGuru Auth

| Issue | Solution |
|-------|----------|
| `No default org` | Set default: `sf config set target-org my-org` |
| `Session expired` | Re-login: `sf org login web --alias my-org` |
| `Insufficient permissions` | Org needs API access enabled |

## Quick Setup Script

For a complete setup on macOS with Homebrew:

```bash
# Install all prerequisites
brew install node@20 openjdk@11 python3

# Set Java environment
export JAVA_HOME="/opt/homebrew/opt/openjdk@11"
export PATH="/opt/homebrew/opt/openjdk@11/bin:$PATH"

# Install Salesforce CLI
npm install -g @salesforce/cli

# Install Code Analyzer
sf plugins install @salesforce/plugin-code-analyzer

# Verify everything
sf --version
sf plugins --core | grep code-analyzer
java -version
node --version
python3 --version
```
