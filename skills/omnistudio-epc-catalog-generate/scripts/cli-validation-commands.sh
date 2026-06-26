#!/usr/bin/env bash
# CLI commands for querying and validating EPC artifacts in a Salesforce org.
# Usage: replace <org> with your authenticated org alias.

# Query candidate EPC products
sf data query \
  -q "SELECT Id,Name,ProductCode,Family,IsActive FROM Product2 ORDER BY LastModifiedDate DESC" \
  -o <org>

# Query Product Child Items for an offer
sf data query \
  -q "SELECT Id,Name,%vlocity_namespace%__ParentProductName__c,%vlocity_namespace%__ChildProductName__c,%vlocity_namespace%__MinMaxDefaultQty__c FROM %vlocity_namespace%__ProductChildItem__c WHERE %vlocity_namespace%__ParentProductName__c='<Offer Name>'" \
  -o <org>

# Retrieve Product2 metadata package members
sf project retrieve start -m Product2:<DeveloperNameOrName> -o <org>

# Validate deployment in dry-run mode
sf project deploy start -x manifest/package.xml --dry-run -o <org>
