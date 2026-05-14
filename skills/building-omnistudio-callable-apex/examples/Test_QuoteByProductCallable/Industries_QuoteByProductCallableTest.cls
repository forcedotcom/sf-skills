/**
 * @description Test class for Industries_QuoteByProductCallable.
 *              Covers positive, negative, contract, and unsupported action scenarios.
 * @author      building-omnistudio-callable-apex
 */
@IsTest
private class Industries_QuoteByProductCallableTest {

    // ═══════════════════════════════════════════════════════════════════════════
    // TEST DATA SETUP
    // ═══════════════════════════════════════════════════════════════════════════

    @TestSetup
    static void setupTestData() {
        Account acc = new Account(Name = 'Test Account');
        insert acc;

        Pricebook2 pb = [SELECT Id FROM Pricebook2 WHERE IsStandard = true LIMIT 1];

        Opportunity opp = new Opportunity(
            Name = 'Test Opp',
            AccountId = acc.Id,
            Pricebook2Id = pb.Id,
            StageName = 'Prospecting',
            CloseDate = Date.today().addMonths(1)
        );
        insert opp;

        Product2 prod = new Product2(
            Name = 'Test Product',
            ProductCode = 'PROD-001',
            IsActive = true
        );
        insert prod;

        PricebookEntry pbe = new PricebookEntry(
            Pricebook2Id = pb.Id,
            Product2Id = prod.Id,
            UnitPrice = 100,
            IsActive = true
        );
        insert pbe;

        Quote q = new Quote(
            Name = 'Test Quote',
            OpportunityId = opp.Id,
            Pricebook2Id = pb.Id
        );
        insert q;

        QuoteLineItem qli = new QuoteLineItem(
            QuoteId = q.Id,
            PricebookEntryId = pbe.Id,
            Quantity = 1,
            UnitPrice = 100
        );
        insert qli;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // POSITIVE TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * @description Tests findQuotesByProductCode returns Quotes with matching productCode
     */
    @IsTest
    static void testFindQuotesByProductCode_Success() {
        Account acc = [SELECT Id FROM Account LIMIT 1];
        System.Callable svc = new Industries_QuoteByProductCallable();
        Map<String, Object> args = new Map<String, Object>{
            'accountId' => acc.Id,
            'productCode' => 'PROD-001'
        };

        Test.startTest();
        Map<String, Object> result = (Map<String, Object>) svc.call('findQuotesByProductCode', args);
        Test.stopTest();

        Assert.isTrue((Boolean) result.get('success'), 'Should succeed');
        Map<String, Object> data = (Map<String, Object>) result.get('data');
        List<Object> quotes = (List<Object>) data.get('quotes');
        Assert.isNotNull(quotes, 'quotes list should not be null');
        Assert.areEqual(1, quotes.size(), 'Should return 1 Quote');
    }

    /**
     * @description Tests findQuotesByProductCode returns empty list when no match
     */
    @IsTest
    static void testFindQuotesByProductCode_NoMatch_ReturnsEmpty() {
        Account acc = [SELECT Id FROM Account LIMIT 1];
        System.Callable svc = new Industries_QuoteByProductCallable();
        Map<String, Object> args = new Map<String, Object>{
            'accountId' => acc.Id,
            'productCode' => 'NONEXISTENT'
        };

        Test.startTest();
        Map<String, Object> result = (Map<String, Object>) svc.call('findQuotesByProductCode', args);
        Test.stopTest();

        Assert.isTrue((Boolean) result.get('success'), 'Should succeed with empty result');
        Map<String, Object> data = (Map<String, Object>) result.get('data');
        List<Object> quotes = (List<Object>) data.get('quotes');
        Assert.areEqual(0, quotes.size(), 'Should return 0 Quotes');
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CONTRACT / INPUT VALIDATION TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * @description Tests missing accountId returns error envelope
     */
    @IsTest
    static void testFindQuotesByProductCode_MissingAccountId_ReturnsError() {
        Map<String, Object> args = new Map<String, Object>{
            'productCode' => 'PROD-001'
        };
        System.Callable svc = new Industries_QuoteByProductCallable();

        Test.startTest();
        Map<String, Object> result = (Map<String, Object>) svc.call('findQuotesByProductCode', args);
        Test.stopTest();

        Assert.isFalse((Boolean) result.get('success'), 'Should fail');
        List<Object> errors = (List<Object>) result.get('errors');
        Assert.isTrue(errors.size() >= 1, 'Should have at least one error');
    }

    /**
     * @description Tests missing productCode returns error envelope
     */
    @IsTest
    static void testFindQuotesByProductCode_MissingProductCode_ReturnsError() {
        Account acc = [SELECT Id FROM Account LIMIT 1];
        Map<String, Object> args = new Map<String, Object>{
            'accountId' => acc.Id
        };
        System.Callable svc = new Industries_QuoteByProductCallable();

        Test.startTest();
        Map<String, Object> result = (Map<String, Object>) svc.call('findQuotesByProductCode', args);
        Test.stopTest();

        Assert.isFalse((Boolean) result.get('success'), 'Should fail');
        List<Object> errors = (List<Object>) result.get('errors');
        Assert.isTrue(errors.size() >= 1, 'Should have at least one error');
    }

    /**
     * @description Tests null args returns error envelope
     */
    @IsTest
    static void testFindQuotesByProductCode_NullArgs_ReturnsError() {
        System.Callable svc = new Industries_QuoteByProductCallable();

        Test.startTest();
        Map<String, Object> result = (Map<String, Object>) svc.call('findQuotesByProductCode', null);
        Test.stopTest();

        Assert.isFalse((Boolean) result.get('success'), 'Should fail');
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // NEGATIVE TESTS (Unsupported Action)
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * @description Tests unsupported action throws IndustriesCallableException
     */
    @IsTest
    static void testUnsupportedAction_ThrowsException() {
        System.Callable svc = new Industries_QuoteByProductCallable();

        Test.startTest();
        try {
            svc.call('unknownAction', new Map<String, Object>());
            Assert.fail('Expected IndustriesCallableException');
        } catch (IndustriesCallableException e) {
            Assert.isTrue(
                e.getMessage().contains('Unsupported action'),
                'Error message should mention unsupported action: ' + e.getMessage()
            );
        }
        Test.stopTest();
    }
}
