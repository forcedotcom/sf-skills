/**
 * Custom BO API Workflow Step: lifts a top-level `Comment` value out of
 * the ingest tactic input onto Tactic.Comment__c.
 *
 * Registered against the `Tactic` BO API entity and wired into the
 * `create`, `update`, and `copy` workflows by the
 * deploy-promotion-bo-api skill.
 *
 * Namespace-agnostic: derives the Tactic namespace from the passed
 * SObject at runtime and never types `<ns>__Tactic__c` at compile time,
 * so the same class works under `cgcloud`, `cgcloud_dev`, and
 * source-deployed (no prefix) orgs.
 *
 * Context keys `currentInput` / `currentOutput` are seeded by the
 * packaged BoTransformationEngine (verified at
 * force-app/main/default/classes/BoTransformationEngine.cls:825-864).
 */
global with sharing class SetCommentValue implements Callable {

  public class SetCommentValueException extends Exception {}

  // MUST be global: on a managed-INSTALLED org the packaged CallableManager
  // resolves/invokes this subscriber Callable across the namespace boundary via
  // Type.forName. A `public` class is invisible there and fails at runtime with
  // `Type "<class>" does not exist` (the ATL row lands in Error). `global` works
  // on both managed-install and same-namespace source/dev orgs.
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
