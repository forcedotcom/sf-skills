/**
 * @description Callable implementation for calculateTotal (converted from VlocityOpenInterface).
 *              Accepts Price and Quantity, returns TotalAmount in response envelope.
 * @author      building-omnistudio-callable-apex
 */
public with sharing class MyCustomCallable implements System.Callable {

    public Object call(String action, Map<String, Object> args) {
        Map<String, Object> inputMap = (args != null && args.containsKey('inputMap'))
            ? (Map<String, Object>) args.get('inputMap') : (args != null ? args : new Map<String, Object>());
        Map<String, Object> options  = (args != null && args.containsKey('options'))
            ? (Map<String, Object>) args.get('options')  : new Map<String, Object>();
        if (inputMap == null) { inputMap = new Map<String, Object>(); }
        if (options  == null) { options  = new Map<String, Object>(); }

        switch on action {
            when 'calculateTotal' {
                return calculateTotal(inputMap, options);
            }
            when else {
                throw new IndustriesCallableException('Unsupported action: ' + action);
            }
        }
    }

    private Map<String, Object> calculateTotal(Map<String, Object> inputMap, Map<String, Object> options) {
        Decimal price = toDecimal(inputMap.get('Price'));
        Integer qty   = toInteger(inputMap.get('Quantity'));

        if (price == null || qty == null) {
            return new Map<String, Object>{
                'success' => false,
                'data'    => new Map<String, Object>(),
                'errors'  => new List<Map<String, Object>>{
                    new Map<String, Object>{
                        'code'    => 'INVALID_INPUT',
                        'message' => 'Price and Quantity are required and must be numeric'
                    }
                }
            };
        }

        Decimal total = price * qty;

        return new Map<String, Object>{
            'success' => true,
            'data'    => new Map<String, Object>{ 'TotalAmount' => total },
            'errors'  => new List<Map<String, Object>>()
        };
    }

    private Decimal toDecimal(Object o) {
        if (o == null) return null;
        if (o instanceof Decimal) return (Decimal) o;
        if (o instanceof Integer) return Decimal.valueOf((Integer) o);
        if (o instanceof Double)  return Decimal.valueOf((Double) o);
        if (o instanceof String) {
            try { return Decimal.valueOf((String) o); } catch (TypeException e) { return null; }
        }
        return null;
    }

    private Integer toInteger(Object o) {
        if (o == null) return null;
        if (o instanceof Integer) return (Integer) o;
        if (o instanceof Long)    return ((Long) o).intValue();
        if (o instanceof Decimal) return ((Decimal) o).intValue();
        if (o instanceof String) {
            try { return Integer.valueOf((String) o); } catch (TypeException e) { return null; }
        }
        return null;
    }
}
