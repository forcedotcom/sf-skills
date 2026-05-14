/**
 * @description Industries callable that finds Quotes on an Account that have at least one
 *              QuoteLineItem with a specified Product2.ProductCode.
 *              Integrates with OmniStudio/Industries extension points.
 * @author      building-omnistudio-callable-apex
 *
 * Actions:
 *   - findQuotesByProductCode: Returns Quotes for an Account with QuoteLineItems matching productCode
 *
 * Input (findQuotesByProductCode):
 *   - accountId (String, required): Id of the Account
 *   - productCode (String, required): Product2.ProductCode to match on QuoteLineItems
 *
 * Output envelope:
 *   - success (Boolean)
 *   - data (Map): quotes (List<Map> with Id, Name, QuoteNumber)
 *   - errors (List<Map>)
 */
public with sharing class Industries_QuoteByProductCallable implements System.Callable {

    private static final String ACTION_FIND_QUOTES = 'findQuotesByProductCode';

    /**
     * @description Dispatches to the appropriate action handler.
     * @param action Action name (e.g. 'findQuotesByProductCode')
     * @param args   Input map with accountId and productCode
     * @return      Response envelope: success, data, errors
     */
    public Object call(String action, Map<String, Object> args) {
        switch on action {
            when ACTION_FIND_QUOTES {
                return findQuotesByProductCode(args);
            }
            when else {
                throw new IndustriesCallableException('Unsupported action: ' + action);
            }
        }
    }

    /**
     * @description Finds all Quotes on an Account that have at least one QuoteLineItem
     *              with the specified Product2.ProductCode.
     * @param args  Map with keys: accountId (String), productCode (String)
     * @return     Response envelope with quotes list or errors
     */
    private Map<String, Object> findQuotesByProductCode(Map<String, Object> args) {
        List<Map<String, Object>> errors = new List<Map<String, Object>>();

        Object accountIdObj = args != null ? args.get('accountId') : null;
        Object productCodeObj = args != null ? args.get('productCode') : null;

        String accountId = accountIdObj != null ? String.valueOf(accountIdObj).trim() : null;
        String productCode = productCodeObj != null ? String.valueOf(productCodeObj).trim() : null;

        if (String.isBlank(accountId)) {
            errors.add(new Map<String, Object>{
                'code' => 'MISSING_ACCOUNT_ID',
                'message' => 'accountId is required'
            });
        }
        if (String.isBlank(productCode)) {
            errors.add(new Map<String, Object>{
                'code' => 'MISSING_PRODUCT_CODE',
                'message' => 'productCode is required'
            });
        }
        if (!errors.isEmpty()) {
            return new Map<String, Object>{
                'success' => false,
                'data' => new Map<String, Object>{ 'quotes' => new List<Map<String, Object>>() },
                'errors' => errors
            };
        }

        try {
            List<Quote> quotes = [
                SELECT Id, Name, QuoteNumber, OpportunityId
                FROM Quote
                WITH USER_MODE
                WHERE Opportunity.AccountId = :accountId
                AND Id IN (
                    SELECT QuoteId
                    FROM QuoteLineItem
                    WHERE Product2.ProductCode = :productCode
                )
            ];

            List<Map<String, Object>> quoteMaps = new List<Map<String, Object>>();
            for (Quote q : quotes) {
                quoteMaps.add(new Map<String, Object>{
                    'Id' => q.Id,
                    'Name' => q.Name,
                    'QuoteNumber' => q.QuoteNumber
                });
            }

            return new Map<String, Object>{
                'success' => true,
                'data' => new Map<String, Object>{ 'quotes' => quoteMaps },
                'errors' => new List<Map<String, Object>>()
            };
        } catch (Exception e) {
            return new Map<String, Object>{
                'success' => false,
                'data' => new Map<String, Object>{ 'quotes' => new List<Map<String, Object>>() },
                'errors' => new List<Map<String, Object>>{
                    new Map<String, Object>{
                        'code' => 'QUERY_ERROR',
                        'message' => e.getMessage()
                    }
                }
            };
        }
    }
}
