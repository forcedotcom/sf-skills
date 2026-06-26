#!/usr/bin/env bash
# Sample skill invocation commands for common EPC modeling tasks.
# Replace `cursor-agent` with your local agent command wrapper if different.

# Create a new EPC offer bundle with full companion metadata
cursor-agent "Create a Product2 offer bundle named Business Internet Plus with ProductCode BIZ-INT-PLUS-01, 3 child products, and generate all companion DataPack JSON files from the assets templates."

# Add configurable attributes to an existing EPC Product2 record
cursor-agent "Update Product2 Business Internet Essential with attribute metadata/defaults/assignments for Bandwidth, ContractTerm, and StaticIPCount, including valid values and defaults."

# Build ProductChildItem relationships for an offer
cursor-agent "Create root and child %vlocity_namespace%__ProductChildItem__c records for offer Business Internet Essential VPL with min/max/default quantity rules."

# Review an existing DataPack for EPC modeling quality
cursor-agent "Review the Product2 bundle JSON files under examples/business-internet-plus-bundle/, score against the 120-point rubric, and return risks plus required fixes."

# Convert a spec product into a bundle-ready offer payload
cursor-agent "Transform Product2 Dedicated Fiber 1G from spec product to offer bundle (SpecificationType=Offer, SpecificationSubType=Bundle) and generate aligned PCI + pricing artifacts."
