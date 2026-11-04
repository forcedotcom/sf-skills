/**
 * Vanilla System.Callable skeleton — flat args, no Open Interface coupling.
 * Use only when the caller is your own Apex passing flat args. Classes invoked by OmniStudio
 * Remote Actions receive { input, output, options } — use pattern_callable_openinterface.cls.
 *
 * Replace Industries_XxxCallable and actionOne with the actual class/action names.
 */
public with sharing class Industries_XxxCallable implements System.Callable {

    public Object call(String action, Map<String, Object> args) {
        Map<String, Object> input = args != null ? args : new Map<String, Object>();

        switch on action {
            when 'actionOne' {
                return actionOne(input);
            }
            when else {
                throw new IndustriesCallableException('Unsupported action: ' + action);
            }
        }
    }

    private Map<String, Object> actionOne(Map<String, Object> args) {
        // 1. Validate required keys (args are flat: the keys are the inputs)
        if (args == null || args.isEmpty()) {
            return new Map<String, Object>{
                'success' => false,
                'error'   => 'Missing required input'
            };
        }
        // 2. Coerce types safely
        // 3. Run business logic (SOQL with WITH USER_MODE, DML with sharing)
        // 4. Return response envelope
        return new Map<String, Object>{
            'success' => true,
            'data'    => new Map<String, Object>()
        };
    }
}
