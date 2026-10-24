'use strict';
const repository = 'mahdinosrati/rdgen';
const workflow = 'generator-windows.yml';
const builderForm = document.getElementById('myForm');
const buildStatus = document.getElementById('build-status');
const actionsLink = document.getElementById('actions-link');
function status(message) {
  buildStatus.textContent = message;
  const nearby = document.getElementById('generate-status');
  if (nearby) nearby.textContent = message;
}
function toBase64(value) {
  const bytes = new Uint8Array(value);
  let text = '';
  for (let offset = 0; offset < bytes.length; offset += 32768) text += String.fromCharCode(...bytes.subarray(offset, offset + 32768));
  return btoa(text);
}
async function encryptConfig(json) {
  const response = await fetch('build-key.json');
  if (!response.ok) throw new Error('Build encryption is not configured.');
  const publicKey = await crypto.subtle.importKey('jwk', await response.json(), {name: 'RSA-OAEP', hash: 'SHA-256'}, false, ['encrypt']);
  const key = await crypto.subtle.generateKey({name: 'AES-GCM', length: 256}, true, ['encrypt']);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const data = await crypto.subtle.encrypt({name: 'AES-GCM', iv, additionalData: new TextEncoder().encode('rdgen-config-v1')}, key, new TextEncoder().encode(json));
  const wrapped = await crypto.subtle.encrypt({name: 'RSA-OAEP'}, publicKey, await crypto.subtle.exportKey('raw', key));
  return {version: 1, key: toBase64(wrapped), iv: toBase64(iv), data: toBase64(data)};
}

function networkPreview() {
  const host = document.getElementById('id_serverIP').value.trim() || 'rs-ny.rustdesk.com';
  const port = document.getElementById('id_serverPort').value || '21116';
  let api = document.getElementById('id_apiServer').value.trim();
  if (api && !api.includes('://')) api = 'http://' + api;
  document.getElementById('network-preview').textContent = JSON.stringify({
    'custom-rendezvous-server': (host.includes(':') && !host.startsWith('[') ? `[${host}]` : host) + ':' + port,
    key: document.getElementById('id_key').value.trim() || (host === 'rs-ny.rustdesk.com' ? 'OeVuKk5nlHiXp+APNn0Y3pC1Iwpwn44JGqrQCsWqmBw=' : ''),
    'relay-server': document.getElementById('id_relayServer').value.trim(),
    'api-server': api.replace(/\/$/, '')
  }, null, 2);
}

async function buildConfig() {
  if (!builderForm.reportValidity()) throw new Error('Please complete the highlighted fields.');
  const config = await saveFormData(false);
  if (!config) throw new Error('A configuration filename is required.');
  if (config.platform !== 'windows') throw new Error('Standalone builds currently support Windows 64-bit. Use Save Configuration for other platforms.');
  const port = String(config.serverPort || '21116');
  if (!/^\d+$/.test(port) || Number(port) < 1 || Number(port) > 65532) throw new Error('Port must be between 1 and 65532.');
  for (const kind of ['icon', 'logo', 'privacy']) {
    if (config[kind + 'file']) delete config[kind + 'base64'];
  }
  const json = JSON.stringify(config);
  if (new TextEncoder().encode(json).length > 15000000) throw new Error('Configuration exceeds 15 MB. Use smaller PNG images.');
  return {config, json};
}

builderForm.addEventListener('submit', async event => {
  event.preventDefault();
  const button = builderForm.querySelector('button[type="submit"]');
  try {
    const {config, json} = await buildConfig();
    if (config.permanentPassword && !document.getElementById('password-artifact-consent').checked) throw new Error('Confirm the permanent password notice before generating a public client.');
    button.disabled = true;
    status('Encrypting configuration and images…');
    const envelope = await encryptConfig(json);
    envelope.build_version = config.version;
    envelope.app_version = config.app_version || '';
    const url = URL.createObjectURL(new Blob([JSON.stringify(envelope)], {type: 'application/json'}));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'payload.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    document.getElementById('upload-instructions').hidden = false;
    status('فایل payload.json آماده شد. روی Upload to GitHub بزنید، همین فایل را انتخاب کنید و Commit changes را روی master انجام دهید. ساخت خودکار شروع می‌شود؛ توکن لازم نیست.');
    document.getElementById('upload-link').focus();
  } catch (error) { status(error.message); }
  finally { button.disabled = false; }
});
builderForm.addEventListener('input', networkPreview);
networkPreview();
