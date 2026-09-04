# Reference example — `SetCommentValue`

One worked customization the skill ships as a preset. It exists so a reviewer can
see a complete, verified answer to the Phase 5 interview. The skill does not
deploy it by default — the customer picks it explicitly via
`--preset set-comment-value` or by saying "use the SetCommentValue reference"
during the interview. All files below ship under
`assets/set-comment-value/`.

## Interview answers

```json
{
  "stepName": "SetCommentValue",
  "entity": "Tactic",
  "workflows": ["create", "update", "copy"],
  "actionName": "setCommentValue",
  "inputPaths": ["Comment"],
  "outputWrites": [
    { "field": "Comment__c", "source": "Comment" }
  ],
  "description": "Copies the tactic input Comment to Tactic.Comment__c.",
  "preconditions": null,
  "sortAfter": null
}
```

Ships at `assets/set-comment-value/interview-answers.json`.

## Generated class

The class is namespace-agnostic — it works whether the target org has `cgcloud`,
`cgcloud_dev`, or no prefix, because it derives the Tactic namespace from the
passed SObject at runtime and never types `<ns>__Tactic__c` or `<ns>__Comment__c`
at compile time. Context-key names (`currentInput`, `currentOutput`) are the ones
the packaged `BoTransformationEngine` seeds — verified at lines 825–864 of
`BoTransformationEngine.cls`. Ships at
`assets/set-comment-value/SetCommentValue.cls`.

```apex
/**
 * Custom BO API Workflow Step: lifts a top-level `Comment` value out of
 * the ingest tactic input onto Tactic.Comment__c.
 *
 * Registered against the `Tactic` BO API entity and wired into the
 * `create`, `update`, and `copy` workflows.
 */
global with sharing class SetCommentValue implements Callable {

  public class SetCommentValueException extends Exception {}

  // global (not public): the packaged CallableManager must resolve/invoke this
  // subscriber Callable across the namespace boundary on a managed-installed org
  // (a public class fails at runtime with `Type "SetCommentValue" does not exist`).
  global Object call(String action, Map<String, Object> context) {
    if (action != 'setCommentValue') {
      throw new SetCommentValueException('Unsupported action: ' + action);
    }
    if (context == null) {
      throw new SetCommentValueException('null context');
    }

    Object rawInput = context.get('currentInput');
    Object rawOutput = context.get('currentOutput');

    if (!(rawInput instanceof Map<String, Object>)) {
      return null;
    }
    Map<String, Object> tacticInput = (Map<String, Object>) rawInput;
    Object commentValue = tacticInput.get('Comment');
    if (commentValue == null) {
      return null;
    }

    // The engine wraps Tactic__c in TPM_Promotion.TacticRecord (see
    // BoTransformationEngineEntityTree.generateObject:696 —
    //   promo.addTactic(new Tactic__c()) returns a TacticRecord wrapper).
    // Unwrap to the underlying SObject via getRecord() before writing;
    // a raw SObject cast fails silently and the write never persists.
    SObject tactic;
    if (rawOutput instanceof SObject) {
      tactic = (SObject) rawOutput;
    } else if (rawOutput instanceof TPM_Promotion.Record) {
      tactic = ((TPM_Promotion.Record) rawOutput).getRecord();
    } else {
      return null;
    }

    String tacticType = String.valueOf(tactic.getSObjectType());
    String prefix = '';
    if (tacticType.contains('__') && tacticType.endsWith('__c')) {
      Integer firstUnderscoreUnderscore = tacticType.indexOf('__');
      Integer lastUnderscoreUnderscore = tacticType.lastIndexOf('__');
      if (firstUnderscoreUnderscore < lastUnderscoreUnderscore) {
        prefix = tacticType.substring(0, firstUnderscoreUnderscore) + '__';
      }
    }

    tactic.put(prefix + 'Comment__c', String.valueOf(commentValue));
    return null;
  }
}
```

## Class metadata

Ships at `assets/set-comment-value/SetCommentValue.cls-meta.xml`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>60.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

## Reference payloads

Live at `assets/set-comment-value/payloads/`:
- `create.json` — sets `Comment` on a new promotion's tactic.
- `update.json` — updates the tactic's `Comment`.
- `copy.json` — copies the source promotion; expects the tactic's `Comment` to be carried across.

Each carries the `REPLACED-AT-RUNTIME` marker for `importId` (and, for
`update`/`copy`, marker ids for the promotion + tactic captured from the
preceding response).

## Expected write

`Tactic__c.Comment__c` on the created / updated / copied promotion's tactic must
equal the `Comment` value from the corresponding payload — this is the
interview's single `outputWrites` assertion.
