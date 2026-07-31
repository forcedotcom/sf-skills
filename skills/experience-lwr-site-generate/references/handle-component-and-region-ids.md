# UUID Generation

**Use when** handling IDs for components and regions of views. All component and region IDs in Experience Site content must be unique UUIDs.

## Requirements

1. **Format**: Lowercase UUID v4 (e.g., `5d56a22f-c1e8-40d3-92ec-6e10e71e36de`)
2. **Uniqueness**: Must be unique across ALL `content.json` files in site (under `digitalExperiences/site/<SITE_NAME>/`)

## For New content.json Files Only

**Multistep Process (REQUIRED)**:

- **CRITICAL**: Each step must be performed separately - do NOT combine steps into a single automated command or script
- **Step 1**: Create files with descriptive placeholders for UUIDs (e.g., `UUID_CONTENT_REGION`, `UUID_HIDDEN_REGION`, `UUID_SEO_COMPONENT`)
- **Step 2**: Count the total number of UUID placeholder occurrences in the generated file, then generate exactly that many UUIDs using:
  - `node -e "console.log(Array.from({length: N}, () => require('crypto').randomUUID()).join('\n'))"` where N is the total count of placeholder occurrences. Present this command to the user for execution.
- **Step 3**: Replace each placeholder occurrence sequentially with the generated UUIDs from the list, ensuring each occurrence gets a unique UUID from the list. Perform replacements one at a time or in small batches - do NOT automate this with scripts.
- **Step 4**: Validate that all placeholders have been replaced - read the file and search for any remaining placeholder patterns (e.g., `UUID_`). The file is NOT valid until all placeholders are replaced with actual UUIDs.
- **CRITICAL**: Every single placeholder occurrence must be replaced with a DIFFERENT UUID from the generated list, even if the placeholder name is repeated. For example, if you have 5 total placeholder occurrences, generate 5 UUIDs and replace each occurrence with the next UUID from the list.
- **NEVER** write UUIDs inline during file creation - always use the multistep placeholder approach

## For Editing Existing content.json Files

- **CRITICAL**: Read file first and preserve all existing UUIDs exactly as-is
- NEVER replace existing UUIDs with placeholders
- For newly added components/regions only, follow the multistep placeholder process from step 3
