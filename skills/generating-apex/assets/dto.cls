/**
 * Data Transfer Object for {describe the data this DTO represents}.
 *              Used to pass structured data between layers without exposing SObjects.
 *              Serialization-friendly for use with JSON.serialize/deserialize and API responses.
 *
 * @example
 * // Create from constructor
 * {ClassName} dto = new {ClassName}('value1', 42);
 *
 * // Deserialize from JSON
 * {ClassName} dto = ({ClassName}) JSON.deserialize(jsonString, {ClassName}.class);
 */
public with sharing class {ClassName} {

    // ─── Properties ──────────────────────────────────────────────────────

    /** {Describe this property} */
    public String name { get; set; }

    /** {Describe this property} */
    public Id recordId { get; set; }

    /** {Describe this property} */
    public Boolean isActive { get; set; }

    /** {Describe this property} */
    public List<String> tags { get; set; }

    // TODO: Add additional properties as needed

    // ─── Constructors ────────────────────────────────────────────────────

    /**
     * No-arg constructor for deserialization compatibility
     */
    public {ClassName}() {
        this.tags = new List<String>();
        this.isActive = false;
    }

    /**
     * Parameterized constructor for convenience
     * @param name The name value
     * @param recordId The associated record Id
     */
    public {ClassName}(String name, Id recordId) {
        this();
        this.name = name;
        this.recordId = recordId;
    }

    // ─── Factory Methods ─────────────────────────────────────────────────

    /**
     * Creates a DTO instance from an SObject record
     * @param record The source {SObject} record
     * @return A populated {ClassName} instance
     */
    public static {ClassName} fromSObject(SObject record) {
        if (record == null) {
            return new {ClassName}();
        }

        {ClassName} dto = new {ClassName}();
        dto.recordId = record.Id;
        dto.name = (String) record.get('Name');
        // TODO: Map additional fields

        return dto;
    }

    /**
     * Creates a list of DTOs from a list of SObject records
     * @param records The source records
     * @return List of populated {ClassName} instances
     */
    public static List<{ClassName}> fromSObjects(List<SObject> records) {
        List<{ClassName}> dtos = new List<{ClassName}>();
        if (records == null) {
            return dtos;
        }

        for (SObject record : records) {
            dtos.add(fromSObject(record));
        }
        return dtos;
    }

    // ─── Utility Methods ─────────────────────────────────────────────────

    /**
     * Serializes this DTO to a JSON string
     * @return JSON representation of this DTO
     */
    public String toJson() {
        return JSON.serialize(this);
    }

    /**
     * Deserializes a JSON string into a {ClassName} instance
     * @param jsonString The JSON string to deserialize
     * @return A {ClassName} instance
     */
    public static {ClassName} fromJson(String jsonString) {
        return ({ClassName}) JSON.deserialize(jsonString, {ClassName}.class);
    }
}
