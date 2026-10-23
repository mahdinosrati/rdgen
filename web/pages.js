'use strict';
const repository = 'mahdinosrati/rdgen';
const workflow = 'generator-windows.yml';
const builderForm = document.getElementById('myForm');
const buildStatus = document.getElementById('build-status');
const actionsLink = document.getElementById('actions-link');

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
  const json = JSON.stringify(config);
  if (new TextEncoder().encode(json).length > 60000) throw new Error('Configuration exceeds the GitHub input limit. Use smaller PNG images.');
  return {config, json};
}

document.getElementById('copy-build').addEventListener('click', async () => {
  try {
    const {json} = await buildConfig();
    await navigator.clipboard.writeText(json);
    buildStatus.textContent = 'Copied. Open GitHub Actions → Run workflow → paste into config_json. Leave zip_url empty.';
  } catch (error) { buildStatus.textContent = error.message; }
});

builderForm.addEventListener('submit', async event => {
  event.preventDefault();
  const button = builderForm.querySelector('button[type="submit"]');
  try {
    const {config, json} = await buildConfig();
    const token = document.getElementById('github-token').value.trim();
    if (!token) {
      buildStatus.textContent = 'Use “Copy build JSON” and “Open GitHub Actions”, or enter a GitHub token above for direct submission.';
      buildStatus.scrollIntoView({behavior: 'smooth', block: 'center'});
      return;
    }
    button.disabled = true;
    buildStatus.textContent = 'Submitting build to GitHub…';
    const response = await fetch(`https://api.github.com/repos/${repository}/actions/workflows/${workflow}/dispatches`, {
      method: 'POST',
      headers: {Accept: 'application/vnd.github+json', Authorization: `Bearer ${token}`, 'Content-Type': 'application/json'},
      body: JSON.stringify({ref: 'master', inputs: {version: config.version, config_json: json, app_version: config.app_version || '', zip_url: ''}})
    });
    document.getElementById('github-token').value = '';
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(`GitHub ${response.status}: ${detail.message || 'Build request failed'}`);
    }
    buildStatus.textContent = 'Build accepted. Open GitHub Actions to follow progress and download the Windows client when it finishes.';
    actionsLink.focus();
  } catch (error) { buildStatus.textContent = error.message; }
  finally { button.disabled = false; }
});
builderForm.addEventListener('input', networkPreview);
networkPreview();
