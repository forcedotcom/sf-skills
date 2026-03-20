# Configure Metadata: DigitalExperienceConfig

## Purpose
This configuration file creates a **net-new, default** DigitalExperienceConfig metadata record for a Digital Experience React Site. It is not intended to edit or modify an existing DigitalExperienceConfig record. Use this template only when provisioning a brand-new React site.

## File Location
```
digitalExperienceConfigs/{siteName}1.digitalExperienceConfig-meta.xml
```

## Default Template
```xml
<?xml version="1.0" encoding="UTF-8"?>
<DigitalExperienceConfig xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>{siteName}</label>
    <site>
        <urlPathPrefix>{siteUrlPathPrefix}</urlPathPrefix>
    </site>
    <space>site/{siteName}1</space>
</DigitalExperienceConfig>
```
