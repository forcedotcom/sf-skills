## 📊 Data Expert Analysis Framework

### Analysis Focus

Analyze all data flow patterns, state management, and data binding mechanisms in the Aura component.

### Key Areas to Review

#### 1. Attribute Analysis

- Document all `<aura:attribute>` declarations with their types and access levels
- Identify public vs private attributes and their usage patterns
- Note default values and their significance
- Check for complex object types that may need restructuring

#### 2. Data Binding Patterns

- Find all `{!v.attributeName}` expressions in markup
- Document two-way vs one-way data binding usage
- Identify computed expressions and complex binding logic
- Note any performance-critical binding patterns

#### 3. Event Data Flow

- Analyze data passed through component and application events
- Document event payloads and their structure
- Identify parent-child data communication patterns
- Note any data transformation in event handlers

#### 4. External Data Sources

- Identify server-side controller methods and their data patterns
- Document API calls and their data handling
- Note any caching or data persistence mechanisms
- Check for reactive data patterns that need LWC equivalents

### Migration Considerations

- Aura attributes become LWC `@api` and `@track` properties
- Data binding syntax changes from `{!v.prop}` to `{prop}`
- Event data structures may need modification for LWC
- Server integration moves from Apex controllers to LWC wire services

### Additional knowledge

#### Data requirements for the 'force:RecordData' component analysis

Your task is to ensure that all data needs are properly documented in a framework-agnostic way within a component's blueprint, focusing on the "what" and "why" of data requirements rather than implementation specifics.
Concept:
The `aura:attribute` used to declare component variables. These component variables can be used for storing data, modifying and rendering them in the UI.
Component variables can also be programmatically modified by the javascript controllers and javascript helpers by referencing them using `v.*` inside `component.get('v.*')` and `component.set('v.*', value)`.
The `force:recordData` component is used to fetch Salesforce Records from the server and store the result in the aura variables.
The `force:recordData` has attributes are used for passing data. The `force:recordData` attributes can be specified inline or can be assigned to the component variables.
Remove aura specific terminology from dataRequirements in the blueprint.
To properly extract the values of the aura variables you must carefully follow controller javascript code and helper javascript code using variable reference.

Review Aura component above and fix its blueprint using following rules:

1. Blueprint dataRequirements **MUST NOT contain `force:recordData`**
2. Review blueprint data requirements and add any missing aura variable used by `force:recordData` components
   - Review and analyze each `force:RecordData` component
   - Trace all component variables used by `force:RecordData`
   - Analyze each component variable to understand:
     - What data is being stored inside the variable
     - How the data is being loaded
     - How is this variable modified inside javascript
3. Analyze each `force:recordData` component and update blueprint if needed
   - For the `recordId` attribute:
     - find its corresponding component variable and the dataRequirements
     - review the "what" section and make sure it says 'The Record Id of the Salesforce Record.'
     - review the "why" and make sure it says 'To load Salesforce Records from the Salesforce database'
     - review the "source" and set it to be in 'Salesforce Records Database - {aura:id}' format
   - For `targetRecord` attribute:
     - find its corresponding component variable and the dataRequirements
     - review the "what" and make sure it says: 'The object representing a Salesforce Record in the {force:recordData.mode} mode'. Also insert all the list of all the fields loaded for this record.
     - review the "why" and make sure it contains the intent, why the record is needed
     - review the "source" and set it to be in 'Salesforce Records Database - {aura:id}' format
   - For the `targetFields` attribute:
     - find its corresponding component variable and the dataRequirements
     - analyze all component and javascript code to extract the list of the fields needed for loading the record
     - review the "what" and update it to make sure that it contains the list of ALL the field values used by the component variable.
     - review the "why" and make sure it says 'To have a simple access to the record fields collection'
     - review the "source" and set it to be in 'Salesforce Records Database - {aura:id}' format
   - For the `fields` attribute:
     - find its corresponding component variable and the dataRequirements
     - analyze all component and javascript code and extract the list of the fields used for loading the record
     - review the "what" and update it to make sure that it contains the list of ALL the field values used by the component variable.
     - review the "why" and make sure it says 'To specify the list of the record fields to load'
     - review the "source" and set it to be in 'Salesforce Records Database - {aura:id}' format
   - For `targetError` attribute:
     - find its corresponding component variable and the dataRequirements
     - review the "what" and make sure it contains the purpose of the variable
     - review the "why" and make sure it contains the intent, why the record is needed
     - review the "source" and set it to be in '{force:recordData.aura:id}' format
   - If the aura component implements `force:hasSObjectName` and if you are not able to get the sobject name from the component files, add it into "unknowns" in the blueprint, otherwise add into the record dataRequirement.
4. Remove aura-specific terminology from dataRequirements in the blueprint
   - Find and replace the all mentions of `force:recordData` inside dataRequirements "source" with the following formatted string like 'Salesforce Records Database - {aura:id}'.
   - Rename `sObjectName` in the dataRequirements to `objectApiName` to help with LWC.

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.

#### Data requirements for the 'lightning:recordViewForm' component analysis

Your task is to ensure that all data needs are properly documented in a framework-agnostic way within a component's blueprint, focusing on the "what" and "why" of data requirements rather than implementation specifics.

Concept:
The `aura:attribute` used to declare component variables. These component variables can be used for storing data, modifyin and rendering them in the UI.
Compnent variables can also be programmaticaly modified by the javascript controllers and javascript helpers by referencing them using `v.*` inside `component.get("v.*")` and `component.set("v.*", value)`.
The `lightning:recordViewForm` component is used to fetch Salesforce Records data from the server and store the result in the aura variables.
The `lightning:recordViewForm` has attributes are used for passing data. The `lightning:recordViewForm` attributes can be specified inline or can be assigned to the component variables.
The `lightning:outputField` inside the `lightning:recordViewForm` is used to display the field on a record
To properly extract the values of the aura variables you must to carefully follow controller javascript code and helper javascript code using variable reference.

Review Aura component above and fix its blueprint using following rules:

1. Blueprint dataRequirements **MUST NOT contain `lightning:recordViewForm`**
2. Review blueprint data requirements and add any missing aura variable used by `lightning:recordViewForm` components
   - Review and analyze each `lightning:recordViewForm` component
   - Trace all component variables used by `lightning:recordViewForm`
   - Analyze each component variable to understand
     - What data is being stored inside the variable
     - How the data is being loaded
     - How is this variable modified inside javascript
3. Analyze each `lightning:recordViewForm` component and update blueprint if needed
   - Create a new section named "record" in "dataRequirements" section to indicate what record we need to fetch from Salesforce Records Database
     - find its corresponding variable `recordId` and "object api name",
     - analyze all component and javascript code and extract the name of the object API name used for loading the record.
     - review the "what" and update it to make sure that it contains the list of ALL the fields values used by the component variable by analyzing `lightning:outputField`, please do not generate new section for each field.
     - review the "why" and make sure it says 'To specify the record to load'
     - review the "source" and set it to be in 'Salesforce Records Database' format
   - If the aura component implements `force:hasSObjectName` and if you are not able to get the sobject name from the component files, add it into "unknowns" in the blueprint, otherwise add into the objectApiName dataRequirement.
4. Remove aura-specific terminology from dataRequirements in the blueprint\*\*
   - Find and replace the all mentions of `lightning:recordViewForm` inside dataRequirements
   - Rename `sObjectName` in the dataRequirements to `objectApiName` to help with LWC.

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.

#### Apex Controller Analysis

Your task is to ensure that all data needs are properly documented in a framework-agnostic way within a component's blueprint, focusing on "source" of data requirements with the controller code.
Concept:
The `controller="*"` declared in `<aura:component>` indicates the apex controller name of the component.
The `aura:attribute` is used to declare component variables.
These component variables can be used for storing data, modifying and rendering them in the UI.
Component variables can also be programmatically modified by the javascript controllers and javascript helpers by referencing them using `v.*` inside `component.get('v.*')` and `component.set('v.*', value)`.
`c.*` indicates the component is calling the client-side controller which is the `*Controller.js` file in the component. You will need to read .js code and find the name of the server-side controller. And analyze the input parameter and the output shape.

Review Aura component above and fix its blueprint using following rules:

1. To properly extract the values of the aura variables you must carefully follow controller javascript code and helper javascript code using variable reference.
2. Review the data in dataRequirements one by one.
3. If one of the data has default value set in the cmp file, you must mention it in the source field of this data. If it's a component variable like `v.*`, please mention it without `v.`.
4. If one of data's source is fetched from apex controller, make sure including the apex controller name and the method name in this field of the current data.
5. Analyze the input and output shape of the apex method and add into the source field if the data source is fetched from apex controller.
6. Review the `*Helper.js` and `*Controller.js` file of the component to learn the data flow of the data, for example, if the Apex output is an object, what field of the Apex output data does the current variable need, and if the sub-field is still an object, how's that data flow, for example, Id, Name, etc fields. Add the dataflow into the source field.
7. During the analysis, if you find any data like fieldName in controller file that need to be retrieved by object api name and you are not able to tell from the component, please add to "unknown" section in the blueprint with the field name.
8. Review "unknowns" section in the blueprint, if any of the refs is the apex controller of this component and it's handled by this reviewer, please remove the item from "unknowns" in the good blueprint.

Review Criteria

- Are all data sources documented?
- Do all data sources with Apex Controller contain the method and controller names, and the input and output shapes?
- Is Apex controller used in this component removed from "unknowns" in the good blueprint?
- Is the data flow between the apex controller and the client-side controller mentioned in the good blueprint?
- Is the object api name field added into "unknown" secontion in the blueprint as needed?
- Is the terminology framework agnostic?
- Are intent and purpose of dataRequirements clearly defined?

* For each issue found, provide a separate, detailed report.
* Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
