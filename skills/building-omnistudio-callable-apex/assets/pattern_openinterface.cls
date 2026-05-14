/**
 * VlocityOpenInterface2 implementation skeleton.
 * Use when the Industries extension point requires the legacy Open Interface contract.
 *
 * Key rules:
 * - Write results into outputMap via putAll(); do NOT return the envelope from invokeMethod
 * - Return true for success, false for unsupported/failed actions
 * - Delegate to the same private methods as the Callable (same inputMap, options signature)
 * - Populate outputMap with the same envelope shape (success, data, errors)
 *
 * Replace Industries_XxxOpenInterface and actionOne with the actual class/action names.
 */
global with sharing class Industries_XxxOpenInterface implements omnistudio.VlocityOpenInterface2 {

    global Boolean invokeMethod(String methodName, Map<String, Object> inputMap,
                                Map<String, Object> outputMap, Map<String, Object> options) {
        switch on methodName {
            when 'actionOne' {
                Map<String, Object> result = actionOne(inputMap, options);
                outputMap.putAll(result);
                return true;
            }
            when else {
                outputMap.put('success', false);
                outputMap.put('errors', new List<Map<String, Object>>{
                    new Map<String, Object>{
                        'code'    => 'UNSUPPORTED_ACTION',
                        'message' => 'Unsupported action: ' + methodName
                    }
                });
                return false;
            }
        }
    }

    private Map<String, Object> actionOne(Map<String, Object> inputMap, Map<String, Object> options) {
        // 1. Validate required keys from inputMap
        // 2. Run business logic (SOQL with WITH USER_MODE, DML with sharing)
        // 3. Return response envelope (written into outputMap by the caller above)
        return new Map<String, Object>{
            'success' => true,
            'data'    => new Map<String, Object>()
        };
    }
}
