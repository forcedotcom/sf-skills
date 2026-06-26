global with sharing class MyCustomRemoteClass implements omnistudio.VlocityOpenInterface2 {
    
    global Boolean invokeMethod(String methodName, Map<String,Object> inputMap, Map<String,Object> outputMap, Map<String,Object> options) {
        if (methodName.equals('calculateTotal')) {
            calculateTotal(inputMap, outputMap);
            return true;
        }
        return false;
    }

    private void calculateTotal(Map<String,Object> inputMap, Map<String,Object> outputMap) {
        Decimal price = (Decimal)inputMap.get('price');
        Decimal qty = (Decimal)inputMap.get('quantity');
        outputMap.put('total', price * qty);
    }
}