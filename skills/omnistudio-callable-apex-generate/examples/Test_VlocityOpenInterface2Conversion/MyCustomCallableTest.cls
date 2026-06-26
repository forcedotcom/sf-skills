/**
 * @description Test class for MyCustomCallable (converted from MyCustomRemoteClass VlocityOpenInterface2).
 *              Covers positive, negative, contract, and unsupported action scenarios.
 * @author      building-omnistudio-callable-apex
 */
@IsTest
private class MyCustomCallableTest {

    // ═══════════════════════════════════════════════════════════════════════════
    // POSITIVE TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * @description Tests calculateTotal returns total with inputMap/options format
     */
    @IsTest
    static void testCalculateTotal_Success() {
        System.Callable svc = new MyCustomCallable();
        Map<String, Object> args = new Map<String, Object>{
            'inputMap' => new Map<String, Object>{
                'price'    => 10.50,
                'quantity' => 3
            },
            'options'  => new Map<String, Object>()
        };

        Test.startTest();
        Map<String, Object> result = (Map<String, Object>) svc.call('calculateTotal', args);
        Test.stopTest();

        Assert.isTrue((Boolean) result.get('success'), 'Should succeed');
        Map<String, Object> data = (Map<String, Object>) result.get('data');
        Assert.areEqual(31.50, (Decimal) data.get('total'), 'total should be 10.50 * 3');
    }

    /**
     * @description Tests calculateTotal with flat args (backward compatibility)
     */
    @IsTest
    static void testCalculateTotal_FlatArgs_Success() {
        System.Callable svc = new MyCustomCallable();
        Map<String, Object> args = new Map<String, Object>{
            'price'    => 100,
            'quantity' => 5
        };

        Test.startTest();
        Map<String, Object> result = (Map<String, Object>) svc.call('calculateTotal', args);
        Test.stopTest();

        Assert.isTrue((Boolean) result.get('success'), 'Should succeed');
        Map<String, Object> data = (Map<String, Object>) result.get('data');
        Assert.areEqual(500, (Decimal) data.get('total'), 'total should be 100 * 5');
    }

    /**
     * @description Tests calculateTotal with string inputs (type coercion from OmniScript)
     */
    @IsTest
    static void testCalculateTotal_StringInputs_Success() {
        System.Callable svc = new MyCustomCallable();
        Map<String, Object> args = new Map<String, Object>{
            'inputMap' => new Map<String, Object>{
                'price'    => '25.00',
                'quantity' => '4'
            },
            'options'  => new Map<String, Object>()
        };

        Map<String, Object> result = (Map<String, Object>) svc.call('calculateTotal', args);

        Assert.isTrue((Boolean) result.get('success'), 'Should succeed');
        Map<String, Object> data = (Map<String, Object>) result.get('data');
        Assert.areEqual(100, (Decimal) data.get('total'), 'total should be 25 * 4');
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // NEGATIVE / CONTRACT TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * @description Tests unsupported action throws IndustriesCallableException
     */
    @IsTest
    static void testUnsupportedAction_Throws() {
        try {
            System.Callable svc = new MyCustomCallable();
            svc.call('unknownAction', new Map<String, Object>{
                'inputMap' => new Map<String, Object>(),
                'options'  => new Map<String, Object>()
            });
            Assert.fail('Expected IndustriesCallableException');
        } catch (IndustriesCallableException e) {
            Assert.isTrue(e.getMessage().contains('Unsupported action'), 'Message should mention unsupported action');
        }
    }

    /**
     * @description Tests missing price returns error envelope
     */
    @IsTest
    static void testCalculateTotal_MissingPrice_ReturnsError() {
        System.Callable svc = new MyCustomCallable();
        Map<String, Object> args = new Map<String, Object>{
            'inputMap' => new Map<String, Object>{ 'quantity' => 2 },
            'options'  => new Map<String, Object>()
        };

        Map<String, Object> result = (Map<String, Object>) svc.call('calculateTotal', args);

        Assert.isFalse((Boolean) result.get('success'), 'Should fail');
        List<Object> errors = (List<Object>) result.get('errors');
        Assert.isNotNull(errors, 'errors should not be null');
        Assert.areEqual(1, errors.size(), 'Should have one error');
    }

    /**
     * @description Tests missing quantity returns error envelope
     */
    @IsTest
    static void testCalculateTotal_MissingQuantity_ReturnsError() {
        System.Callable svc = new MyCustomCallable();
        Map<String, Object> args = new Map<String, Object>{
            'inputMap' => new Map<String, Object>{ 'price' => 50 },
            'options'  => new Map<String, Object>()
        };

        Map<String, Object> result = (Map<String, Object>) svc.call('calculateTotal', args);

        Assert.isFalse((Boolean) result.get('success'), 'Should fail');
        List<Object> errors = (List<Object>) result.get('errors');
        Assert.isNotNull(errors, 'errors should not be null');
    }

    /**
     * @description Tests null args handled gracefully
     */
    @IsTest
    static void testCalculateTotal_NullArgs_ReturnsError() {
        System.Callable svc = new MyCustomCallable();

        Map<String, Object> result = (Map<String, Object>) svc.call('calculateTotal', null);

        Assert.isFalse((Boolean) result.get('success'), 'Should fail with null inputMap');
    }
}
