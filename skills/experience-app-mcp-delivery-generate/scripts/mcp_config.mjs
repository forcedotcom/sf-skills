// Connection validation shared by standalone configuration and plugin delivery.
function need(condition, message) { if (!condition) throw new Error(message); }
function text(value, name) { need(typeof value === "string" && value.trim(), `${name} must be a non-empty string`); return value.trim(); }

// Org environment → route segment between the domain token and the site.
const ENVIRONMENT_SEGMENTS = { production: "", developer: "develop", sandbox: "sandbox", scratch: "scratch" };

function checkDomain(domain, environment) {
  need(/^[a-z0-9]+(?:[a-z0-9.-]*[a-z0-9])?$/.test(domain) && !domain.includes(".."), "domain must be the routing domain token, not a URL or full instance hostname");
  need(!domain.endsWith("salesforce.com"), "Use the routing domain token, not the full Salesforce hostname");
  need(!domain.includes("."), `${environment} domain must not contain dots`);
  if (environment === "sandbox") need(/^[a-z0-9-]+--[a-z0-9]+$/.test(domain), "sandbox domain must be {my-domain}--{sandbox-name}");
  else need(!domain.includes("--"), `${environment} domain must not contain a sandbox suffix`);
}

function mcpUrl(mcp) {
  need(mcp.sitePrefix === undefined, "mcp.sitePrefix is no longer supported; supply the exact site developer name as mcp.siteDeveloperName");
  if (mcp.url) {
    need(!mcp.domain && !mcp.environment && mcp.siteDeveloperName === undefined, "Supply a verified URL or route components, not both");
    const url = new URL(mcp.url);
    need(url.protocol === "https:" && !url.username && !url.password && !url.search && !url.hash, "MCP URL must use HTTPS without credentials, query, or fragment");
    return url.href;
  }
  const environment = text(mcp.environment, "mcp.environment");
  need(Object.hasOwn(ENVIRONMENT_SEGMENTS, environment), `mcp.environment must be one of: ${Object.keys(ENVIRONMENT_SEGMENTS).join(", ")}`);
  const domain = text(mcp.domain, "mcp.domain");
  checkDomain(domain, environment);
  const siteDeveloperName = text(mcp.siteDeveloperName, "mcp.siteDeveloperName");
  need(/^[A-Za-z0-9_-]+$/.test(siteDeveloperName), "siteDeveloperName must be the exact site developer name without slashes");
  const name = text(mcp.mcpName, "mcp.mcpName");
  need(/^[A-Za-z][A-Za-z0-9_]*$/.test(name), "mcpName must be the exact server DeveloperName");
  const segment = ENVIRONMENT_SEGMENTS[environment];
  return `https://api.salesforce.com/platform/mcp/v1/p/${encodeURIComponent(domain)}/${segment ? `${segment}/` : ""}${encodeURIComponent(siteDeveloperName)}/custom/${encodeURIComponent(name)}`;
}

export function createMcpConfig(config) {
  need(config.mcp && typeof config.mcp === "object", "mcp configuration is required");
  const serverKey = text(config.mcp.serverName, "mcp.serverName");
  need(/^[A-Za-z0-9_-]+$/.test(serverKey), "mcp.serverName must contain letters, numbers, underscores, or hyphens");
  const clientId = text(config.mcp.clientId, "mcp.clientId");
  need(!/[\s<>]/.test(clientId), "Use the actual ECA consumer key as clientId, not a placeholder or ECA record ID");
  need(clientId !== config.mcp.ecaId, "clientId must be the ECA consumer key, not its record ID");
  const url = mcpUrl(config.mcp);
  // Custom client conventions must be explicitly selected, not inferred from submission.
  const authStyle = config.authStyle ?? "claude-code";
  need(["requested", "claude-code"].includes(authStyle), "authStyle must be requested or claude-code");
  const server = { type: "http", url };
  if (authStyle === "requested") server.auth = { CLIENT_ID: clientId };
  else server.oauth = { clientId };
  if (config.mcp.callbackPort !== undefined) {
    need(authStyle === "claude-code", "mcp.callbackPort requires the claude-code OAuth profile");
    const port = config.mcp.callbackPort;
    need(Number.isInteger(port) && port >= 1 && port <= 65535, "mcp.callbackPort must be a JSON integer from 1 through 65535; omit it when skipped");
    server.oauth.callbackPort = port;
  }
  return { mcpServers: { [serverKey]: server } };
}
