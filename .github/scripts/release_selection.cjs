'use strict';
const parts = v => v.split('.').map(Number);
function compare(a, b) {
  const x = parts(a), y = parts(b);
  for (let i = 0; i < 3; i++) if (x[i] !== y[i]) return x[i] - y[i];
  return 0;
}
function selectRelease(releases, stable, attempts, retry = false) {
  const newest = [...stable].sort((a, b) => compare(b, a))[0];
  return releases.filter(r => !r.draft && !r.prerelease && /^\d+\.\d+\.\d+$/.test(r.tag_name))
    .filter(r => compare(r.tag_name, newest) > 0 && !stable.includes(r.tag_name))
    .filter(r => retry || !attempts[r.tag_name] || attempts[r.tag_name].release_updated !== r.updated_at)
    .sort((a, b) => compare(b.tag_name, a.tag_name))[0];
}
module.exports = {selectRelease, compare};
