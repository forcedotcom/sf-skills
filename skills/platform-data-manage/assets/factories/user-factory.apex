/**
 * Test Data Factory for User records
 * Supports creation of test users with various profiles and roles
 *
 * NOTE: User creation requires specific permissions and may fail in some orgs.
 * Users created in tests are automatically rolled back.
 *
 * Usage:
 *   User testUser = TestDataFactory_User.createStandardUser();
 *   User adminUser = TestDataFactory_User.createSystemAdmin();
 *   List<User> users = TestDataFactory_User.create(5, 'Standard User');
 */
public class TestDataFactory_User {

    private static final String DEFAULT_EMAIL_DOMAIN = 'testuser.example.com';
    private static final String DEFAULT_LOCALE = 'en_US';
    private static final String DEFAULT_LANGUAGE = 'en_US';
    private static final String DEFAULT_TIMEZONE = 'America/Los_Angeles';
    private static final String DEFAULT_ENCODING = 'UTF-8';

    /**
     * Create a single Standard User
     * @return Inserted User record
     */
    public static User createStandardUser() {
        return createWithProfile('Standard User');
    }

    /**
     * Create a single System Administrator
     * @return Inserted User record
     */
    public static User createSystemAdmin() {
        return createWithProfile('System Administrator');
    }

    /**
     * Create a single User with a specific Profile
     * @param profileName Profile name
     * @return Inserted User record
     */
    public static User createWithProfile(String profileName) {
        List<User> users = create(1, profileName);
        return users.isEmpty() ? null : users[0];
    }

    /**
     * Create multiple Users with a specific Profile
     * @param count Number of users to create
     * @param profileName Profile name
     * @return List of inserted User records
     */
    public static List<User> create(Integer count, String profileName) {
        return create(count, profileName, true);
    }

    /**
     * Create multiple Users with insert option
     * @param count Number of users to create
     * @param profileName Profile name
     * @param doInsert Whether to insert records
     * @return List of User records
     */
    public static List<User> create(Integer count, String profileName, Boolean doInsert) {
        // Query the Profile
        List<Profile> profiles = [
            SELECT Id, Name
            FROM Profile
            WHERE Name = :profileName
            LIMIT 1
        ];

        if (profiles.isEmpty()) {
            throw new TestDataFactoryException('Profile not found: ' + profileName);
        }

        Profile p = profiles[0];

        List<User> records = new List<User>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i, p.Id));
        }

        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Users with a specific Role
     * @param count Number of users to create
     * @param profileName Profile name
     * @param roleName Role DeveloperName
     * @return List of inserted User records
     */
    public static List<User> createWithRole(Integer count, String profileName, String roleName) {
        // Query the Profile
        List<Profile> profiles = [
            SELECT Id FROM Profile WHERE Name = :profileName LIMIT 1
        ];
        if (profiles.isEmpty()) {
            throw new TestDataFactoryException('Profile not found: ' + profileName);
        }

        // Query the Role
        List<UserRole> roles = [
            SELECT Id FROM UserRole WHERE DeveloperName = :roleName LIMIT 1
        ];
        if (roles.isEmpty()) {
            throw new TestDataFactoryException('Role not found: ' + roleName);
        }

        List<User> records = new List<User>();
        for (Integer i = 0; i < count; i++) {
            User u = buildRecord(i, profiles[0].Id);
            u.UserRoleId = roles[0].Id;
            records.add(u);
        }

        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create a Community/Experience Cloud User
     * @param contactId Contact ID for the community user
     * @param communityProfileName Community profile name
     * @return Inserted community User record
     */
    public static User createCommunityUser(Id contactId, String communityProfileName) {
        // Query the Profile
        List<Profile> profiles = [
            SELECT Id FROM Profile WHERE Name = :communityProfileName LIMIT 1
        ];
        if (profiles.isEmpty()) {
            throw new TestDataFactoryException('Community Profile not found: ' + communityProfileName);
        }

        // Get Contact details
        Contact con = [
            SELECT Id, FirstName, LastName, Email, AccountId
            FROM Contact
            WHERE Id = :contactId
            LIMIT 1
        ];

        String uniqueId = String.valueOf(DateTime.now().getTime());
        String alias = (con.FirstName != null ? con.FirstName.substring(0, 1) : 'X') +
                       con.LastName.substring(0, Math.min(4, con.LastName.length()));

        User u = new User(
            FirstName = con.FirstName,
            LastName = con.LastName,
            Email = con.Email,
            Username = 'community.' + uniqueId + '@' + DEFAULT_EMAIL_DOMAIN,
            Alias = alias.toLowerCase(),
            ProfileId = profiles[0].Id,
            ContactId = contactId,
            LocaleSidKey = DEFAULT_LOCALE,
            LanguageLocaleKey = DEFAULT_LANGUAGE,
            TimeZoneSidKey = DEFAULT_TIMEZONE,
            EmailEncodingKey = DEFAULT_ENCODING,
            IsActive = true
        );

        insert u;
        return u;
    }

    /**
     * Create an inactive User for historical/deactivated user testing
     * @param profileName Profile name
     * @return Inserted inactive User record
     */
    public static User createInactiveUser(String profileName) {
        User u = createWithProfile(profileName);
        u.IsActive = false;
        update u;
        return u;
    }

    /**
     * Build a single User record with default values
     * @param index Record index for unique naming
     * @param profileId Profile ID
     * @return User record (not inserted)
     */
    private static User buildRecord(Integer index, Id profileId) {
        String uniqueId = String.valueOf(DateTime.now().getTime()) + String.valueOf(index);
        String indexStr = String.valueOf(index).leftPad(5, '0');

        return new User(
            FirstName = 'Test',
            LastName = 'User' + indexStr,
            Email = 'testuser' + uniqueId + '@' + DEFAULT_EMAIL_DOMAIN,
            Username = 'testuser' + uniqueId + '@' + DEFAULT_EMAIL_DOMAIN,
            Alias = 'tuser' + index,
            ProfileId = profileId,
            LocaleSidKey = DEFAULT_LOCALE,
            LanguageLocaleKey = DEFAULT_LANGUAGE,
            TimeZoneSidKey = DEFAULT_TIMEZONE,
            EmailEncodingKey = DEFAULT_ENCODING,
            IsActive = true,
            Street = '123 Test User Street',
            City = 'San Francisco',
            State = 'CA',
            PostalCode = '94105',
            Country = 'USA',
            Phone = '(555) 700-' + String.valueOf(1000 + index),
            MobilePhone = '(555) 800-' + String.valueOf(1000 + index),
            Title = 'Test User',
            Department = 'Test Department',
            CompanyName = 'Test Company'
        );
    }

    /**
     * Run code as a specific user (for testing user context)
     * @param userId User ID to run as
     * @param callback Runnable code to execute
     */
    public static void runAs(Id userId, Runnable callback) {
        User u = [SELECT Id FROM User WHERE Id = :userId LIMIT 1];
        System.runAs(u) {
            callback.run();
        }
    }

    /**
     * Interface for runnable callback
     */
    public interface Runnable {
        void run();
    }

    /**
     * Get IDs of created records for cleanup
     * @param records List of User records
     * @return Set of User IDs
     */
    public static Set<Id> getIds(List<User> records) {
        Set<Id> ids = new Set<Id>();
        for (User u : records) {
            if (u.Id != null) {
                ids.add(u.Id);
            }
        }
        return ids;
    }

    /**
     * Deactivate users (cannot delete Users)
     * @param recordIds Set of User IDs to deactivate
     */
    public static void cleanup(Set<Id> recordIds) {
        if (!recordIds.isEmpty()) {
            List<User> usersToDeactivate = [
                SELECT Id, IsActive
                FROM User
                WHERE Id IN :recordIds AND IsActive = true
            ];
            for (User u : usersToDeactivate) {
                u.IsActive = false;
            }
            if (!usersToDeactivate.isEmpty()) {
                update usersToDeactivate;
            }
        }
    }

    /**
     * Custom exception for factory errors
     */
    public class TestDataFactoryException extends Exception {}
}
