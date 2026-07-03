# ESLint Tier 2: Configurable Rules

[← Back to ESLint Rules Discovery](eslint-rules-discovery.md)

## Tier 2: Configurable Rules

When no built-in rule exists but the pattern is generic (ban a function, ban a property, ban a syntax construct):

### Option A: `no-restricted-globals`

Ban specific global functions or variables.

**Example: Ban setTimeout/setInterval**
```javascript
// eslint.config.js
module.exports = [
  {
    files: ["**/lwc/**/*.js"],
    rules: {
      "no-restricted-globals": ["error",
        {
          name: "setTimeout",
          message: "Use LWC lifecycle hooks instead of setTimeout"
        },
        {
          name: "setInterval",
          message: "Use LWC lifecycle hooks instead of setInterval"
        }
      ]
    }
  }
];
```

**Example: Ban window.localStorage**
```javascript
rules: {
  "no-restricted-globals": ["error",
    {
      name: "localStorage",
      message: "Use Salesforce state management instead of localStorage"
    }
  ]
}
```

### Option B: `no-restricted-syntax`

Ban specific AST patterns using ESLint selectors.

**Example: Ban eval() calls**
```javascript
rules: {
  "no-restricted-syntax": ["error",
    {
      selector: "CallExpression[callee.name='eval']",
      message: "eval() is forbidden for security reasons"
    }
  ]
}
```

**Example: Ban innerHTML property access**
```javascript
rules: {
  "no-restricted-syntax": ["error",
    {
      selector: "MemberExpression[property.name='innerHTML']",
      message: "innerHTML is forbidden - use textContent or render() for XSS prevention"
    }
  ]
}
```

**Example: Ban for-in loops**
```javascript
rules: {
  "no-restricted-syntax": ["error",
    {
      selector: "ForInStatement",
      message: "for-in loops are forbidden - use for-of or Object.keys()"
    }
  ]
}
```

#### ESLint Selector Syntax Cheat Sheet

| Pattern | Selector | Example |
|---|---|---|
| Function call | `CallExpression[callee.name='functionName']` | `eval()`, `alert()` |
| Property access | `MemberExpression[property.name='propName']` | `obj.innerHTML` |
| Statement type | `ForInStatement`, `WithStatement` | for-in, with statements |
| Operator | `BinaryExpression[operator='==']` | `==` instead of `===` |
| Literal value | `Literal[value='string']` | Specific string literals |

**Full selector docs:** https://eslint.org/docs/latest/extend/selectors

### Option C: `no-restricted-properties`

Ban specific object properties.

**Example: Ban Object.prototype methods**
```javascript
rules: {
  "no-restricted-properties": ["error",
    {
      object: "Object",
      property: "setPrototypeOf",
      message: "setPrototypeOf is forbidden for performance reasons"
    }
  ]
}
```
