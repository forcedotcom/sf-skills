global class MyCustomClass implements vlocity_cmt.VlocityOpenInterface {
    
    global Boolean invokeMethod(String methodName, Map<String, Object> inputs, 
                                Map<String, Object> output, Map<String, Object> options) {
        
        if (methodName == 'calculateTotal') {
            calculateTotal(inputs, output);
        }
        return true;
    }

    private void calculateTotal(Map<String, Object> inputs, Map<String, Object> output) {
        // Retrieve inputs from OmniScript/IP
        Decimal price = (Decimal)inputs.get('Price');
        Integer qty = (Integer)inputs.get('Quantity');
        
        // Perform calculation
        Decimal total = price * qty;
        
        // Return result to JSON
        output.put('TotalAmount', total);
    }
}