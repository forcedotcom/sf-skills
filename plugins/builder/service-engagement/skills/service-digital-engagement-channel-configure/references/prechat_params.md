# Pre-chat parameters

## Standard parameters
Generate `<standardParameters>` elements with `parameterType`.

## Custom parameters
Generate `<customParameters>` elements with `name`, `masterLabel`, `parameterDataType`, `externalParameterName`, and `maxLength`. Always set `parameterDataType` to `String`: the channel accepts no other value. The field's actual type (Checkbox, Number, dropdown) is set at the deployment level via `formFieldType`, not here.

## Flow variable mappings
If the channel uses Flow routing and the user specifies flow variable mappings, include `<actionParameterMappings>` with `actionParameterName` to map each parameter to a flow input variable.
