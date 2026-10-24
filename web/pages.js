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

document.getElementById('copy-build').addEventListener('click', async () => {
  try {
    const {json} = await buildConfig();
    if (new TextEncoder().encode(json).length > 60000) throw new Error('این فایل برای کپی در Workflow بزرگ است. توکن GitHub را وارد کنید و Generate را بزنید؛ تصاویر بدون کاهش کیفیت به‌صورت رمزگذاری‌شده ارسال می‌شوند.');
    await navigator.clipboard.writeText(json);
    status('Copied. Open GitHub Actions → Run workflow → paste into config_json. Leave zip_url empty.');
  } catch (error) { status(error.message); }
});

builderForm.addEventListener('submit', async event => {
  event.preventDefault();
  const button = builderForm.querySelector('button[type="submit"]');
  let uploadRef = null;
  let dispatchStarted = false;
  const tokenField = document.getElementById('github-token');
  const token = tokenField.value.trim();
  async function github(path, method = 'GET', body) {
    const response = await fetch(`https://api.github.com/repos/${repository}/${path}`, {
      method, headers: {Accept: 'application/vnd.github+json', Authorization: `Bearer ${token}`, 'Content-Type': 'application/json'},
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(`GitHub ${response.status}: ${detail.message || 'Request failed'}. Token needs Actions and Contents read/write permission.`);
    }
    return response.status === 204 ? null : response.json();
  }
  try {
    const {config, json} = await buildConfig();
    if (!token) {
      status('برای شروع ساخت، توکن GitHub با دسترسی نوشتن Actions و Contents را وارد کنید. ورود به حساب GitHub به‌تنهایی به این صفحه دسترسی ساخت نمی‌دهد.');
      tokenField.closest('details').open = true;
      tokenField.scrollIntoView({behavior: 'smooth', block: 'center'});
      tokenField.focus();
      return;
    }
    if (config.permanentPassword && !document.getElementById('password-artifact-consent').checked) throw new Error('رمز دائمی داخل فایل اجرایی قرار می‌گیرد و خوانندگان مخزن می‌توانند آن را استخراج کنند. رمز را حذف کنید یا تأیید مربوط به رمز را در بخش GitHub فعال کنید.');
    button.disabled = true;
    status('Encrypting configuration and images…');
    const envelope = await encryptConfig(json);
    const head = await github('git/ref/heads/master');
    uploadRef = `rdgen-inputs/${crypto.randomUUID()}`;
    await github('git/refs', 'POST', {ref: `refs/heads/${uploadRef}`, sha: head.object.sha});
    status('Uploading encrypted configuration and images…');
    await github('contents/.rdgen-inputs/payload.json', 'PUT', {message: 'Temporary encrypted build input', branch: uploadRef, content: toBase64(new TextEncoder().encode(JSON.stringify(envelope)))});
    status('Starting GitHub Actions build…');
    dispatchStarted = true;
    await github(`actions/workflows/${workflow}/dispatches`, 'POST', {ref: 'master', inputs: {version: config.version, config_ref: uploadRef, config_json: '', app_version: config.app_version || '', zip_url: ''}});
    status('ساخت شروع شد. برای مشاهدهٔ پیشرفت و دریافت خروجی، Open GitHub Actions را باز کنید.');
    actionsLink.focus();
  } catch (error) {
    if (uploadRef && !dispatchStarted) await github(`git/refs/heads/${uploadRef}`, 'DELETE').catch(() => {});
    status(error.message + (dispatchStarted ? ' Check GitHub Actions before retrying.' : ''));
  }
  finally { button.disabled = false; tokenField.value = ''; }
});
builderForm.addEventListener('input', networkPreview);
networkPreview();
