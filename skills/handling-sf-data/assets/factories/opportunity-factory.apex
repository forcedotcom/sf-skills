/**
 * Test Data Factory for Opportunity records
 * Supports bulk creation with Account relationships and stage variations
 *
 * Usage:
 *   List<Opportunity> opps = TestDataFactory_Opportunity.create(200);
 *   List<Opportunity> oppsForAccount = TestDataFactory_Opportunity.createForAccount(50, accountId);
 *   List<Opportunity> closedWon = TestDataFactory_Opportunity.createWithStage(100, 'Closed Won');
 */
public class TestDataFactory_Opportunity {

    private static final String DEFAULT_NAME_PREFIX = 'Test Opportunity ';
    private static final String DEFAULT_STAGE = 'Prospecting';
    private static final Integer DEFAULT_CLOSE_DAYS = 30;

    /**
     * Create and insert Opportunity records (creates parent Account automatically)
     * @param count Number of records to create
     * @return List of inserted Opportunity records with IDs
     */
    public static List<Opportunity> create(Integer count) {
        return create(count, true);
    }

    /**
     * Create Opportunity records with insert option
     * @param count Number of records to create
     * @param doInsert Whether to insert records
     * @return List of Opportunity records
     */
    public static List<Opportunity> create(Integer count, Boolean doInsert) {
        // Create a parent Account
        Account parentAccount = new Account(Name = 'Test Parent Account for Opportunities');
        insert parentAccount;

        return createForAccount(count, parentAccount.Id, doInsert);
    }

    /**
     * Create Opportunity records for a specific Account
     * @param count Number of records to create
     * @param accountId Parent Account ID
     * @return List of inserted Opportunity records
     */
    public static List<Opportunity> createForAccount(Integer count, Id accountId) {
        return createForAccount(count, accountId, true);
    }

    /**
     * Create Opportunity records for a specific Account with insert option
     * @param count Number of records to create
     * @param accountId Parent Account ID
     * @param doInsert Whether to insert records
     * @return List of Opportunity records
     */
    public static List<Opportunity> createForAccount(Integer count, Id accountId, Boolean doInsert) {
        List<Opportunity> records = new List<Opportunity>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i, accountId));
        }
        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Opportunities with a specific Stage
     * @param count Number of records to create
     * @param stageName StageName picklist value
     * @return List of inserted Opportunity records
     */
    public static List<Opportunity> createWithStage(Integer count, String stageName) {
        Account parentAccount = new Account(Name = 'Test Parent Account for ' + stageName + ' Opps');
        insert parentAccount;

        return createWithStageForAccount(count, stageName, parentAccount.Id);
    }

    /**
     * Create Opportunities with a specific Stage for an Account
     * @param count Number of records to create
     * @param stageName StageName picklist value
     * @param accountId Parent Account ID
     * @return List of inserted Opportunity records
     */
    public static List<Opportunity> createWithStageForAccount(Integer count, String stageName, Id accountId) {
        List<Opportunity> records = new List<Opportunity>();
        for (Integer i = 0; i < count; i++) {
            Opportunity opp = buildRecord(i, accountId);
            opp.StageName = stageName;

            // Set Probability based on stage
            if (stageName == 'Closed Won') {
                opp.Probability = 100;
            } else if (stageName == 'Closed Lost') {
                opp.Probability = 0;
            }

            records.add(opp);
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Opportunities with varied Stages for pipeline testing
     * @param count Number of records to create
     * @param accountId Parent Account ID
     * @return List of inserted Opportunity records with varied stages
     */
    public static List<Opportunity> createWithVariedStages(Integer count, Id accountId) {
        List<String> stages = new List<String>{
            'Prospecting', 'Qualification', 'Needs Analysis',
            'Value Proposition', 'Id. Decision Makers', 'Perception Analysis',
            'Proposal/Price Quote', 'Negotiation/Review', 'Closed Won', 'Closed Lost'
        };

        List<Opportunity> records = new List<Opportunity>();
        for (Integer i = 0; i < count; i++) {
            Opportunity opp = buildRecord(i, accountId);
            opp.StageName = stages[Math.mod(i, stages.size())];
            records.add(opp);
        }

        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Opportunities with varied Amounts for revenue testing
     * @param count Number of records to create
     * @param accountId Parent Account ID
     * @param minAmount Minimum amount
     * @param maxAmount Maximum amount
     * @return List of inserted Opportunity records
     */
    public static List<Opportunity> createWithVariedAmounts(Integer count, Id accountId, Decimal minAmount, Decimal maxAmount) {
        List<Opportunity> records = new List<Opportunity>();
        Decimal range = maxAmount - minAmount;

        for (Integer i = 0; i < count; i++) {
            Opportunity opp = buildRecord(i, accountId);
            // Distribute amounts evenly across the range
            opp.Amount = minAmount + (range * i / count);
            records.add(opp);
        }

        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Build a single Opportunity record with default values
     * @param index Record index for unique naming
     * @param accountId Parent Account ID
     * @return Opportunity record (not inserted)
     */
    private static Opportunity buildRecord(Integer index, Id accountId) {
        String indexStr = String.valueOf(index).leftPad(5, '0');

        return new Opportunity(
            Name = DEFAULT_NAME_PREFIX + indexStr,
            AccountId = accountId,
            StageName = DEFAULT_STAGE,
            CloseDate = Date.today().addDays(DEFAULT_CLOSE_DAYS + index),
            Amount = 10000 + (index * 1000),
            Probability = 20,
            Type = 'New Customer',
            LeadSource = 'Web',
            NextStep = 'Follow up call',
            Description = 'Test opportunity created by TestDataFactory for automated testing'
        );
    }

    /**
     * Get IDs of created records for cleanup
     * @param records List of Opportunity records
     * @return Set of Opportunity IDs
     */
    public static Set<Id> getIds(List<Opportunity> records) {
        Set<Id> ids = new Set<Id>();
        for (Opportunity opp : records) {
            if (opp.Id != null) {
                ids.add(opp.Id);
            }
        }
        return ids;
    }

    /**
     * Delete records by IDs (cleanup utility)
     * @param recordIds Set of Opportunity IDs to delete
     */
    public static void cleanup(Set<Id> recordIds) {
        if (!recordIds.isEmpty()) {
            delete [SELECT Id FROM Opportunity WHERE Id IN :recordIds];
        }
    }
}
