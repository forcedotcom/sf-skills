/**
 * Test Data Factory for Lead records
 * Supports bulk creation with status and source variations
 *
 * Usage:
 *   List<Lead> leads = TestDataFactory_Lead.create(200);
 *   List<Lead> openLeads = TestDataFactory_Lead.createWithStatus(100, 'Open - Not Contacted');
 *   List<Lead> qualifiedLeads = TestDataFactory_Lead.createQualified(50);
 */
public class TestDataFactory_Lead {

    private static final String DEFAULT_FIRST_NAME_PREFIX = 'Test';
    private static final String DEFAULT_LAST_NAME_PREFIX = 'Lead';
    private static final String DEFAULT_COMPANY_PREFIX = 'Test Company ';
    private static final String DEFAULT_STATUS = 'Open - Not Contacted';
    private static final String DEFAULT_EMAIL_DOMAIN = 'testlead.example.com';

    /**
     * Create and insert Lead records with default values
     * @param count Number of records to create
     * @return List of inserted Lead records with IDs
     */
    public static List<Lead> create(Integer count) {
        return create(count, true);
    }

    /**
     * Create Lead records with insert option
     * @param count Number of records to create
     * @param doInsert Whether to insert records
     * @return List of Lead records
     */
    public static List<Lead> create(Integer count, Boolean doInsert) {
        List<Lead> records = new List<Lead>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i));
        }
        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Lead records with a specific Status
     * @param count Number of records to create
     * @param status Lead Status picklist value
     * @return List of inserted Lead records
     */
    public static List<Lead> createWithStatus(Integer count, String status) {
        List<Lead> records = new List<Lead>();
        for (Integer i = 0; i < count; i++) {
            Lead lead = buildRecord(i);
            lead.Status = status;
            records.add(lead);
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create qualified Lead records (ready for conversion)
     * @param count Number of records to create
     * @return List of inserted qualified Lead records
     */
    public static List<Lead> createQualified(Integer count) {
        List<Lead> records = new List<Lead>();
        for (Integer i = 0; i < count; i++) {
            Lead lead = buildRecord(i);
            lead.Status = 'Qualified';
            lead.Rating = 'Hot';
            lead.NumberOfEmployees = 100;
            lead.AnnualRevenue = 1000000;
            records.add(lead);
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Leads with varied Lead Sources for attribution testing
     * @param count Number of records to create
     * @return List of inserted Lead records with varied sources
     */
    public static List<Lead> createWithVariedSources(Integer count) {
        List<String> sources = new List<String>{
            'Web', 'Phone Inquiry', 'Partner Referral', 'Purchased List',
            'Other', 'Trade Show', 'Employee Referral', 'External Referral'
        };

        List<Lead> records = new List<Lead>();
        for (Integer i = 0; i < count; i++) {
            Lead lead = buildRecord(i);
            lead.LeadSource = sources[Math.mod(i, sources.size())];
            records.add(lead);
        }

        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Leads with varied Industries for segmentation testing
     * @param count Number of records to create
     * @return List of inserted Lead records with varied industries
     */
    public static List<Lead> createWithVariedIndustries(Integer count) {
        List<String> industries = new List<String>{
            'Technology', 'Healthcare', 'Finance', 'Manufacturing',
            'Retail', 'Education', 'Energy', 'Media', 'Government'
        };

        List<Lead> records = new List<Lead>();
        for (Integer i = 0; i < count; i++) {
            Lead lead = buildRecord(i);
            lead.Industry = industries[Math.mod(i, industries.size())];
            records.add(lead);
        }

        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Build a single Lead record with default values
     * @param index Record index for unique naming
     * @return Lead record (not inserted)
     */
    private static Lead buildRecord(Integer index) {
        String indexStr = String.valueOf(index).leftPad(5, '0');
        String firstName = DEFAULT_FIRST_NAME_PREFIX + indexStr;
        String lastName = DEFAULT_LAST_NAME_PREFIX + indexStr;

        return new Lead(
            FirstName = firstName,
            LastName = lastName,
            Company = DEFAULT_COMPANY_PREFIX + indexStr,
            Status = DEFAULT_STATUS,
            Email = firstName.toLowerCase() + '.' + lastName.toLowerCase() + '@' + DEFAULT_EMAIL_DOMAIN,
            Phone = '(555) 400-' + String.valueOf(1000 + index),
            MobilePhone = '(555) 500-' + String.valueOf(1000 + index),
            Title = 'Decision Maker',
            Industry = 'Technology',
            LeadSource = 'Web',
            Rating = 'Warm',
            NumberOfEmployees = 50 + index,
            AnnualRevenue = 500000 + (index * 10000),
            Street = '789 Lead Blvd',
            City = 'San Francisco',
            State = 'CA',
            PostalCode = '94104',
            Country = 'USA',
            Website = 'https://testlead' + index + '.example.com',
            Description = 'Test lead created by TestDataFactory for automated testing'
        );
    }

    /**
     * Get IDs of created records for cleanup
     * @param records List of Lead records
     * @return Set of Lead IDs
     */
    public static Set<Id> getIds(List<Lead> records) {
        Set<Id> ids = new Set<Id>();
        for (Lead lead : records) {
            if (lead.Id != null) {
                ids.add(lead.Id);
            }
        }
        return ids;
    }

    /**
     * Delete records by IDs (cleanup utility)
     * @param recordIds Set of Lead IDs to delete
     */
    public static void cleanup(Set<Id> recordIds) {
        if (!recordIds.isEmpty()) {
            delete [SELECT Id FROM Lead WHERE Id IN :recordIds];
        }
    }
}
