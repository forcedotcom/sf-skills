#!/bin/bash
# Integration Procedure CLI Commands
# Replace <Name> with the IP's Type_SubType name and <org> with your authenticated org alias.

# Query active Integration Procedures (add filters as needed)
sf data query -q "SELECT Id,Name,Type,SubType,IsActive FROM OmniProcess WHERE IsActive=true AND IsIntegrationProcedure=true LIMIT 200" -o <org>

# Query all Integration Procedures including inactive, sorted by most recently modified
sf data query -q "SELECT Id,Name,Type,SubType,IsActive,LastModifiedDate FROM OmniProcess WHERE IsIntegrationProcedure=true ORDER BY LastModifiedDate DESC LIMIT 200" -o <org>

# Retrieve an Integration Procedure from an org
sf project retrieve start -m OmniIntegrationProcedure:<Name> -o <org>

# Deploy an Integration Procedure to an org
sf project deploy start -m OmniIntegrationProcedure:<Name> -o <org>

# Deploy with dry-run validation first (recommended before production deploys)
sf project deploy start -m OmniIntegrationProcedure:<Name> -o <org> --dry-run
