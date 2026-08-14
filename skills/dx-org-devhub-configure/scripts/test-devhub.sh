#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$SCRIPT_DIR/devhub.sh"
WORK_DIR="$(mktemp -d)"
STUB_DIR="$WORK_DIR/bin"
LOG_FILE="$WORK_DIR/sf.log"
MARKER="$WORK_DIR/trap-injection"
mkdir -p "$STUB_DIR"
trap 'rm -rf -- "$WORK_DIR"' EXIT

cat > "$STUB_DIR/sf" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$SF_STUB_LOG"

case "$*" in
  "config get target-org --json")
    printf '%s\n' '{"status":0,"result":[{"value":"default-org"}]}'
    ;;
  "config get target-dev-hub --json")
    printf '%s\n' '{"status":0,"result":[{"value":"default-devhub"}]}'
    ;;
  org\ login\ web*)
    printf '%s\n' '{"status":0,"result":{"username":"logged-in@example.com"}}'
    ;;
  "data query --query SELECT COUNT() FROM ScratchOrgInfo"*)
    if [ "${SF_TEST_DEVHUB_ENABLED:-0}" = "1" ]; then
      printf '%s\n' '{"status":0,"result":{"totalSize":0}}'
    else
      printf '%s\n' '{"status":1,"name":"INVALID_TYPE","message":"ScratchOrgInfo unavailable"}'
      exit 1
    fi
    ;;
  "org list limits"*)
    if [ "${SF_TEST_LIMITS_FAIL:-0}" = "1" ]; then
      printf '%s\n' '{"status":1,"message":"limits unavailable"}'
      exit 1
    fi
    printf '%s\n' '{"status":0,"result":[{"name":"ActiveScratchOrgs","remaining":3,"max":3},{"name":"DailyScratchOrgs","remaining":6,"max":6}]}'
    ;;
  "org display"*)
    printf '%s\n' '{"status":0,"result":{"id":"00D000000000001","username":"admin@example.com","instanceUrl":"https://example.my.salesforce.com"}}'
    ;;
  "project deploy start"*)
    printf '%s\n' '{"status":0,"result":{"success":true,"checkOnly":true}}'
    ;;
  *)
    printf '%s\n' '{"status":1,"message":"unexpected sf invocation"}'
    exit 1
    ;;
esac
EOF
chmod +x "$STUB_DIR/sf"

export PATH="$STUB_DIR:$PATH"
export SF_STUB_LOG="$LOG_FILE"

pass=0
fail=0

check() {
  local name="$1" expected_rc="$2" expected_text="$3"
  shift 3
  local output rc
  : > "$LOG_FILE"
  output="$("$@" 2>&1)"
  rc=$?
  if [ "$rc" -eq "$expected_rc" ] && { [ "$expected_text" = "-" ] || printf '%s' "$output" | grep -Fq -- "$expected_text"; }; then
    pass=$((pass + 1))
    printf 'PASS: %s\n' "$name"
  else
    fail=$((fail + 1))
    printf 'FAIL: %s (exit %s, expected %s)\n%s\n' "$name" "$rc" "$expected_rc" "$output"
  fi
}

check "reject disabling the master switch" 2 "cannot be set to false" \
  "$SCRIPT" explicit-org --pref enableScratchOrgManagementPref=false

check "warn for scratch-management apply" 0 "IRREVERSIBLE" \
  "$SCRIPT" explicit-org --scratch-management --apply

check "propagate status allocation failure" 1 "Could not read org limits" \
  env SF_TEST_DEVHUB_ENABLED=1 SF_TEST_LIMITS_FAIL=1 "$SCRIPT" explicit-org

check "require explicit target for apply" 2 "explicit org" \
  "$SCRIPT" --enable --apply

check "reject non-Salesforce login origin" 2 "Salesforce hostname" \
  "$SCRIPT" explicit-org --instance-url https://attacker.example --login

check "login-only exits after authentication" 0 "Authenticated" \
  "$SCRIPT" explicit-org --login
if grep -Fq "data query" "$LOG_FILE"; then
  fail=$((fail + 1))
  printf 'FAIL: login-only queried org status\n'
else
  pass=$((pass + 1))
  printf 'PASS: login-only skipped org status\n'
fi

unsafe_tmp="$WORK_DIR/unsafe'; touch $MARKER; #"
mkdir -p "$unsafe_tmp"
check "cleanup trap does not execute TMPDIR content" 0 "Dry run passed" \
  env TMPDIR="$unsafe_tmp" "$SCRIPT" explicit-org --packaging
if [ -e "$MARKER" ]; then
  fail=$((fail + 1))
  printf 'FAIL: cleanup trap executed TMPDIR content\n'
else
  pass=$((pass + 1))
  printf 'PASS: cleanup trap treated TMPDIR as data\n'
fi

printf '\nRESULT: %s passed, %s failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
