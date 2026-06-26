/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * BULK INSERT 10,000+ RECORDS
 * For Bulk API and large data volume testing
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * ⚠️  IMPORTANT: This script is designed to be run via sf CLI Bulk API
 *     NOT via Anonymous Apex (which has governor limits)
 *
 * PURPOSE:
 * Generate large datasets for:
 * • Bulk API 2.0 testing
 * • Performance testing
 * • Data migration validation
 * • Report/Dashboard testing with realistic volumes
 *
 * APPROACHES:
 * 1. Use sf data import bulk with CSV files (recommended)
 * 2. Use Data Loader for very large datasets
 * 3. Use batch Apex to create in smaller chunks
 *
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// APPROACH 1: BATCH APEX FOR LARGE DATA CREATION
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Batch class to create large number of Account records
 * Execute with: Database.executeBatch(new BulkAccountCreator(10000), 200);
 */
public class BulkAccountCreator implements Database.Batchable<Integer>, Database.Stateful {

    private Integer targetCount;
    private Integer createdCount = 0;
    private String namePrefix;
    private List<String> industries;
    private DateTime startTime;

    public BulkAccountCreator(Integer count) {
        this.targetCount = count;
        this.namePrefix = 'BulkData';
        this.industries = new List<String>{
            'Technology', 'Healthcare', 'Finance', 'Manufacturing',
            'Retail', 'Education', 'Energy', 'Media'
        };
        this.startTime = DateTime.now();
    }

    public Iterable<Integer> start(Database.BatchableContext bc) {
        // Create list of indices to process
        List<Integer> indices = new List<Integer>();
        for (Integer i = 0; i < targetCount; i++) {
            indices.add(i);
        }
        return indices;
    }

    public void execute(Database.BatchableContext bc, List<Integer> indices) {
        List<Account> accounts = new List<Account>();

        for (Integer i : indices) {
            accounts.add(new Account(
                Name = namePrefix + '_' + String.valueOf(i).leftPad(7, '0'),
                Industry = industries[Math.mod(i, industries.size())],
                Type = Math.mod(i, 3) == 0 ? 'Customer' : 'Prospect',
                AnnualRevenue = 50000 + (Math.mod(i, 1000) * 1000),
                NumberOfEmployees = 10 + Math.mod(i, 1000),
                BillingCity = 'San Francisco',
                BillingState = 'CA',
                BillingCountry = 'USA',
                Description = 'Bulk created record ' + i
            ));
        }

        insert accounts;
        createdCount += accounts.size();
    }

    public void finish(Database.BatchableContext bc) {
        DateTime endTime = DateTime.now();
        Long durationMs = endTime.getTime() - startTime.getTime();

        System.debug('═══════════════════════════════════════════════════════════════');
        System.debug('BULK CREATION COMPLETE');
        System.debug('═══════════════════════════════════════════════════════════════');
        System.debug('Records Created: ' + createdCount);
        System.debug('Duration: ' + durationMs + 'ms (' + (durationMs / 1000) + ' seconds)');
        System.debug('Rate: ' + (createdCount * 1000 / durationMs) + ' records/second');
        System.debug('═══════════════════════════════════════════════════════════════');
    }
}

// Execute with:
// Database.executeBatch(new BulkAccountCreator(10000), 200);

// ═══════════════════════════════════════════════════════════════════════════════
// APPROACH 2: GENERATE CSV FOR BULK API IMPORT
// Run this to generate CSV, then use sf data import bulk
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Generate CSV content for bulk import
 * Note: For very large files, generate externally with Python/Node.js
 */
public class BulkCsvGenerator {

    public static String generateAccountCsv(Integer count) {
        List<String> rows = new List<String>();

        // Header
        rows.add('Name,Industry,Type,AnnualRevenue,NumberOfEmployees,BillingCity,BillingState,BillingCountry,Description');

        List<String> industries = new List<String>{
            'Technology', 'Healthcare', 'Finance', 'Manufacturing',
            'Retail', 'Education', 'Energy', 'Media'
        };
        List<String> types = new List<String>{'Prospect', 'Customer', 'Partner'};

        // Data rows
        for (Integer i = 0; i < count; i++) {
            String name = 'BulkImport_' + String.valueOf(i).leftPad(7, '0');
            String industry = industries[Math.mod(i, industries.size())];
            String type = types[Math.mod(i, types.size())];
            Decimal revenue = 50000 + (Math.mod(i, 1000) * 1000);
            Integer employees = 10 + Math.mod(i, 1000);

            rows.add(String.join(new List<String>{
                name,
                industry,
                type,
                String.valueOf(revenue),
                String.valueOf(employees),
                'San Francisco',
                'CA',
                'USA',
                'Bulk imported record ' + i
            }, ','));
        }

        return String.join(rows, '\n');
    }
}

// Usage:
// String csv = BulkCsvGenerator.generateAccountCsv(1000);
// System.debug(csv);
// Then save to file and use: sf data import bulk --file accounts.csv --sobject Account --target-org myorg

// ═══════════════════════════════════════════════════════════════════════════════
// SF CLI BULK IMPORT COMMANDS
// ═══════════════════════════════════════════════════════════════════════════════

/*
STEP 1: Create CSV file with headers and data

Example accounts.csv:
Name,Industry,Type,AnnualRevenue,BillingCity,BillingState,BillingCountry
BulkTest_0000001,Technology,Prospect,100000,San Francisco,CA,USA
BulkTest_0000002,Healthcare,Customer,150000,San Francisco,CA,USA
...

STEP 2: Import using Bulk API 2.0

# Import with wait for completion
sf data import bulk \
  --file accounts.csv \
  --sobject Account \
  --target-org myorg \
  --wait 30

# Import async (returns job ID)
sf data import bulk \
  --file accounts.csv \
  --sobject Account \
  --target-org myorg

# Check job status
sf data bulk results \
  --job-id 7500000000XXXXX \
  --target-org myorg

*/

// ═══════════════════════════════════════════════════════════════════════════════
// PYTHON SCRIPT TO GENERATE LARGE CSV
// ═══════════════════════════════════════════════════════════════════════════════

/*
Save as generate_bulk_data.py:

import csv
import random

industries = ['Technology', 'Healthcare', 'Finance', 'Manufacturing',
              'Retail', 'Education', 'Energy', 'Media']
types = ['Prospect', 'Customer', 'Partner']
cities = ['San Francisco', 'New York', 'Chicago', 'Los Angeles', 'Seattle']
states = ['CA', 'NY', 'IL', 'CA', 'WA']

def generate_accounts(count, filename='accounts.csv'):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Industry', 'Type', 'AnnualRevenue',
                        'NumberOfEmployees', 'BillingCity', 'BillingState',
                        'BillingCountry', 'Description'])

        for i in range(count):
            city_idx = i % len(cities)
            writer.writerow([
                f'BulkTest_{i:07d}',
                industries[i % len(industries)],
                types[i % len(types)],
                50000 + (i % 1000) * 1000,
                10 + (i % 500),
                cities[city_idx],
                states[city_idx],
                'USA',
                f'Bulk test record {i}'
            ])

    print(f'Generated {count} records to {filename}')

if __name__ == '__main__':
    generate_accounts(10000)

Run: python generate_bulk_data.py
Then: sf data import bulk --file accounts.csv --sobject Account --target-org myorg --wait 30

*/

// ═══════════════════════════════════════════════════════════════════════════════
// CLEANUP FOR LARGE DATASETS
// ═══════════════════════════════════════════════════════════════════════════════

/*
CLEANUP via Bulk API:

# Step 1: Export IDs to delete
sf data query \
  --query "SELECT Id FROM Account WHERE Name LIKE 'BulkTest%' OR Name LIKE 'BulkData%' OR Name LIKE 'BulkImport%'" \
  --target-org myorg \
  --result-format csv \
  > delete-accounts.csv

# Step 2: Bulk delete
sf data delete bulk \
  --file delete-accounts.csv \
  --sobject Account \
  --target-org myorg \
  --wait 30

# For hard delete (permanent, requires permission):
sf data delete bulk \
  --file delete-accounts.csv \
  --sobject Account \
  --target-org myorg \
  --hard-delete \
  --wait 30
*/

// ═══════════════════════════════════════════════════════════════════════════════
// BATCH APEX CLEANUP
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Batch class to delete large number of records
 */
public class BulkRecordDeleter implements Database.Batchable<SObject> {

    private String query;

    public BulkRecordDeleter(String soqlQuery) {
        this.query = soqlQuery;
    }

    public Database.QueryLocator start(Database.BatchableContext bc) {
        return Database.getQueryLocator(query);
    }

    public void execute(Database.BatchableContext bc, List<SObject> records) {
        delete records;
    }

    public void finish(Database.BatchableContext bc) {
        System.debug('Bulk delete complete');
    }
}

// Execute with:
// String query = 'SELECT Id FROM Account WHERE Name LIKE \'BulkTest%\'';
// Database.executeBatch(new BulkRecordDeleter(query), 200);
