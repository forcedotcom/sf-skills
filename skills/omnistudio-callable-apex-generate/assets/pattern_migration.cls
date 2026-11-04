// ─────────────────────────────────────────────────────────────────────────────
// BEFORE: VlocityOpenInterface2
// Results written into outputMap by reference; return value is a success flag.
// ─────────────────────────────────────────────────────────────────────────────
// global class OrderOpenInterface implements omnistudio.VlocityOpenInterface2 {
//     global Object invokeMethod(String methodName, Map<String, Object> input,
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
// OmniStudio passes the same three maps in args: { 'input', 'output', 'options' }.
// Results are still written into the output map — OmniStudio reads the response from it.
// Action strings mirror the original methodName values to keep callers stable.
// ─────────────────────────────────────────────────────────────────────────────
public with sharing class Industries_XxxCallable implements System.Callable {

    public Object call(String action, Map<String, Object> args) {
        Map<String, Object> inputMap = (args != null && args.containsKey('input'))
            ? (Map<String, Object>) args.get('input')
            : (args != null ? args : new Map<String, Object>());
        Map<String, Object> output   = (args != null && args.containsKey('output'))
            ? (Map<String, Object>) args.get('output')
            : new Map<String, Object>();
        Map<String, Object> options  = (args != null && args.containsKey('options'))
            ? (Map<String, Object>) args.get('options')
            : new Map<String, Object>();
        if (inputMap == null) { inputMap = new Map<String, Object>(); }
        if (output   == null) { output   = new Map<String, Object>(); }
        if (options  == null) { options  = new Map<String, Object>(); }

        switch on action {
            when 'createOrder' {
                output.putAll(createOrder(inputMap, options));
                return output;
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
