# Utility Bar FlexiPage

A UtilityBar FlexiPage referenced by a CustomApplication's `utilityBar`. Save it before the app.

## Page template

```xml
<FlexiPage xmlns="http://soap.sforce.com/2006/04/metadata">
    <flexiPageRegions>
        <itemInstances>
            <componentInstance>
                <componentName>console:history</componentName>
                <identifier>console_history</identifier>
            </componentInstance>
        </itemInstances>
        <name>utilityItems</name>
        <type>Region</type>
    </flexiPageRegions>
    <flexiPageRegions>
        <name>backgroundComponents</name>
        <type>Background</type>
    </flexiPageRegions>
    <masterLabel>Support Console UtilityBar</masterLabel>
    <template>
        <name>one:utilityBarTemplateDesktop</name>
    </template>
    <type>UtilityBar</type>
</FlexiPage>
```

## Recent Items item

`flexipage:recentItems` fails to save without these properties ("missing required decorator property [label]"). Decorator properties keep their plain name and add `<type>decorator</type>`. `entityNames` is a `valueList`, not a string. Add this `componentInstance` under the `utilityItems` region's `itemInstances`:

```xml
<componentInstance>
    <componentInstanceProperties><name>eager</name><type>decorator</type><value>false</value></componentInstanceProperties>
    <componentInstanceProperties>
        <name>entityNames</name>
        <valueList>
            <valueListItems><value>Case</value></valueListItems>
            <valueListItems><value>Contact</value></valueListItems>
        </valueList>
    </componentInstanceProperties>
    <componentInstanceProperties><name>height</name><type>decorator</type><value>480</value></componentInstanceProperties>
    <componentInstanceProperties><name>icon</name><type>decorator</type><value>fallback</value></componentInstanceProperties>
    <componentInstanceProperties><name>label</name><value>Standard.RecentItems</value></componentInstanceProperties>
    <componentInstanceProperties><name>label</name><type>decorator</type><value>Recent Items</value></componentInstanceProperties>
    <componentInstanceProperties><name>maxRecords</name><value>3</value></componentInstanceProperties>
    <componentInstanceProperties><name>scrollable</name><type>decorator</type><value>true</value></componentInstanceProperties>
    <componentInstanceProperties><name>width</name><type>decorator</type><value>340</value></componentInstanceProperties>
    <componentName>flexipage:recentItems</componentName>
    <identifier>flexipage_recentItems</identifier>
</componentInstance>
```
