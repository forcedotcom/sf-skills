# Salesforce Metadata API - Section-Specific Loading Examples

This directory contains working code examples demonstrating how to programmatically load only specific sections from metadata JSON files.

## ⚠️ Critical Warning

**NEVER use built-in tools like Read, cat, or any other tool that loads entire JSON files into context!**

These tools inject the complete file (including verbose WSDL segments and all sections) directly into your context, wasting 60-80% of tokens.

## Available Examples

### 1. Python Example
**File**: [`python_section_loading.py`](./python_section_loading.py)

Demonstrates:
- Loading single section (`fields` only)
- Loading multiple sections (`description` + `fields`)
- Checking available sections first
- What NOT to do

**Usage**:
```bash
python3 examples/python_section_loading.py
```

**Key Pattern**:
```python
import json
with open('data/metadata_api/CustomObject.json') as f:
    data = json.load(f)
    fields_only = data.get('fields', {})  # Only extract 'fields'
```

### 2. JavaScript/Node.js Example
**File**: [`javascript_section_loading.js`](./javascript_section_loading.js)

Demonstrates:
- Synchronous file loading with section extraction
- Multiple sections extraction
- Section checking
- Async/Promise version

**Usage**:
```bash
node examples/javascript_section_loading.js
```

**Key Pattern**:
```javascript
const fs = require('fs');
const data = JSON.parse(fs.readFileSync('data/metadata_api/CustomObject.json', 'utf-8'));
const fieldsOnly = data.fields || {};  // Only extract 'fields'
```

### 3. Bash + jq Example
**File**: [`bash_section_loading.sh`](./bash_section_loading.sh)

Demonstrates:
- Using `jq` to extract specific sections
- Shell-based section filtering
- Field-level extraction
- Section availability checking

**Prerequisites**:
- `jq` must be installed
  - macOS: `brew install jq`
  - Linux: `apt-get install jq` or `yum install jq`
  - Windows: `winget install jqlang.jq` or `choco install jq`

> **Windows note:** The Bash + jq example targets a POSIX shell (use WSL, Git
> Bash, or Cygwin on Windows). For a cross-platform, no-extra-dependency option,
> prefer the Python (`python_section_loading.py`) or JavaScript
> (`javascript_section_loading.js`) examples, which run natively on Windows.

**Usage**:
```bash
chmod +x examples/bash_section_loading.sh
./examples/bash_section_loading.sh
```

**Key Pattern**:
```bash
# Extract only the 'fields' section
jq '.fields' data/metadata_api/CustomObject.json
```

## Token Savings

| Approach | Tokens Used | Savings |
|----------|-------------|---------|
| **❌ Read tool (entire file)** | 500-2,000 | 0% (baseline) |
| **✅ Section-specific loading** | 50-200 | **60-80%** |

## Common Patterns

### Pattern 1: Single Section
Load only the section you need:

```text
CustomObject.json → Extract only 'fields' → Use 200 tokens instead of 2,000
```

### Pattern 2: Multiple Sections
Load 2-3 specific sections:

```text
Flow.json → Extract 'description' + 'fields' → Use 400 tokens instead of 1,500
```

### Pattern 3: Check First, Then Load
Always check what sections are available:

```text
1. Read 'sections' array
2. Determine what's available
3. Load only what you need
```

## What Sections to Load

Choose based on your need:

| Your Need | Load These Sections | Skip These |
|-----------|-------------------|------------|
| **Field definitions** | `fields` | `wsdl_segment`, `declarative_metadata_sample_definition` |
| **Understanding purpose** | `description` | `wsdl_segment`, `file_information` |
| **XML structure examples** | `declarative_metadata_sample_definition` | `wsdl_segment` |
| **Schema validation** | `wsdl_segment` | (rarely needed) |

## Anti-Patterns (What NOT to Do)

### ❌ Wrong: Using Read Tool
```bash
# This loads the ENTIRE file into context (2,000 tokens)
Read data/metadata_api/CustomObject.json
```

### ❌ Wrong: Using cat/type
```bash
# This loads the ENTIRE file into context (2,000 tokens)
cat data/metadata_api/CustomObject.json
type data/metadata_api/CustomObject.json
```

### ✅ Correct: Programmatic Section Extraction
```bash
# This loads only the 'fields' section (200 tokens)
jq '.fields' data/metadata_api/CustomObject.json
```

## Adapting to Other Languages

These patterns work in any language with JSON parsing:

- **Python**: `json.load()` or `json.loads()`
- **JavaScript/Node.js**: `JSON.parse()`
- **Java**: `new Gson().fromJson()` or `new ObjectMapper().readValue()`
- **Go**: `json.Unmarshal()`
- **Ruby**: `JSON.parse()`
- **PHP**: `json_decode()`
- **C#**: `JsonConvert.DeserializeObject()`
- **Bash**: `jq`

The key principle is the same: **parse the JSON, extract only needed sections, ignore the rest**.

## Questions?

See the main [SKILL.md](../SKILL.md) for comprehensive documentation on token optimization strategies and conceptual approaches.
