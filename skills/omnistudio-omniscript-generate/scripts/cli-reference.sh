#!/bin/bash
# OmniScript CLI command reference. Not meant to be run directly.
# Copy individual commands as needed. Replace <org>, <id>, <Type>, <SubType>, <Name> with actual values.
# <Name> for OmniScript metadata is <Type>_<SubType>_<Language>_<Version> (e.g. ServiceRequest_NewCase_English_1).

# List active OmniScripts
sf data query -q "SELECT Id,Name,Type,SubType,Language,IsActive,VersionNumber FROM OmniProcess WHERE IsActive=true AND IsIntegrationProcedure=false LIMIT 50" -o <org>

# Query all elements for a specific OmniScript (ordered by hierarchy)
sf data query -q "SELECT Id,Name,Type,PropertySetConfig,Level,SequenceNumber,ParentElementId FROM OmniProcessElement WHERE OmniProcessId='<id>' ORDER BY Level,SequenceNumber LIMIT 200" -o <org>

# Retrieve OmniScript metadata from org
sf project retrieve start -m "OmniScript:<Name>" -o <org>

# Deploy OmniScript metadata to org
sf project deploy start -m "OmniScript:<Name>" -o <org>

# Check all versions of a specific OmniScript
sf data query -q "SELECT Id,VersionNumber,IsActive,LastModifiedDate FROM OmniProcess WHERE Type='<Type>' AND SubType='<SubType>' AND IsIntegrationProcedure=false ORDER BY VersionNumber DESC LIMIT 10" -o <org>

# Verify active version after deployment
sf data query -q "SELECT Id,Name,Type,SubType,Language,IsActive,VersionNumber FROM OmniProcess WHERE Type='<Type>' AND SubType='<SubType>' AND IsIntegrationProcedure=false AND IsActive=true LIMIT 5" -o <org>
