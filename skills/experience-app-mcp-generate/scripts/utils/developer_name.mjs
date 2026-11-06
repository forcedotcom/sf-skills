// DeveloperName values are interpolated into SOQL and filenames.
// Allow one managed-package separator (ns__Name). Reject a second double
// underscore, a trailing underscore, and anything over 80 characters.
const DEVELOPER_NAME =
  /^(?:[A-Za-z][A-Za-z0-9]{0,14}__)?[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*$/;

export function isValidDeveloperName(name) {
  return typeof name === "string" && name.length > 0 && name.length <= 80 && DEVELOPER_NAME.test(name);
}
