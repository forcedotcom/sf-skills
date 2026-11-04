#!/usr/bin/env bash
# FlexCard CLI Commands
# Replace <org> with your org alias and <Name> with the FlexCard API name.

# Query active FlexCards in the org
sf data query -q "SELECT Id,Name,DataSourceConfig,PropertySetConfig,IsActive FROM OmniUiCard WHERE IsActive=true LIMIT 200" -o <org>

# Retrieve a specific FlexCard by name
sf project retrieve start -m OmniUiCard:<Name>_<Author>_<Version> -o <org>

# Deploy a FlexCard to the target org
sf project deploy start -m OmniUiCard:<Name>_<Author>_<Version> -o <org>

# Retrieve all FlexCards
sf project retrieve start -m OmniUiCard -o <org>

# Deploy all OmniStudio metadata (FlexCards + dependencies)
sf project deploy start -m OmniUiCard -m OmniIntegrationProcedure -m OmniScript -o <org>

# Check deploy status (use job ID from deploy output)
sf project deploy report --job-id <jobId> -o <org>

# The OmniUiCard fullName is <Name>_<AuthorName>_<VersionNumber> (e.g. AccountSummary_MyAuthor_1).
# The metadata type is never namespace-prefixed; managed-package (non-Core) orgs use Vlocity Build DataPacks instead.
