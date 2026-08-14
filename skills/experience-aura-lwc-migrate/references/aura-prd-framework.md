# Framework to generate a PRD/Blueprint for an Aura Component

Generate a detailed blueprint for the provided Aura component using the following schema. Ensure that all sections of the blueprint are filled out accurately and comprehensively, covering every aspect of the component's design, functionality, and requirements.

Before filling in the schema, inspect the component bundle files (`.cmp`, `.controller.js`, `.helper.js`, `.renderer.js`, `.css`, `.design`, `.evt`, `.intf`) that the caller has provided. Extract the component name, the `access` attribute from the `.cmp` metadata, and every embedded or referenced component. Use those findings to populate the sections below.

## Instructions:

1. **Component Overview**:

   - Provide a clear and concise description of the component's purpose.
   - Explain how the component fits into the larger application or system.
   - State the component's access attribute as declared in its metadata in the blueprint overview description and context (e.g., access="GLOBAL"). If the access level is GLOBAL, clearly mention that the component is publicly available and can be used across different namespaces. If the access level is PRIVILEGED, PUBLIC, or any other value, explicitly describe its restrictions and where it can be used.

2. **Static References**:

   - List all static references (labels, resources, assets, URLs) required by the component.
   - Include the purpose and importance of each reference.

3. **Content Requirements**:

   - Detail the content elements required by the component.
   - List each embedded component within the host component separately and for each, provide a clear description of its purpose, the referencing approach used, and the nature of its interaction or communication within the host component's context.
   - Specify what needs to be displayed, why it is necessary, and any constraints.

4. **Data Requirements**:

   - Specify the data elements needed by the component.
   - Include their source (e.g., public property, event payload, global data provider) and how they are used.

5. **Interactions**:

   - Describe all user interactions supported by the component.
   - Include what triggers the interaction, what it does, and the expected outcome.

6. **Component Communication**:

   - Explain how the component communicates with other parts of the application.
   - Specify what information is sent or received and why.

7. **States**:

   - List the different states the component can be in.
   - Describe what each state represents and why it is important.

8. **Accessibility**:

   - Document all accessibility features required for the component.
   - Include what needs to be done and why.

9. **Responsiveness**:

   - Describe how the component should adapt to different screen sizes or devices.
   - Specify what changes are necessary and why.

10. **Styling**:

    - Outline the styling requirements for the component.
    - Include what styles should be applied and the reasoning behind them.

11. **Localization**:

    - Specify any localization requirements for the component.
    - Include what needs to be localized and why.

12. **Security**:

    - List any security considerations for the component.
    - Include what measures need to be taken and why.

13. **Acceptance Criteria**:

    - Define the criteria for accepting the component as complete.
    - Ensure at least one criterion is provided.

14. **Unknowns**:
    - List any external events, interfaces, controllers or libraries dependencies required by this component to function.
    - Never list the host component itself as an unknown — that creates a circular dependency.
    - If no valid unknowns exist, return an empty array for this section instead of filling it with assumptions about the component.
