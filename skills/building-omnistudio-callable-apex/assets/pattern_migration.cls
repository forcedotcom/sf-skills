// ─────────────────────────────────────────────────────────────────────────────
// BEFORE: VlocityOpenInterface2
// Results written into outputMap by reference; return value is Boolean success flag.
// ─────────────────────────────────────────────────────────────────────────────
// global class OrderOpenInterface implements omnistudio.VlocityOpenInterface2 {
//     global Boolean invokeMethod(String methodName, Map<String, Object> input,
//                                 Map<String, Object> output,
//                                 Map<String, Object> options) {
//         if (methodName == 'createOrder') {
//             output.putAll(createOrder(input, options));
//             return true;
//         }
//         return false;
//     }
//
//     private Map<String, Object> createOrder(Map<String, Object> inputMap,
//                                             Map<String, Object> options) {
//         return new Map<String, Object>{ 'success' => true };
//     }
// }

// ─────────────────────────────────────────────────────────────────────────────
// AFTER: System.Callable
// Same inputs (inputMap, options); return value replaces outputMap mutation.
// Action strings mirror the original methodName values to keep callers stable.
// ─────────────────────────────────────────────────────────────────────────────
public with sharing class Industries_XxxCallable implements System.Callable {

    public Object call(String action, Map<String, Object> args) {
        Map<String, Object> inputMap = (args != null && args.containsKey('inputMap'))
            ? (Map<String, Object>) args.get('inputMap')
            : (args != null ? args : new Map<String, Object>());
        Map<String, Object> options  = (args != null && args.containsKey('options'))
            ? (Map<String, Object>) args.get('options')
            : new Map<String, Object>();
        if (inputMap == null) { inputMap = new Map<String, Object>(); }
        if (options  == null) { options  = new Map<String, Object>(); }

        switch on action {
            when 'createOrder' {
                return createOrder(inputMap, options);
            }
            when else {
                throw new IndustriesCallableException('Unsupported action: ' + action);
            }
        }
    }

    private Map<String, Object> createOrder(Map<String, Object> inputMap,
                                            Map<String, Object> options) {
        // Validate input, run business logic, return response envelope
        return new Map<String, Object>{ 'success' => true, 'data' => new Map<String, Object>() };
    }
}
