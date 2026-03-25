/**
 * Test class for external API callouts using mock framework
 *              Demonstrates HttpCalloutMock and WebServiceMock patterns.
 */
@IsTest
private class {{ClassName}}CalloutTest {

    // ═══════════════════════════════════════════════════════════════════════════
    // MOCK IMPLEMENTATIONS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Mock for successful HTTP response (200 OK)
     */
    private class SuccessMock implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest req) {
            HttpResponse res = new HttpResponse();
            res.setStatusCode(200);
            res.setStatus('OK');
            res.setHeader('Content-Type', 'application/json');
            res.setBody(JSON.serialize(new Map<String, Object>{
                'success' => true,
                'data' => new Map<String, Object>{
                    'id' => '12345',
                    'status' => 'completed',
                    'timestamp' => Datetime.now().format()
                }
            }));
            return res;
        }
    }

    /**
     * Mock for error HTTP response (500 Internal Server Error)
     */
    private class ErrorMock implements HttpCalloutMock {
        private Integer statusCode;
        private String errorMessage;

        public ErrorMock(Integer statusCode, String errorMessage) {
            this.statusCode = statusCode;
            this.errorMessage = errorMessage;
        }

        public HttpResponse respond(HttpRequest req) {
            HttpResponse res = new HttpResponse();
            res.setStatusCode(this.statusCode);
            res.setStatus('Error');
            res.setHeader('Content-Type', 'application/json');
            res.setBody(JSON.serialize(new Map<String, Object>{
                'success' => false,
                'error' => this.errorMessage
            }));
            return res;
        }
    }

    /**
     * Mock for timeout simulation
     */
    private class TimeoutMock implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest req) {
            // Simulate timeout by throwing CalloutException
            throw new CalloutException('Read timed out');
        }
    }

    /**
     * Mock that validates request parameters
     */
    private class ValidatingMock implements HttpCalloutMock {
        private String expectedEndpoint;
        private String expectedMethod;

        public ValidatingMock(String endpoint, String method) {
            this.expectedEndpoint = endpoint;
            this.expectedMethod = method;
        }

        public HttpResponse respond(HttpRequest req) {
            Assert.areEqual(expectedMethod, req.getMethod(),
                'HTTP method should be ' + expectedMethod);
            Assert.isTrue(req.getEndpoint().contains(expectedEndpoint),
                'Endpoint should contain ' + expectedEndpoint);

            HttpResponse res = new HttpResponse();
            res.setStatusCode(200);
            res.setBody('{"validated": true}');
            return res;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // SUCCESS TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Tests successful API call returns expected data
     */
    @IsTest
    static void testCallout_Success_ReturnsData() {
        // GIVEN
        Test.setMock(HttpCalloutMock.class, new SuccessMock());

        // WHEN
        Test.startTest();
        // TODO: Replace with your actual service call
        // {{ClassName}}Response response = {{ClassName}}.callExternalAPI('test-param');
        HttpRequest req = new HttpRequest();
        req.setEndpoint('https://api.example.com/test');
        req.setMethod('GET');
        HttpResponse res = new Http().send(req);
        Test.stopTest();

        // THEN
        Assert.areEqual(200, res.getStatusCode(), 'Should return 200 OK');

        Map<String, Object> responseBody = (Map<String, Object>) JSON.deserializeUntyped(res.getBody());
        Assert.areEqual(true, responseBody.get('success'), 'Response should indicate success');
        Assert.isNotNull(responseBody.get('data'), 'Response should contain data');
    }

    /**
     * Tests POST request with body
     */
    @IsTest
    static void testCallout_PostWithBody_Success() {
        // GIVEN
        Test.setMock(HttpCalloutMock.class, new SuccessMock());

        Map<String, Object> requestBody = new Map<String, Object>{
            'name' => 'Test Record',
            'value' => 100
        };

        // WHEN
        Test.startTest();
        HttpRequest req = new HttpRequest();
        req.setEndpoint('https://api.example.com/create');
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        req.setBody(JSON.serialize(requestBody));
        HttpResponse res = new Http().send(req);
        Test.stopTest();

        // THEN
        Assert.areEqual(200, res.getStatusCode(), 'POST should succeed');
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // ERROR HANDLING TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Tests handling of 400 Bad Request
     */
    @IsTest
    static void testCallout_BadRequest_HandlesGracefully() {
        // GIVEN
        Test.setMock(HttpCalloutMock.class, new ErrorMock(400, 'Invalid request parameters'));

        // WHEN
        Test.startTest();
        HttpRequest req = new HttpRequest();
        req.setEndpoint('https://api.example.com/test');
        req.setMethod('GET');
        HttpResponse res = new Http().send(req);
        Test.stopTest();

        // THEN
        Assert.areEqual(400, res.getStatusCode(), 'Should return 400');

        Map<String, Object> errorBody = (Map<String, Object>) JSON.deserializeUntyped(res.getBody());
        Assert.areEqual(false, errorBody.get('success'), 'Should indicate failure');
        Assert.isNotNull(errorBody.get('error'), 'Should contain error message');
    }

    /**
     * Tests handling of 500 Internal Server Error
     */
    @IsTest
    static void testCallout_ServerError_HandlesGracefully() {
        // GIVEN
        Test.setMock(HttpCalloutMock.class, new ErrorMock(500, 'Internal server error'));

        // WHEN
        Test.startTest();
        HttpRequest req = new HttpRequest();
        req.setEndpoint('https://api.example.com/test');
        req.setMethod('GET');
        HttpResponse res = new Http().send(req);
        Test.stopTest();

        // THEN
        Assert.areEqual(500, res.getStatusCode(), 'Should return 500');
    }

    /**
     * Tests handling of timeout exception
     */
    @IsTest
    static void testCallout_Timeout_ThrowsException() {
        // GIVEN
        Test.setMock(HttpCalloutMock.class, new TimeoutMock());

        // WHEN/THEN
        Test.startTest();
        try {
            HttpRequest req = new HttpRequest();
            req.setEndpoint('https://api.example.com/slow');
            req.setMethod('GET');
            new Http().send(req);
            Assert.fail('Expected CalloutException was not thrown');
        } catch (CalloutException e) {
            Assert.isTrue(e.getMessage().containsIgnoreCase('timeout'),
                'Exception should mention timeout: ' + e.getMessage());
        }
        Test.stopTest();
    }

    /**
     * Tests handling of 401 Unauthorized
     */
    @IsTest
    static void testCallout_Unauthorized_HandlesGracefully() {
        // GIVEN
        Test.setMock(HttpCalloutMock.class, new ErrorMock(401, 'Invalid or expired token'));

        // WHEN
        Test.startTest();
        HttpRequest req = new HttpRequest();
        req.setEndpoint('https://api.example.com/protected');
        req.setMethod('GET');
        HttpResponse res = new Http().send(req);
        Test.stopTest();

        // THEN
        Assert.areEqual(401, res.getStatusCode(), 'Should return 401 Unauthorized');
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // REQUEST VALIDATION TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Verifies correct endpoint and method are used
     */
    @IsTest
    static void testCallout_ValidatesRequestParameters() {
        // GIVEN
        Test.setMock(HttpCalloutMock.class, new ValidatingMock('/api/v1/resource', 'POST'));

        // WHEN
        Test.startTest();
        HttpRequest req = new HttpRequest();
        req.setEndpoint('https://api.example.com/api/v1/resource');
        req.setMethod('POST');
        req.setBody('{"test": true}');
        HttpResponse res = new Http().send(req);
        Test.stopTest();

        // THEN - Mock validates; test passes if no assertion failure
        Assert.areEqual(200, res.getStatusCode(), 'Request should be valid');
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // ASYNC CALLOUT TESTS (@future, Queueable)
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Tests @future method with callout
     *              Note: Must use Test.startTest/stopTest to execute @future
     */
    @IsTest
    static void testFutureCallout_ExecutesSuccessfully() {
        // GIVEN
        Test.setMock(HttpCalloutMock.class, new SuccessMock());

        // WHEN - Call @future method
        Test.startTest();
        // TODO: Replace with your actual @future method
        // {{ClassName}}.makeAsyncCallout('test-param');
        Test.stopTest();  // Forces @future to execute

        // THEN - Verify results (may need to query for side effects)
        // TODO: Add assertions based on what @future method does
    }

    /**
     * Tests Queueable with callout
     */
    @IsTest
    static void testQueueableCallout_ExecutesSuccessfully() {
        // GIVEN
        Test.setMock(HttpCalloutMock.class, new SuccessMock());

        // WHEN
        Test.startTest();
        // TODO: Replace with your actual Queueable
        // System.enqueueJob(new {{ClassName}}Queueable('param'));
        Test.stopTest();  // Forces Queueable to execute

        // THEN - Verify results
        // TODO: Add assertions
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // MULTI-CALLOUT TESTS
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Mock for multiple sequential callouts
     */
    private class MultiCalloutMock implements HttpCalloutMock {
        private Integer callCount = 0;

        public HttpResponse respond(HttpRequest req) {
            callCount++;
            HttpResponse res = new HttpResponse();
            res.setStatusCode(200);
            res.setBody('{"callNumber": ' + callCount + '}');
            return res;
        }
    }

    /**
     * Tests multiple callouts in sequence (limit: 100 per transaction)
     */
    @IsTest
    static void testMultipleCallouts_AllSucceed() {
        // GIVEN
        Test.setMock(HttpCalloutMock.class, new MultiCalloutMock());

        // WHEN - Make multiple callouts
        Test.startTest();
        List<HttpResponse> responses = new List<HttpResponse>();
        for (Integer i = 0; i < 5; i++) {
            HttpRequest req = new HttpRequest();
            req.setEndpoint('https://api.example.com/call/' + i);
            req.setMethod('GET');
            responses.add(new Http().send(req));
        }
        Test.stopTest();

        // THEN
        Assert.areEqual(5, responses.size(), 'Should complete 5 callouts');
        for (HttpResponse res : responses) {
            Assert.areEqual(200, res.getStatusCode(), 'Each callout should succeed');
        }
    }
}
