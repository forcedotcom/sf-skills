# SFMC SDK Migrator evaluations

Run from the `sf-skills` repository root:

```bash
python3 skills/sfmc-sdk-migrator/evals/run_evals.py
python3 skills/sfmc-sdk-migrator/evals/run_evals.py --json
```

The runner uses Python's standard library and needs no network, LLM, or mobile
build tools. It tests seven fixture scenarios: full Android migration, Gradle
version catalog, already modern Android, full iOS migration, CocoaPods-only iOS,
SPM-only iOS, and already modern iOS. The 62 deterministic assertions cover SDK
integration, current version, architecture era, features, and target selection.

`evals.json` also defines 23 rewrite-quality assertions. These are skipped unless
a migrated output tree is supplied and the assertion has static checks. Passing
the deterministic tier does not prove the skill rewrites or builds an app correctly.

To check a real migration, copy a fixture to a temporary directory, apply the
skill there, then supply the resulting tree (fixture-relative paths preserved):

```bash
python3 skills/sfmc-sdk-migrator/evals/run_evals.py --eval 0 --with-skill 0=/tmp/out-full --verbose
```

`--with-skill ID=PATH` is repeatable. Missing files referenced by static checks
fail; assertions without static checks remain for human or model review.
The runner exits nonzero if any checked assertion fails.

`trigger-evals.json` contains positive and negative routing prompts for Android,
iOS, version bumps, and unrelated tasks. These require a separate routing evaluator
and are not executed by `run_evals.py`.

When changing detection logic, inspect the actual scanner output before updating
assertions. Scanner matching includes comments, so avoid putting incidental SDK
symbols in fixture comments. Fixtures are source snippets for detection and
rewrite evaluation; they are not complete buildable mobile applications.
