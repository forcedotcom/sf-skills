#!/usr/bin/env bash
# FlexCard CLI Commands
# Replace <org> with your org alias and <Name> with the FlexCard API name.

# Query active FlexCards in the org
sf data query -q "SELECT Id,Name,DataSourceConfig,PropertySetConfig,IsActive FROM OmniUiCard WHERE IsActive=true LIMIT 200" -o <org>

# Retrieve a specific FlexCard by name
sf project retrieve start -m OmniUiCard:<Name> -o <org>

# Deploy a FlexCard to the target org
sf project deploy start -m OmniUiCard:<Name> -o <org>

# Retrieve all FlexCards
sf project retrieve start -m OmniUiCard -o <org>

# Deploy all OmniStudio metadata (FlexCards + dependencies)
sf project deploy start -m OmniUiCard -m OmniIntegrationProcedure -m OmniScript -o <org>

# Check deploy status (use job ID from deploy output)
sf project deploy report --job-id <jobId> -o <org>

# In namespaced orgs (managed package), prefix the metadata type:
# sf project deploy start -m omnistudio__OmniUiCard:<Name> -o <org>
