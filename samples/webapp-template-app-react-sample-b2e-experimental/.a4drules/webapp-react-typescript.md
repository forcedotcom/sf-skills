---
description: Strict TypeScript standards for type-safe React applications
paths:
  - "**/webapplications/**/*"
---

## Type Safety Rules

### Never Use `any`
```typescript
// FORBIDDEN
const data: any = await fetchData();
```

## React TypeScript Patterns

### Event Handlers
```typescript
const handleSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
  event.preventDefault();
};
```

### State and Hooks
```typescript
// Type useState properly
const [user, setUser] = useState<User | null>(null);
```

### GraphQL via DataSDK

See **webapp-react.md** for DataSDK usage patterns. Type your GraphQL responses:

```typescript
const response = await sdk.graphql?.<GetAccountsQuery>(QUERY, variables);
```

### Type Assertions
```typescript
// FORBIDDEN: Unsafe assertions
const user = data as User;

// REQUIRED: Type guards
function isUser(obj: unknown): obj is User {
  return typeof obj === 'object' && obj !== null && typeof (obj as User).id === 'string';
}

if (isUser(data)) {
  console.log(data.name); // Now safely typed
}
```
