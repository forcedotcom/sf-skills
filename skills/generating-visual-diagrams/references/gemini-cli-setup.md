<!-- Parent: generating-visual-diagrams/SKILL.md -->
# Gemini CLI Setup for generating-visual-diagrams

## Prerequisites

### 1. Authenticate with Google

```bash
# Start Gemini CLI - opens browser for OAuth
gemini

# Select "Login with Google" when prompted
# Credentials cached at ~/.gemini/oauth_creds.json
```

### 2. Install Nano Banana Extension

```bash
gemini extensions install nanobanana
```

### 3. Install timg for Image Display

```bash
brew install timg
```

### 4. Configure Environment

Add to `~/.zshrc`:

```bash
export NANOBANANA_MODEL=gemini-3-pro-image-preview
export PATH="$HOME/.local/bin:$PATH"
```

---

## Verification

```bash
# Check Gemini CLI
gemini --version

# Check Nano Banana
gemini extensions list

# Check timg
which timg

# Test image generation
gemini "/generate 'A blue circle on white background'"
timg ~/gemini-images/*.png
```

---

## File Locations

| File | Purpose |
|------|---------|
| `~/.gemini/settings.json` | Gemini CLI settings |
| `~/.gemini/oauth_creds.json` | OAuth tokens |
| `~/.gemini/extensions/nanobanana/` | Nano Banana extension |
| `~/gemini-images/` | Generated images |
