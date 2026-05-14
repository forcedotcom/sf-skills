# Credits & Acknowledgments

This skill is built on established Salesforce DevOps practices, official platform tooling, and the collective knowledge embedded in Salesforce's documentation and developer ecosystem.

---

## Key Concepts

### Two-Phase Deployment Pattern
The `--dry-run` validation before actual deployment is a community-established best practice to prevent production failures, widely promoted across official Salesforce documentation.

### Quick Deploy Strategy
The workflow of validating with tests, then using quick deploy for actual deployment, originates from Salesforce release management best practices.

### Test Level Recommendations
The guidance on appropriate test levels (RunLocalTests vs RunAllTests vs RunSpecifiedTests) comes from official Salesforce deployment documentation.

### Incremental Deployment Strategy
The recommendation for small, frequent deployments over large batches is a DevOps industry best practice adapted for Salesforce.

---

## Special Thanks

To the entire Salesforce DevOps community — release managers, architects, developers, and CI/CD engineers — for continuously improving deployment practices and making Salesforce deployments more reliable.
