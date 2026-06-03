# BaseCapability

Common interface implemented by every mobile native capability. Use `isAvailable()` to gate code paths so the LWC degrades gracefully on unsupported surfaces (desktop, mobile web).

```typescript
/*
 * Copyright (c) 2024, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

/**
 * Provide all services with common functionalities.
 */
export interface BaseCapability {
  /**
   * Use this function to determine whether the respective service functionality is available.
   * @returns Returns true when used on a supported device and false otherwise.
   */
  isAvailable(): boolean;
}
```
