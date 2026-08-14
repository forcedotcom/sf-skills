## 💎 Values Expert Analysis Framework

### Analysis Focus

Analyze default values, configuration patterns, and value initialization in the Aura component.

### Key Areas to Review

#### 1. Default Value Analysis

- Document all attribute default values and their significance
- Identify initialization patterns and timing requirements
- Note any computed default values or dynamic initialization
- Check for environment-specific default value variations

#### 2. Configuration Management

- Analyze configuration attribute patterns and their usage
- Document how configuration values affect component behavior
- Identify any configuration validation or constraint patterns
- Note any hierarchical configuration inheritance

#### 3. Value Validation and Constraints

- Document any validation logic for attribute values
- Identify data type constraints and format requirements
- Note any business rule validation patterns
- Check for error handling of invalid values

#### 4. Value Transformation

- Analyze any value formatting or transformation logic
- Document currency, date, or number formatting patterns
- Identify any localization-specific value handling
- Note any value normalization or sanitization

### Migration Considerations

- Aura default values need equivalent LWC property initialization
- Configuration patterns may need LWC-specific approaches
- Validation logic needs to be migrated to LWC methods
- Value transformation may require different utility approaches

### Additional knowledge

#### Default Values analysis

Your task is to make sure that default values of Aura attributes are assigned to JavaScript properties of LWC component.

Review Aura component above and add default value of the attribute to the "what" property:

1. If default value is a constant, add its type and value even if the value is empty string or null.
   For example for <aura:attribute name="index" type="String" default="0">
   """
   "name": "index",
   "what": "The index of the row being edited. Default value is string \"0\"."
   """

2. If default value points to a static resource, infer namespace and name of the resource, not its value.
   For example for <aura:attribute name="label" default="{!$Label.myOrg.myLabelName}">, default value should be mentioned like so:
   """
   "name": "label",
   "what": "The label next to input. Default value is a label from namespace \"myOrg\" with the name \"myLabelName\"".
   """

- For each issue found, provide a separate, detailed report.
- Keep issues concise, avoid duplicated issues or unnecessary or non-applicable problems.
