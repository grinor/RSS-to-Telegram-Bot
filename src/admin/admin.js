'use strict';
let token = '', data = null, previewFile = null, noticeTimer;
const $ = s => document.querySelector(s);
const el = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
const formats = {
  notify: ['通知', [[1, '开启'], [0, '静音']]],
  send_mode: ['发送方式', [[0, '自动'], [-1, '链接'], [1, 'Telegraph'], [2, 'Telegram 消息']]],
  link_preview: ['链接预览', [[0, '自动'], [1, '启用']]],
  display_author: ['作者', [[0, '自动'], [1, '显示'], [-1, '隐藏']]],
  display_via: ['来源', [[0, '自动'], [1, '显示'], [-1, '仅链接'], [-2, '隐藏']]],
  display_title: ['标题', [[0, '自动'], [1, '显示'], [-1, '隐藏']]],
  display_entry_tags: ['文章标签', [[0, '自动'], [1, '显示'], [-1, '隐藏']]],
  style: ['排版风格', [[0, 'RSStT'], [1, 'flowerss']]],
  display_media: ['媒体', [[0, '启用'], [-1, '禁用']]]
};
function notice(message) { $('#notice').textContent = message; $('#notice').hidden = false; clearTimeout(noticeTimer); noticeTimer = setTimeout(() => $('#notice').hidden = true, 7000); }
async function api(path, {method = 'GET', body, headers = {}} = {}) {
  const opts = {method, headers: {...headers, Authorization: `Bearer ${token}`}};
  if (body !== undefined) { opts.body = body instanceof File ? body : JSON.stringify(body); if (!(body instanceof File)) opts.headers['Content-Type'] = 'application/json'; }
  const res = await fetch(path, opts);
  if (!res.ok) { const info = await res.json().catch(() => ({})); if (res.status === 401) logout(); throw new Error(info.error || `请求失败 (${res.status})`); }
  return res;
}
function logout() { token = ''; data = null; $('#app').classList.add('hidden'); $('#login').classList.remove('hidden'); $('#token').value = ''; document.querySelectorAll('dialog[open]').forEach(d => d.close()); }
const kind = u => u.state === 50 ? '频道' : u.state === 51 ? '群聊' : u.id < 0 ? '群组' : '私聊';
const targetLabel = u => `${kind(u)} · ${u.id}`;
function targetOptions(select, all = false) { select.replaceChildren(); if (all) select.append(new Option('所有接收目标', '')); data.users.forEach(u => select.append(new Option(targetLabel(u), String(u.id)))); }
async function refresh() {
  const selected = $('#target-filter').value;
  data = await (await api('/api/state')).json();
  $('#bot-name').textContent = data.bot.username ? `@${data.bot.username}` : '当前 Bot';
  $('#total').textContent = data.subscriptions.length;
  $('#enabled').textContent = data.subscriptions.filter(s => s.state === 1).length;
  $('#target-count').textContent = data.users.length;
  targetOptions($('#target-filter'), true); $('#target-filter').value = selected;
  for (const [k, v] of Object.entries(data.options)) if ($('#settings-form').elements[k]) $('#settings-form').elements[k].value = v;
  renderSubs(); renderTargets();
}
function renderSubs() {
  const root = $('#subscriptions'); root.replaceChildren();
  const term = $('#search').value.toLocaleLowerCase(), target = $('#target-filter').value, state = $('#state-filter').value;
  const subs = data.subscriptions.filter(s => (!target || String(s.user_id) === target) && (!state || String(s.state) === state) &&
    `${s.title || ''} ${s.feed.title} ${s.feed.link} ${JSON.stringify(s.keyword_filter || {})}`.toLocaleLowerCase().includes(term));
  for (const s of subs) {
    const card = el('div', undefined, 'card subscription'), content = el('div');
    content.append(el('h3', s.title || s.feed.title || '未命名订阅'), el('div', s.feed.link, 'url'));
    const u = data.users.find(u => u.id === s.user_id);
    content.append(el('span', u ? targetLabel(u) : s.user_id, 'pill'), el('span', s.state ? '启用中' : '已暂停', `pill ${s.state ? '' : 'off'}`));
    const r = s.keyword_filter;
    if (r && (r.include.length || r.exclude.length)) content.append(el('span', `包含 ${r.include.length} · 排除 ${r.exclude.length}`, 'pill'));
    if (s.feed.error_count) content.append(el('span', `抓取失败 ${s.feed.error_count} 次`, 'pill off'));
    if (s.state && !s.feed.state) content.append(el('span', '源已停用，请暂停后重新启用以重试', 'pill off'));
    const actions = el('div', undefined, 'actions');
    for (const [name, action, cls] of [['编辑', () => openSub(s), 'secondary'], [s.state ? '暂停' : '启用', () => mutate(`/api/subscriptions/${s.id}`, 'PATCH', {state: s.state ? 0 : 1}), 'secondary'], ['删除', async () => { if (confirm(`删除「${s.title || s.feed.title}」的此条订阅？`)) await mutate(`/api/subscriptions/${s.id}`, 'DELETE'); }, 'danger']]) {
      const b = el('button', name, cls); b.onclick = () => run(action); actions.append(b);
    }
    card.append(content, actions); root.append(card);
  }
  if (!subs.length) root.append(el('div', '没有符合条件的订阅。可以添加 RSS 地址开始使用。', 'card empty'));
}
function renderTargets() {
  $('#targets').replaceChildren();
  for (const u of data.users) {
    const row = el('div', undefined, 'row target-row'), text = el('div');
    text.append(el('strong', targetLabel(u)), el('div', `${data.subscriptions.filter(s => s.user_id === u.id).length} 条订阅 · 默认间隔 ${u.interval || '跟随全局'}${u.state === -1 ? ' · 已封禁' : ''}`, 'muted'));
    const b = el('button', '默认设置', 'secondary'); b.onclick = () => openTarget(u); row.append(text, b); $('#targets').append(row);
  }
  if (!data.users.length) $('#targets').append(el('p', '暂无接收目标，请先向 Bot 发送 /start 或添加频道 / 群聊。', 'muted'));
}
function buildOptions(container, inherited) {
  container.replaceChildren();
  for (const [key, [label, values]] of Object.entries(formats)) {
    const wrap = el('div'), caption = el('label', label), input = el('select'); input.name = key;
    if (inherited) input.append(new Option('继承接收目标', '-100'));
    values.forEach(([v, text]) => input.append(new Option(text, String(v))));
    wrap.append(caption, input); container.append(wrap);
  }
  const wrap = el('div'), input = el('input'); input.type = 'number'; input.name = 'length_limit'; input.min = inherited ? '-100' : '0'; input.max = '32767';
  wrap.append(el('label', inherited ? 'Telegraph 长度阈值（-100 继承）' : 'Telegraph 长度阈值（0 自动）'), input); container.append(wrap);
}
function openSub(sub = null) {
  const f = $('#sub-form'); f.reset(); buildOptions($('#sub-options'), true); targetOptions(f.elements.user_id);
  f.elements.id.value = sub ? sub.id : ''; $('#sub-heading').textContent = sub ? '编辑订阅' : '添加订阅';
  for (const name of ['user_id', 'url']) f.elements[name].disabled = !!sub;
  if (sub) {
    for (const key of ['title', 'tags', 'state', 'interval', ...Object.keys(formats), 'length_limit']) f.elements[key].value = sub[key] ?? '';
    f.elements.user_id.value = String(sub.user_id); f.elements.url.value = sub.feed.link;
  } else f.elements.length_limit.value = '-100';
  const r = sub?.keyword_filter || {}; f.elements.include.value = (r.include || []).join('\n'); f.elements.exclude.value = (r.exclude || []).join('\n'); f.elements.mode.value = r.mode || 'any'; f.elements.scope.value = r.scope || 'all';
  $('#sub-dialog').showModal();
}
function openTarget(user = null) {
  const f = $('#target-form'); f.reset(); f.elements.id.value = user ? user.id : '';
  $('#target-input').hidden = !!user; $('#target-defaults').hidden = !user;
  $('#target-heading').textContent = user ? `${targetLabel(user)} · 默认设置` : '添加接收目标';
  buildOptions($('#target-defaults'), false);
  const wrap = el('div'), input = el('input'); input.name = 'interval'; input.type = 'number'; input.min = '1'; input.max = '32767'; input.placeholder = '跟随全局'; wrap.append(el('label', '检查间隔（分钟）'), input); $('#target-defaults').prepend(wrap);
  if (user) for (const key of [...Object.keys(formats), 'length_limit', 'interval']) f.elements[key].value = user[key] ?? '';
  $('#target-dialog').showModal();
}
async function mutate(path, method, body) { await api(path, {method, body}); await refresh(); notice('已保存'); }
async function run(fn) { try { await fn(); } catch (e) { notice(e.message); } }
function readOptions(f) { const out = {}; for (const key of [...Object.keys(formats), 'length_limit']) out[key] = Number(f.elements[key].value); out.interval = f.elements.interval.value ? Number(f.elements.interval.value) : null; return out; }
$('#login-form').onsubmit = async e => { e.preventDefault(); token = $('#token').value.trim(); $('#login-error').textContent = ''; try { await refresh(); $('#token').value = ''; $('#login').classList.add('hidden'); $('#app').classList.remove('hidden'); } catch(err) { $('#login-error').textContent = err.message; } };
$('#logout').onclick = logout;
document.querySelectorAll('[data-page]').forEach(b => b.onclick = () => { document.querySelectorAll('main>section').forEach(s => s.hidden = s.id !== `page-${b.dataset.page}`); document.querySelectorAll('[data-page]').forEach(n => n.classList.toggle('active', n === b)); });
document.querySelectorAll('.close-dialog').forEach(b => b.onclick = () => b.closest('dialog').close());
['search', 'target-filter', 'state-filter'].forEach(id => $(`#${id}`).addEventListener('input', renderSubs));
$('#add-sub').onclick = () => openSub(); $('#add-target').onclick = () => openTarget();
$('#sub-form').onsubmit = e => { e.preventDefault(); run(async () => {
  const f = e.target, id = f.elements.id.value, out = readOptions(f);
  out.title = f.elements.title.value || null; out.tags = f.elements.tags.value || null; out.state = Number(f.elements.state.value);
  const words = key => f.elements[key].value.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  out.keyword_filter = {include: words('include'), exclude: words('exclude'), mode: f.elements.mode.value, scope: f.elements.scope.value};
  if (id) await mutate(`/api/subscriptions/${id}`, 'PATCH', out);
  else await mutate('/api/subscriptions', 'POST', {user_id: Number(f.elements.user_id.value), url: f.elements.url.value, options: out});
  $('#sub-dialog').close();
}); };
$('#target-form').onsubmit = e => { e.preventDefault(); run(async () => { const f = e.target, id = f.elements.id.value; if (id) await mutate(`/api/targets/${id}`, 'PATCH', readOptions(f)); else await mutate('/api/targets', 'POST', {target: f.elements.target.value.trim()}); $('#target-dialog').close(); }); };
$('#settings-form').onsubmit = e => { e.preventDefault(); run(async () => { const values = Object.fromEntries(new FormData(e.target)); for (const k in values) if (k !== 'sub_limit_reached_message') values[k] = Number(values[k]); await mutate('/api/options', 'PATCH', values); }); };
$('#export').onclick = () => run(async () => { const response = await api(`/api/backup?runtime=${$('#include-runtime').checked ? 1 : 0}`); const link = el('a'); const url = URL.createObjectURL(await response.blob()); link.href = url; link.download = `rsstt-backup-${new Date().toISOString().slice(0,10)}.zip`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); });
$('#backup-file').onchange = () => run(async () => { previewFile = null; $('#restore').disabled = true; $('#restore-summary').hidden = true; const file = $('#backup-file').files[0]; if (!file) return; if (file.size > 16*1024*1024) throw Error('备份文件不能超过 16 MB'); const result = await (await api('/api/restore?preview=1', {method: 'POST', body: file})).json(); previewFile = file; $('#restore-summary').textContent = `校验通过\n${result.users} 个目标 · ${result.feeds} 个 RSS 源 · ${result.subscriptions} 条订阅\n${result.runtime_included ? '含敏感运行配置' : '不含运行配置'}\n备份时间：${result.created_at || '未知'}`; $('#restore-summary').hidden = false; $('#restore').disabled = false; });
$('#restore').onclick = () => run(async () => { if (!previewFile || !confirm('确认合并还原？备份中的订阅、默认设置和全局配置将覆盖对应的当前配置。')) return; $('#restore').disabled = true; try { const r = await (await api(`/api/restore?runtime=${$('#restore-runtime').checked ? 1 : 0}`, {method: 'POST', body: previewFile, headers: {'X-Confirm-Restore': 'merge'}})).json(); await refresh(); notice(`还原完成，已保存恢复备份 ${r.recovery_backup}。${r.restart_required ? '\n运行配置将在重启 Bot 后生效。' : ''}`); previewFile = null; $('#backup-file').value = ''; } finally { $('#restore').disabled = !previewFile; } });
