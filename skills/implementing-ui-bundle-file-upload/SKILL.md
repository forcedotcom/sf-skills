---
name: implementing-ui-bundle-file-upload
description: "Add file upload functionality to React UI bundles with progress tracking and Salesforce ContentVersion integration. Use when the user wants to upload files, attach documents, handle file input, create file dropzones, track upload progress, or link files to Salesforce records. This feature provides programmatic APIs ONLY — no components or hooks are exported. Build your own custom UI using the upload() API. ALWAYS use this feature instead of building file upload from scratch with FormData or XHR."
---

# File Upload API (workflow)

When the user wants file upload functionality in a React UI bundle, follow this workflow. This feature provides **APIs only** — you must build the UI components yourself using the provided APIs.

## CRITICAL: This is an API-only package

The package exports **programmatic APIs**, not React components or hooks. You will:

- Use the `upload()` function to handle file uploads with progress tracking
- Build your own custom UI (file input, dropzone, progress bars, etc.)
- Track upload progress through the `onProgress` callback

**Do NOT:**

- Expect pre-built components like `<FileUpload />` — they are not exported
- Try to import React hooks like `useFileUpload` — they are not exported
- Look for dropzone components — they are not exported

The source code contains reference components for demonstration, but they are **not available** as imports. Use them as examples to build your own UI.

## 1. Install the package

```bash
npm install @salesforce/ui-bundle-template-feature-react-file-upload
```

Dependencies are automatically installed:

- `@salesforce/ui-bundle` (API client)
- `@salesforce/sdk-data` (data SDK)

## 2. Understand the three upload patterns

### Pattern A: Basic upload (no record linking)

Upload files to Salesforce and get back `contentBodyId` for each file. No ContentVersion record is created.

**When to use:**

- User wants to upload files first, then create/link them to a record later
- Building a multi-step form where the record doesn't exist yet
- Deferred record linking scenarios

```tsx
import { upload } from "@salesforce/ui-bundle-template-feature-react-file-upload";

const results = await upload({
  files: [file1, file2],
  onProgress: (progress) => {
    console.log(`${progress.fileName}: ${progress.status} - ${progress.progress}%`);
  },
});

// results[0].contentBodyId: "069..." (always available)
// results[0].contentVersionId: undefined (no record linked)
```

### Pattern B: Upload with immediate record linking

Upload files and immediately link them to an existing Salesforce record by creating ContentVersion records.

**When to use:**

- Record already exists (Account, Opportunity, Case, etc.)
- User wants files immediately attached to the record
- Direct upload-and-attach scenarios

```tsx
import { upload } from "@salesforce/ui-bundle-template-feature-react-file-upload";

const results = await upload({
  files: [file1, file2],
  recordId: "001xx000000yyyy", // Existing record ID
  onProgress: (progress) => {
    console.log(`${progress.fileName}: ${progress.status} - ${progress.progress}%`);
  },
});

// results[0].contentBodyId: "069..." (always available)
// results[0].contentVersionId: "068..." (linked to record)
```

### Pattern C: Deferred record linking (record creation flow)

Upload files without a record, then link them after the record is created.

**When to use:**

- Building a "create record with attachments" form
- Record doesn't exist until form submission
- Need to upload files before knowing the final record ID

```tsx
import {
  upload,
  createContentVersion,
} from "@salesforce/ui-bundle-template-feature-react-file-upload";

// Step 1: Upload files (no recordId)
const uploadResults = await upload({
  files: [file1, file2],
  onProgress: (progress) => console.log(progress),
});

// Step 2: Create the record
const newRecordId = await createRecord(formData);

// Step 3: Link uploaded files to the new record
for (const file of uploadResults) {
  const contentVersionId = await createContentVersion(
    new File([""], file.fileName),
    file.contentBodyId,
    newRecordId,
  );
}
```

## 3. Build your custom UI

The package provides the backend — you build the frontend. Here's a minimal example:

```tsx
import {
  upload,
  type FileUploadProgress,
} from "@salesforce/ui-bundle-template-feature-react-file-upload";
import { useState } from "react";

function CustomFileUpload({ recordId }: { recordId?: string }) {
  const [progress, setProgress] = useState<Map<string, FileUploadProgress>>(new Map());

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);

    await upload({
      files,
      recordId,
      onProgress: (fileProgress) => {
        setProgress((prev) => new Map(prev).set(fileProgress.fileName, fileProgress));
      },
    });
  };

  return (
    <div>
      <input type="file" multiple onChange={handleFileSelect} />

      {Array.from(progress.entries()).map(([fileName, fileProgress]) => (
        <div key={fileName}>
          {fileName}: {fileProgress.status} - {fileProgress.progress}%
          {fileProgress.error && <span>Error: {fileProgress.error}</span>}
        </div>
      ))}
    </div>
  );
}
```

## 4. Track upload progress

The `onProgress` callback fires multiple times for each file as it moves through stages:

| Status         | When                                           | Progress Value       |
| -------------- | ---------------------------------------------- | -------------------- |
| `"pending"`    | File queued for upload                         | `0`                  |
| `"uploading"`  | Upload in progress (XHR)                       | `0-100` (percentage) |
| `"processing"` | Creating ContentVersion (if recordId provided) | `0`                  |
| `"success"`    | Upload complete                                | `100`                |
| `"error"`      | Upload failed                                  | `0`                  |

**Always provide visual feedback:**

- Show file name
- Display current status
- Render progress bar for "uploading" status
- Show error message if status is "error"

## 5. Cancel uploads (optional)

Use an `AbortController` to allow users to cancel uploads:

```tsx
const abortController = new AbortController();

const handleUpload = async (files: File[]) => {
  try {
    await upload({
      files,
      signal: abortController.signal,
      onProgress: (progress) => console.log(progress),
    });
  } catch (error) {
    console.error("Upload cancelled or failed:", error);
  }
};

const cancelUpload = () => {
  abortController.abort();
};
```

## 6. Link to current user (special case)

If the user wants to upload files to their own profile or personal library:

```tsx
import {
  upload,
  getCurrentUserId,
} from "@salesforce/ui-bundle-template-feature-react-file-upload";

const userId = await getCurrentUserId();
await upload({ files, recordId: userId });
```

## API Reference

### upload(options)

Main upload API that handles complete flow with progress tracking.

```typescript
interface UploadOptions {
  files: File[];
  recordId?: string | null; // If provided, creates ContentVersion
  onProgress?: (progress: FileUploadProgress) => void;
  signal?: AbortSignal; // Optional cancellation
}

interface FileUploadProgress {
  fileName: string;
  status: "pending" | "uploading" | "processing" | "success" | "error";
  progress: number; // 0-100 for uploading, 0 for other states
  error?: string;
}

interface FileUploadResult {
  fileName: string;
  size: number;
  contentBodyId: string; // Always available
  contentVersionId?: string; // Only if recordId was provided
}
```

**Returns:** `Promise<FileUploadResult[]>`

### createContentVersion(file, contentBodyId, recordId)

Manually create a ContentVersion record from a previously uploaded file.

```typescript
async function createContentVersion(
  file: File,
  contentBodyId: string,
  recordId: string,
): Promise<string | undefined>;
```

**Parameters:**

- `file` — File object (used for metadata like name)
- `contentBodyId` — ContentBody ID from previous upload
- `recordId` — Record ID for FirstPublishLocationId

**Returns:** ContentVersion ID if successful

### getCurrentUserId()

Get the current user's Salesforce ID.

```typescript
async function getCurrentUserId(): Promise<string>;
```

**Returns:** Current user ID

## Common UI patterns

### File input with button

```tsx
<input type="file" multiple accept=".pdf,.doc,.docx,.jpg,.png" onChange={handleFileSelect} />
```

### Drag-and-drop zone

Build your own dropzone using native events:

```tsx
function DropZone({ onDrop }: { onDrop: (files: File[]) => void }) {
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    onDrop(files);
  };

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      style={{ border: "2px dashed #ccc", padding: "2rem" }}
    >
      Drop files here
    </div>
  );
}
```

### Progress bar

```tsx
{
  progress.status === "uploading" && (
    <div style={{ width: "100%", background: "#eee" }}>
      <div
        style={{
          width: `${progress.progress}%`,
          background: "#0176d3",
          height: "8px",
        }}
      />
    </div>
  );
}
```

## Decision tree for agents

**User asks for file upload functionality:**

1. **Ask about record context:**
   - "Do you want to link uploaded files to a specific record, or upload them first and link later?"

2. **Based on response:**
   - **Link to existing record** → Use Pattern B with `recordId`
   - **Upload first, link later** → Use Pattern A (no recordId), then Pattern C for linking
   - **Link to current user** → Use Pattern B with `getCurrentUserId()`

3. **Build the UI:**
   - Create file input or dropzone (not provided by package)
   - Add progress display for each file (status + progress bar)
   - Handle errors in the UI

4. **Test the implementation:**
   - Verify progress callbacks fire correctly
   - Check that `contentBodyId` is returned
   - If `recordId` was provided, verify `contentVersionId` is returned

## Reference implementation

The package includes a reference implementation in `src/features/fileupload/` with:

- `FileUpload.tsx` — Complete component with dropzone and dialog
- `FileUploadDialog.tsx` — Progress tracking dialog
- `FileUploadDropZone.tsx` — Drag-and-drop zone
- `useFileUpload.ts` — React hook for state management

**These are NOT exported** but can be viewed as examples. Read the source files to understand patterns for building your own UI.

## Troubleshooting

**Upload fails with CORS error:**

- Ensure the UI bundle is properly deployed to Salesforce or running on `localhost`
- Check that the org allows the origin in CORS settings

**No progress updates:**

- Verify `onProgress` callback is provided
- Check that the callback function updates React state correctly

**ContentVersion not created:**

- Verify `recordId` is provided to `upload()` function
- Check that the record ID is valid and exists in the org
- Ensure user has permissions to create ContentVersion records

**Files upload but don't appear in record:**

- Verify `recordId` is correct
- Check that ContentVersion was created (look for `contentVersionId` in results)
- Confirm user has access to view files on the record

## DO NOT do these things

- ❌ Build XHR/fetch upload logic from scratch — use the `upload()` API
- ❌ Try to import `<FileUpload />` component — it's not exported
- ❌ Try to import `useFileUpload` hook — it's not exported
- ❌ Use third-party file upload libraries when this feature exists
- ❌ Skip progress tracking — always provide user feedback
- ❌ Ignore errors — always handle and display error messages
