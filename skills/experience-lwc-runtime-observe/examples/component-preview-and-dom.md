# Example — preview a component and grab its DOM

**User:** "Preview `accountTile` from my org `dev-sandbox` and give me the
rendered HTML."

**Agent:**
1. `"<skill_dir>/scripts/verify-toolchain.sh" dev-sandbox` — passes.
2. `OPEN_BROWSER=false sf lightning dev component -o dev-sandbox -n accountTile`
3. Log: `Lightning Preview running at URL: http://localhost:3333/...`
4. Capture the helper output first so a failure aborts the caller, then
   eval the exports:
   ```bash
   frontdoor_env="$("<skill_dir>/scripts/open-frontdoor.sh" dev-sandbox http://localhost:3333/...)" || exit 1
   eval "$frontdoor_env"
   ```
   `$FRONTDOOR_URL_FILE` and `$PREVIEW_URL` are now exported for the
   browser process (do NOT read/print the tempfile's contents).
5. Browser driver reads the URL from `$FRONTDOOR_URL_FILE`, navigates to
   establish session, then deletes the file.
6. Navigate to preview URL, wait for network idle.
7. Compute the selector:
   ```bash
   selector="$("<skill_dir>/scripts/extract-dom.sh" selector accountTile)"
   # → c-account-tile
   ```
8. Pierce `lwr_dev-preview-container` shadow root via the driver, find
   the first `$selector` host, read `element.shadowRoot.innerHTML` into
   `$html_subtree`, and wrap:
   ```bash
   printf '%s' "$html_subtree" \
     | "<skill_dir>/scripts/extract-dom.sh" wrap component accountTile
   ```
   Emits:

```text
DOM_OUTPUT_START
<c-account-tile>
  <!-- rendered shadow DOM here -->
</c-account-tile>
DOM_OUTPUT_END
```
