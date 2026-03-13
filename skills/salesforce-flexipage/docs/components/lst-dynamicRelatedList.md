 # Quick Example: Adding Related List

 User request:  Add MyCustomObject related list to the flexipage Parent_Record_Page.flexipage-meta.xml

 Steps:
   1. Read the flexipage file and parse the XML.
   2. Generate unique identifier: `lst_dynamicRelatedList_<childEntityName>_1`
   3. Generate component XML with substitution points:
 ```xml
   <itemInstances>
     <componentInstance>
       <componentName>lst:dynamicRelatedList</componentName>
 
       <!-- SUBSTITUTION POINT: identifier -->
       <!-- PATTERN: lst_dynamicRelatedList_<childEntityName>_<number> -->
       <!-- MUST BE UNIQUE within the flexipage -->
       <identifier>lst_dynamicRelatedList_childEntity_1</identifier>
 
       <componentInstanceProperties>
         <name>actionNames</name>
         <valueList>
           <valueListItems>
             <value>New</value>
           </valueListItems>
         </valueList>
       </componentInstanceProperties>

       <componentInstanceProperties>
         <name>adminFilters</name>
       </componentInstanceProperties>

       <componentInstanceProperties>
         <name>maxRecordsToDisplay</name>
         <value>10</value>
       </componentInstanceProperties>

       <!-- SUBSTITUTION POINT: parentFieldApiName -->
       <!-- PATTERN: <ParentEntityApiName>.Id -->
       <!-- FOR CUSTOM PARENT: ParentObject__c.Id -->
       <!-- ALWAYS ENDS WITH: .Id -->
       <componentInstanceProperties>
         <name>parentFieldApiName</name>
         <value>Parent.Id</value>
       </componentInstanceProperties>

       <!-- SUBSTITUTION POINT: relatedListApiName -->
       <!-- FOR CUSTOM OBJECTS: Use relationshipLabel from lookup field -->
       <!-- ALWAYS ENDS WITH: __r for custom objects -->
       <!-- EXAMPLE: MyCustomObjects__r -->
       <componentInstanceProperties>
         <name>relatedListApiName</name>
         <value>MyCustomObjects__r</value>
       </componentInstanceProperties>

       <componentInstanceProperties>
         <name>relatedListDisplayType</name>
         <value>ADVGRID</value>
       </componentInstanceProperties>

       <!-- SUBSTITUTION POINT: relatedListFieldAliases -->
       <!-- FOR CUSTOM OBJECTS: Field API names ending in __c -->
       <componentInstanceProperties>
         <name>relatedListFieldAliases</name>
         <valueList>
           <valueListItems>
             <value>NAME</value>
           </valueListItems>
           <valueListItems>
             <value>FieldNameOne__c</value>
           </valueListItems>
           <valueListItems>
             <value>FieldNameTwo__c</value>
           </valueListItems>
           <valueListItems>
             <value>FieldNameThree__c</value>
           </valueListItems>
         </valueList>
       </componentInstanceProperties>

       <!-- SUBSTITUTION POINT: relatedListLabel -->
       <!-- PATTERN: Any display string, typically plural child entity name -->
       <componentInstanceProperties>
         <name>relatedListLabel</name>
         <value>My Custom Objects</value>
       </componentInstanceProperties>

       <componentInstanceProperties>
         <name>showActionBar</name>
         <value>true</value>
       </componentInstanceProperties>

       <componentInstanceProperties>
         <name>sortFieldAlias</name>
         <value>__DEFAULT__</value>
       </componentInstanceProperties>

       <componentInstanceProperties>
         <name>sortFieldOrder</name>
         <value>Default</value>
       </componentInstanceProperties>
     </componentInstance>
   </itemInstances>
 ```
   4. Insert into flexipage at end of "main" region.  Append this after the last "itemInstances" element in that region.
   5. Write file
 
 It is now ready to deploy.
 
 ### Critical Rules for Success
 
 **RULE 1: parentFieldApiName**
           - Pattern: `<ParentEntityApiName>.Id`
           - Example: Account__c.Id or Customer__c.Id
           - ALWAYS ends with ".Id"
           - The __c is part of the entity name
 
 **RULE 2: relatedListApiName**
           - Source: Use relationshipLabel from the lookup field in child entity
           - Pattern: ALWAYS ends with "__r"
           - Example: If child is "Subscription__c" → likely "Subscriptions__r"
           - This is the child relationship name for parent-to-child traversal
           - Typically the plural form of child entity + "__r"
 
 **RULE 3: relatedListFieldAliases**
           - For custom objects: Use field API names from child entity
           - Pattern: Custom fields ALWAYS end with "__c"
           - Examine the child entity metadata and find up to three fields that are not NAME fields.  Use the "NAME" field followed by those fields.
 
 **EXAMPLE: multi column list**
 ```xml
 <valueList>
   <valueListItems>
     <value>NAME</value>
   </valueListItems>
   <valueListItems>
     <value>FieldNameOne__c</value>
   </valueListItems>
   <valueListItems>
     <value>FieldNameTwo__c</value>
   </valueListItems>
   <valueListItems>
     <value>FieldNameThree__c</value>
   </valueListItems>
 </valueList>
 ```
 
 **RULE 4: relatedListLabel**
           - Can be any user-friendly string
           - Commonly: Plural form of child entity name without __c
           - Example: "Subscriptions" or "Custom Orders"
           - No strict pattern - use descriptive text

 **INSERTION RULES**
           - This component must be inside its own "itemInstances" element
           - The component must go into the "main" region
           - Insert the new "itemInstances" element after the last existing "itemInstances" element in that region
 
 **Common Mistakes to Avoid:**
 - ❌ Nesting the "itemInstances" element inside another existing "itemInstances" element
 - ❌ Inserting a second "componentInstance" element inside an existing "itemInstances" element
 - ❌ Using field labels instead of API names
 - ❌ Forgetting __c suffix on custom fields
 - ❌ Including the lookup field that defines the relationship
 - ❌ Including more than 10 fields
 
 ### Complete Custom Object Example
 
 **Scenario:** Add "Subscription__c" related list to "Customer__c" record page
 
 **Given:**
 - Parent entity: Customer__c
 - Child entity: Subscription__c
 - Lookup field in Subscription__c: Customer__c (references Customer__c)
 - Lookup field's relationshipLabel: "Subscriptions"
 - Child fields: Name, Status__c, Start_Date__c, Amount__c
 
 **Generated Component:**
 ```xml
  <itemInstances>
    <componentInstance>
      <componentName>lst:dynamicRelatedList</componentName>
      <identifier>lst_dynamicRelatedList_subscriptions_1</identifier>
      <componentInstanceProperties>
        <name>actionNames</name>
        <valueList>
          <valueListItems><value>New</value></valueListItems>
        </valueList>
      </componentInstanceProperties>
      <componentInstanceProperties>
        <name>adminFilters</name>
      </componentInstanceProperties>
      <componentInstanceProperties>
        <name>maxRecordsToDisplay</name>
        <value>10</value>
      </componentInstanceProperties>
      <componentInstanceProperties>
        <name>parentFieldApiName</name>
        <value>Customer__c.Id</value>  <!-- Parent entity + .Id -->
      </componentInstanceProperties>
      <componentInstanceProperties>
        <name>relatedListApiName</name>
        <value>Subscriptions__r</value>  <!-- relationshipLabel + __r -->
      </componentInstanceProperties>
      <componentInstanceProperties>
        <name>relatedListDisplayType</name>
        <value>ADVGRID</value>
      </componentInstanceProperties>
        <componentInstanceProperties>
        <name>relatedListFieldAliases</name>
        <valueList>
          <valueListItems><value>NAME</value></valueListItems>
          <valueListItems><value>Status__c</value></valueListItems>
          <valueListItems><value>Start_Date__c</value></valueListItems>
          <valueListItems><value>Amount__c</value></valueListItems>
        </valueList>
      </componentInstanceProperties>
      <componentInstanceProperties>
        <name>relatedListLabel</name>
        <value>Subscriptions</value>  <!-- User-friendly display name -->
      </componentInstanceProperties>
      <componentInstanceProperties>
        <name>showActionBar</name>
        <value>true</value>
      </componentInstanceProperties>
      <componentInstanceProperties>
        <name>sortFieldAlias</name>
        <value>__DEFAULT__</value>
      </componentInstanceProperties>
      <componentInstanceProperties>
        <name>sortFieldOrder</name>
        <value>Default</value>
      </componentInstanceProperties>
    </componentInstance>
  </itemInstances>
 ```