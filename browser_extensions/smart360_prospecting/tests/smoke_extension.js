const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

assert.strictEqual(manifest.manifest_version, 3);
assert.strictEqual(manifest.background.service_worker, "background.js");
assert(!manifest.permissions.includes("<all_urls>"));
assert(!manifest.host_permissions.includes("<all_urls>"));
assert(manifest.host_permissions.some((host) => host.includes("google.com/maps")));
assert(manifest.host_permissions.some((host) => host.includes("127.0.0.1:8000")));

const referencedFiles = [
  manifest.background.service_worker,
  manifest.action.default_popup,
  ...manifest.content_scripts.flatMap((script) => script.js)
];
for (const file of referencedFiles) {
  assert(fs.existsSync(path.join(root, file)), `${file} does not exist`);
}

const source = fs.readFileSync(path.join(root, "background.js"), "utf8")
  + fs.readFileSync(path.join(root, "lib", "smart360_api.js"), "utf8")
  + fs.readFileSync(path.join(root, "content", "google_maps.js"), "utf8")
  + fs.readFileSync(path.join(root, "popup", "popup.js"), "utf8");

const forbidden = [
  /api[_-]?key\s*[:=]/i,
  /password\s*[:=]/i,
  /secret\s*[:=]/i,
  /token\s*[:=]\s*["'][a-z0-9_\-.]{16,}/i,
  /csrf_exempt/,
  /CORS_ALLOW_ALL_ORIGINS\s*=\s*True/
];
for (const pattern of forbidden) {
  assert(!pattern.test(source), `Forbidden pattern found: ${pattern}`);
}

console.log("Smart360 Prospect smoke validation OK");
