## 🔧 Resolver Expert Aura Component Analysis and Migration Guide

### Analysis Focus

The goal is to analyze dependency resolution, module loading, and component lifecycle patterns in the Aura component to prepare for migration to LWC.

### Resolving Unknowns

To ensure a successful migration, you must first resolve all "unknowns" listed in the PRD (Product Requirements Document). These unknowns represent dependencies that need to be understood and mapped to LWC equivalents.

**Instructions for Resolving Unknowns:**

1.  **Install Knowledge Package**: Make sure you have the `@sfdc-internal/adk-knowledge` package installed in your project. This package contains the necessary documentation for standard Salesforce components, events, interfaces, and libraries.

    If the package is not available in the caller's workspace, surface the missing dependency as part of the unknowns section rather than failing — note which knowledge file paths you attempted so a human can populate the context manually.

2.  **Locate Knowledge Files**: For each unknown in the PRD, use the following mapping rules to find the corresponding knowledge file within `node_modules/@sfdc-internal/adk-knowledge/dist/`.

#### Knowledge File Mapping Rules:

1. **Controller References**: For unknowns like "serviceComponent://ui.global.components.one.header.HeaderController"

   - Extract the path: ui.global.components.one.header.HeaderController
   - Look for: node_modules/@sfdc-internal/adk-knowledge/dist/controller/one/HeaderController.md
   - Pattern: Extract namespace and controller name, map to dist/controller/{namespace}/{ControllerName}.md

2. **Interface References**: For unknowns like "force:layoutRegionCenterEmbeddable interface"

   - Extract the interface name: layoutRegionCenterEmbeddable
   - Look for: node_modules/@sfdc-internal/adk-knowledge/dist/interfaces/force/layoutRegionCenterEmbeddable.md
   - Pattern: dist/interfaces/{namespace}/{interfaceName}.md

3. **Event References**: For unknowns like "force:showOnboardingPrompt event type"

   - Extract the event name: showOnboardingPrompt
   - Look for: node_modules/@sfdc-internal/adk-knowledge/dist/events/force/showOnboardingPrompt.json
   - Pattern: dist/events/{namespace}/{eventName}.json

4. **Library References**: For unknowns like "lightning:utilityBarAPI library" or library dependencies

   - Extract the library name: utilityBarAPI
   - Look for: node_modules/@sfdc-internal/adk-knowledge/dist/library/lightning/utilityBarAPI.md
   - Pattern: dist/library/{namespace}/{libraryName}.md

5. **Component References**: For unknowns like "one:systemMessage Component"
   - Extract the component name: one:systemMessage
   - Look for: node_modules/@sfdc-internal/adk-knowledge/dist/components/one/systemMessage/blueprint.json or
     node_modules/@sfdc-internal/adk-knowledge/dist/components/one/systemMessage/enhanced-prd.md
   - Pattern: dist/components/{namespace}/{componentName}/blueprint.json or dist/components/{namespace}/{componentName}/enhanced-prd.md

#### Resolution Steps:

1. Check if @sfdc-internal/adk-knowledge package is available
2. For each unknown in the PRD file:
   - Parse the unknown string to identify type (controller/interface/event/library)
   - Extract namespace and component name
   - Attempt to locate corresponding knowledge file using the mapping rules above
   - If found, include the knowledge content in the analysis and remove the unknown from the PRD file
   - If not found, keep the item as unknown and update the PRD file to note that no knowledge file was available on the knowledge file mapping rules above and call out the path to the knowledge file mapping rules above.
3. **Update the PRD**:
   - **If a knowledge file is found**: Read the file to understand the unknown's functionality. Then, update the PRD to describe what the dependency does and why it is needed. Remove the item from the "unknowns" section.
   - **If a knowledge file is not found**: Note in the PRD that the dependency could not be resolved automatically using the provided knowledge package. You may need to research it manually.

### Key Areas to Review

#### 1. Component Dependencies

- Document all component imports and dependencies
- Identify circular dependencies that need breaking
- Note version compatibility requirements
- Check for optional vs required dependencies

#### 2. Module Loading Patterns

- Analyze dynamic loading of JavaScript modules
- Document lazy loading or code splitting patterns
- Identify any performance optimization strategies
- Note any conditional module loading logic

#### 3. Lifecycle Management

- Document component initialization and cleanup patterns
- Identify any memory management requirements
- Note event listener management and cleanup
- Check for proper resource disposal patterns

#### 4. Error Handling and Recovery

- Analyze error boundary patterns and fallback strategies
- Document graceful degradation mechanisms
- Identify retry logic or recovery procedures
- Note any debugging or diagnostic capabilities

#### 5. Configuration and Environment

- Document environment-specific configuration patterns
- Identify feature flags or conditional functionality
- Note any runtime configuration requirements
- Check for development vs production differences

#### 6. Performance Optimization

- Analyze caching strategies and data persistence
- Document performance monitoring or metrics
- Identify any optimization patterns or techniques
- Note any resource usage considerations

### Migration Considerations

- LWC has different module resolution and import patterns
- Component lifecycle hooks have different names and behaviors
- Error handling patterns may need restructuring
- Performance optimization strategies differ between frameworks
- Configuration patterns need LWC-compatible approaches
- Resolved unknowns should be incorporated into the migration strategy with proper LWC equivalents
