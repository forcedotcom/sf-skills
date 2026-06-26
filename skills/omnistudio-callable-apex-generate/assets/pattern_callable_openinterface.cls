/**
 * System.Callable skeleton — same inputMap/options structure as VlocityOpenInterface.
 * Use when integrating with Open Interface callers or when callers pass { inputMap, options }.
 * Backward-compatible: if args lacks 'inputMap', treats args itself as inputMap.
 *
 * Replace Industries_XxxCallable and actionOne with the actual class/action names.
 */
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
            when 'actionOne' {
                return actionOne(inputMap, options);
            }
            when else {
                throw new IndustriesCallableException('Unsupported action: ' + action);
            }
        }
    }

    private Map<String, Object> actionOne(Map<String, Object> inputMap, Map<String, Object> options) {
        // 1. Validate required keys from inputMap
        // 2. Coerce types safely
        // 3. Run business logic (SOQL with WITH USER_MODE, DML with sharing)
        // 4. Return response envelope
        return new Map<String, Object>{
            'success' => true,
            'data'    => new Map<String, Object>()
        };
    }
}
