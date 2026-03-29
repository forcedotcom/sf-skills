public without sharing class MaintenanceRequestTriggerHandler {

    /**
     * Handles before insert logic for Maintenance Request records
     * Automatically assigns workers based on request type and updates status to Assigned
     */
    public static void handleBeforeInsert(List<Maintenance_Request__c> newRequests) {
        // Map to store request type to worker type mappings
        Map<String, String> requestTypeToWorkerType = new Map<String, String>{
            'Plumbing'    => 'Plumbing',
            'Electrical'  => 'Electrical',
            'HVAC'        => 'HVAC (Heating & Cooling)',
            'Appliance'   => 'Appliance Repair',
            'Carpentry'   => 'General Carpentry',
            'Landscaping' => 'Landscaping / Grounds',
            'Cleaning'    => 'Janitorial / Cleaning',
            'Pest'        => 'Pest Control'
        };

        // Collect unique worker types needed
        Set<String> workerTypesNeeded = new Set<String>();
        for (Maintenance_Request__c request : newRequests) {
            if (request.Type__c != null && requestTypeToWorkerType.containsKey(request.Type__c)) {
                workerTypesNeeded.add(requestTypeToWorkerType.get(request.Type__c));
            }
        }

        // Query for available workers by type
        Map<String, List<Maintenance_Worker__c>> workersByType = new Map<String, List<Maintenance_Worker__c>>();
        if (!workerTypesNeeded.isEmpty()) {
            for (Maintenance_Worker__c worker : [
                SELECT Id, Name, Type__c, Rating__c
                FROM Maintenance_Worker__c
                WHERE Type__c IN :workerTypesNeeded
                AND IsActive__c = true
                ORDER BY Rating__c DESC NULLS LAST, Name ASC
            ]) {
                if (!workersByType.containsKey(worker.Type__c)) {
                    workersByType.put(worker.Type__c, new List<Maintenance_Worker__c>());
                }
                workersByType.get(worker.Type__c).add(worker);
            }
        }

        // Assign workers to requests
        for (Maintenance_Request__c request : newRequests) {
            // Only process requests with 'New' status (or null, since 'New' is the default)
            if ((request.Status__c == 'New' || request.Status__c == null) &&
                request.Type__c != null && requestTypeToWorkerType.containsKey(request.Type__c)) {
                String workerType = requestTypeToWorkerType.get(request.Type__c);

                // Check if we have available workers for this type
                if (workersByType.containsKey(workerType) && !workersByType.get(workerType).isEmpty()) {
                    // Assign the first available worker (highest rated)
                    Maintenance_Worker__c assignedWorker = workersByType.get(workerType).get(0);
                    request.Assigned_Worker__c = assignedWorker.Id;
                    request.Status__c = 'Assigned';

                    // Set scheduled date to 3 days from now
                    request.Scheduled__c = DateTime.now().addDays(3);

                    // Rotate worker to end of list for round-robin assignment
                    workersByType.get(workerType).remove(0);
                    workersByType.get(workerType).add(assignedWorker);
                }
            }
        }
    }
}