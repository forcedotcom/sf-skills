const BLOCKED_SCHEMES = new Set(["javascript", "data", "file", "blob", "vbscript"]);

function loopbackHost(hostname) {
  const host = hostname.replace(/^\[|\]$/g, "");
  return host === "localhost" || host === "127.0.0.1" || host === "::1";
}

// OAuth redirect URIs are absolute. https is the normal case; http is only
// loopback; native clients may use a custom scheme with a host. Wildcards,
// fragments, and userinfo are not redirect URIs.
export function callbackRejection(raw) {
  if (typeof raw !== "string" || !raw.trim()) return "callback URL is empty";
  const value = raw.trim();
  if (value.includes("*") || value.includes("#") || /\s/.test(value)) {
    return "callback URL must be an absolute redirect URI without wildcards, fragments, or whitespace";
  }
  let url;
  try {
    url = new URL(value);
  } catch {
    return "callback URL must be an absolute URI";
  }
  if (url.username || url.password) return "callback URL must not include userinfo";
  const scheme = url.protocol.slice(0, -1).toLowerCase();
  if (BLOCKED_SCHEMES.has(scheme)) return `callback scheme '${scheme}' is not allowed`;
  if (scheme === "https") {
    return url.hostname ? "" : "https callback URL needs a host";
  }
  if (scheme === "http") {
    return loopbackHost(url.hostname) ? "" : "http callbacks are limited to loopback hosts";
  }
  if (!/^[a-z][a-z0-9+.-]*$/.test(scheme) || !url.hostname) {
    return "custom-scheme callbacks need a scheme and a host";
  }
  return "";
}
