/**
 * System.Callable skeleton — OmniStudio Remote Action contract.
 * OmniStudio (OmniScript / Integration Procedure / Data Mapper) calls call(action, args) with
 *   args = { 'input' => Map<String,Object>, 'output' => Map<String,Object>, 'options' => Map<String,Object> }
 * Results must be written into the 'output' map — OmniStudio returns its contents to the caller.
 * Backward-compatible: if args lacks 'input', treats args itself as input (direct Apex callers).
 *
 * Replace Industries_XxxCallable and actionOne with the actual class/action names.
 */
public with sharing class Industries_XxxCallable implements System.Callable {

    public Object call(String action, Map<String, Object> args) {
        Map<String, Object> input = (args != null && args.containsKey('input'))
            ? (Map<String, Object>) args.get('input')
            : (args != null ? args : new Map<String, Object>());
        Map<String, Object> output = (args != null && args.containsKey('output'))
            ? (Map<String, Object>) args.get('output')
            : new Map<String, Object>();
        Map<String, Object> options = (args != null && args.containsKey('options'))
            ? (Map<String, Object>) args.get('options')
            : new Map<String, Object>();
        if (input   == null) { input   = new Map<String, Object>(); }
        if (output  == null) { output  = new Map<String, Object>(); }
        if (options == null) { options = new Map<String, Object>(); }

        switch on action {
            when 'actionOne' {
                output.putAll(actionOne(input, options));
                return output;
            }
            when else {
                throw new IndustriesCallableException('Unsupported action: ' + action);
            }
        }
    }

    private Map<String, Object> actionOne(Map<String, Object> input, Map<String, Object> options) {
        // 1. Validate required keys from input
        // 2. Coerce types safely
        // 3. Run business logic (SOQL with WITH USER_MODE, DML with sharing)
        // 4. Return response envelope (copied into the output map by call())
        return new Map<String, Object>{
            'success' => true,
            'data'    => new Map<String, Object>()
        };
    }
}
