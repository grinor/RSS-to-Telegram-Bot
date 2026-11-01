'use strict';
let token = '', data = null, previewFile = null, noticeTimer;
const $ = s => document.querySelector(s);
const el = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
const EN = {
  "RSS 管理台": "RSS Admin",
  "订阅管理，从这里开始。": "Your subscriptions, in one place.",
  "使用部署时设置的管理员密钥登录。": "Sign in with the admin secret configured for this instance.",
  "管理员密钥": "Admin secret",
  "进入管理台": "Sign in",
  "◉ 订阅源": "◉ Subscriptions",
  "◎ 接收目标": "◎ Destinations",
  "⚙ 全局配置": "⚙ Global settings",
  "↓ 备份与还原": "↓ Backup & restore",
  "退出登录": "Sign out",
  "订阅源": "Subscriptions",
  "管理内容、接收位置和关键词规则。": "Manage feeds and keyword rules, grouped by destination.",
  "＋ 添加订阅": "＋ Add subscription",
  "订阅总数": "Subscriptions",
  "启用订阅": "Active subscriptions",
  "接收目标": "Destinations",
  "搜索订阅": "Search subscriptions",
  "搜索名称、地址或关键词…": "Search names, URLs, or keywords…",
  "按目标筛选": "Filter by destination",
  "按状态筛选": "Filter by status",
  "所有状态": "All statuses",
  "启用中": "Active",
  "已暂停": "Paused",
  "私聊、频道与群聊；同一个 Bot 管理的所有订阅。": "Private chats, channels, and groups managed by this bot.",
  "＋ 添加目标": "＋ Add destination",
  "私聊用户需先向 Bot 发送 /start；频道与群聊需先加入 Bot，并授予发送消息所需权限。": "Private-chat users must send /start first. Add the bot to channels or groups and grant permission to send messages.",
  "全局配置": "Global settings",
  "修改后立即生效。Bot 凭据、代理与数据库连接仍由部署配置管理。": "Changes take effect immediately. Bot credentials, proxies, and database connections remain in your deployment configuration.",
  "默认检查间隔（分钟）": "Default polling interval (minutes)",
  "最小检查间隔（分钟）": "Minimum polling interval (minutes)",
  "用户订阅上限（-1 为不限）": "User subscription limit (-1 for unlimited)",
  "频道 / 群聊订阅上限": "Channel / group subscription limit",
  "达到上限时的提示": "Subscription limit message",
  "保存配置": "Save settings",
  "备份与还原": "Backup & restore",
  "将订阅和设置打包，迁移到另一个实例。": "Export subscriptions and settings, or move them to another instance.",
  "导出备份": "Export backup",
  "ZIP 包含全部接收目标、订阅、自定义设置、关键词规则、文章历史和全局配置。备份含聊天 ID 等私人信息，请妥善保管。": "The ZIP includes all destinations, subscriptions, custom settings, keyword rules, article history, and global options. Keep it private: it contains chat IDs and other personal information.",
  "同时包含 Bot Token、管理员、API 凭据、Telegraph、代理等运行配置（敏感）": "Include runtime settings: bot token, managers, API credentials, Telegraph, and proxies (sensitive)",
  "不包含 Telegram 会话、数据库连接地址及 Web 登录密钥。新环境首次启动仍需提供 Bot Token、管理员和 Web 密钥。": "Telegram sessions, database connection settings, and the web admin secret are excluded. A new instance still needs its bot token, managers, and web secret to start.",
  "下载 ZIP 备份": "Download ZIP backup",
  "合并还原": "Merge restore",
  "按聊天 ID 和 RSS 地址合并。备份中的同名订阅与目标设置会覆盖当前设置，当前额外的订阅会保留。先校验和预览，再确认执行；执行前自动保留一份恢复备份。": "Merge by chat ID and RSS URL. Matching subscriptions and destination settings are overwritten; additional current subscriptions are kept. Validate and preview before confirming. A recovery backup is saved automatically first.",
  "还原备份中的运行配置（保存后需重启 Bot）": "Restore runtime settings from the backup (requires restarting the bot)",
  "数据库连接与 Web 密钥保持当前值。运行配置还原后以 config/web-restored.env 为准。": "The database connection and web secret stay unchanged. Restored runtime settings are saved to config/web-restored.env.",
  "确认合并还原": "Confirm merge restore",
  "编辑订阅": "Edit subscription",
  "关闭": "Close",
  "RSS 地址": "RSS URL",
  "自定义标题": "Custom title",
  "留空使用源标题": "Leave empty to use the feed title",
  "标签": "Tags",
  "多个标签用空格分隔": "Separate tags with spaces",
  "状态": "Status",
  "启用": "Enable",
  "暂停": "Pause",
  "检查间隔（分钟）": "Polling interval (minutes)",
  "继承接收目标默认值": "Inherit destination default",
  "关键词过滤": "Keyword filtering",
  "每行一个关键词，不区分大小写。排除规则优先；留空即不过滤。仅影响此订阅之后的新文章。": "One keyword per line, case-insensitive. Exclusions take priority. Leave empty for no filtering. Applies only to future articles in this subscription.",
  "必须包含": "Include keywords",
  "排除关键词": "Exclude keywords",
  "包含条件": "Include matching",
  "任意一个匹配即可": "Match any keyword",
  "全部关键词都要匹配": "Match every keyword",
  "匹配范围": "Search in",
  "标题与正文": "Title and body",
  "仅标题": "Title only",
  "消息格式设置": "Message formatting",
  "取消": "Cancel",
  "保存订阅": "Save subscription",
  "频道用户名 / 聊天 ID": "Channel username / chat ID",
  "@channel 或 -1001234567890": "@channel or -1001234567890",
  "保存目标": "Save destination",
  "科技\n开源": "Technology\nOpen source",
  "广告\n推广": "Advertising\nPromotion",
  "通知": "Notifications",
  "开启": "On",
  "静音": "Silent",
  "发送方式": "Delivery mode",
  "自动": "Automatic",
  "链接": "Link",
  "Telegram 消息": "Telegram message",
  "链接预览": "Link preview",
  "作者": "Author",
  "显示": "Show",
  "隐藏": "Hide",
  "来源": "Source",
  "仅链接": "Link only",
  "标题": "Title",
  "文章标签": "Article tags",
  "排版风格": "Formatting style",
  "媒体": "Media",
  "禁用": "Disable",
  "所有接收目标": "All destinations",
  "频道": "Channel",
  "群聊": "Group",
  "群组": "Group",
  "私聊": "Private chat",
  "当前 Bot": "Current bot",
  "未命名订阅": "Untitled subscription",
  "编辑": "Edit",
  "删除": "Delete",
  "默认设置": "Default settings",
  "已保存": "Saved",
  "添加订阅": "Add subscription",
  "添加接收目标": "Add destination",
  "继承接收目标": "Inherit destination",
  "Telegraph 长度阈值（-100 继承）": "Telegraph length threshold (-100 to inherit)",
  "Telegraph 长度阈值（0 自动）": "Telegraph length threshold (0 for automatic)",
  "跟随全局": "Use global default",
  "已封禁": "Banned",
  "没有符合条件的订阅。可以添加 RSS 地址开始使用。": "No matching subscriptions. Add an RSS URL to get started.",
  "暂无接收目标，请先向 Bot 发送 /start 或添加频道 / 群聊。": "No destinations yet. Send /start to the bot, or add a channel or group.",
  "源已停用，请暂停后重新启用以重试": "Feed deactivated. Pause and enable it again to retry.",
  "包含 {include} · 排除 {exclude}": "Include {include} · Exclude {exclude}",
  "抓取失败 {count} 次": "{count} fetch failures",
  "{count} 条订阅 · {active} 条启用": "Subscriptions: {count} · Active: {active}",
  "{count} 条订阅 · 默认间隔 {interval}{banned}": "Subscriptions: {count} · Default interval: {interval}{banned}",
  "{count} 分钟": "{count} min",
  " · 已封禁": " · Banned",
  "删除「{title}」的此条订阅？": "Delete this subscription to “{title}”?",
  "请求失败 ({status})": "Request failed ({status})",
  "备份文件不能超过 16 MB": "The backup cannot exceed 16 MB.",
  "校验通过": "Validation passed",
  "{users} 个目标 · {feeds} 个 RSS 源 · {subscriptions} 条订阅": "{users} destinations · {feeds} feeds · {subscriptions} subscriptions",
  "含敏感运行配置": "Includes sensitive runtime settings",
  "不含运行配置": "No runtime settings included",
  "备份时间：{time}": "Backup created: {time}",
  "未知": "Unknown",
  "确认合并还原？备份中的订阅、默认设置和全局配置将覆盖对应的当前配置。": "Confirm merge restore? Subscriptions, defaults, and global options in the backup will overwrite the matching current settings.",
  "还原完成，已保存恢复备份 {file}。": "Restore complete. Recovery backup saved as {file}.",
  "运行配置将在重启 Bot 后生效。": "Runtime settings will take effect after restarting the bot.",
  "语言": "Language",
  "切换为深色": "Switch to dark",
  "切换为浅色": "Switch to light",
  "按接收目标分组；点击分组标题可折叠。": "Grouped by destination. Click a group heading to collapse it.",
  "选择备份文件": "Choose a backup file",
  "需要管理员登录": "Please sign in with the admin secret.",
  "请求来源无效": "Invalid request origin.",
  "需要 JSON 请求": "A JSON request is required.",
  "请求必须是 JSON 对象": "The request must be a JSON object.",
  "记录不存在": "Record not found.",
  "记录已存在或关联关系无效": "The record already exists or has invalid references.",
  "请输入频道用户名或聊天 ID": "Enter a channel username or chat ID.",
  "请先在 Telegram 中向 Bot 发送 /start": "Send /start to the bot in Telegram first.",
  "无法访问目标，请先把 Bot 加入频道/群聊并赋予发送权限": "Cannot access this destination. Add the bot to the channel/group and grant permission to send messages.",
  "添加失败，请检查 RSS 地址": "Could not add the feed. Check its RSS URL.",
  "请先预览并确认合并还原": "Preview the backup and confirm the merge restore first.",
  "过滤规则格式错误": "Invalid keyword rule format.",
  "过滤模式或范围无效": "Invalid keyword mode or search scope.",
  "每组关键词最多 100 个": "Each keyword list allows at most 100 keywords.",
  "关键词不能为空，且最多 200 个字符": "Keywords must be nonempty and at most 200 characters long.",
  "备份文件超过 16 MB": "The backup exceeds 16 MB.",
  "解压后备份超过限制": "The uncompressed backup exceeds the size limit.",
  "缺少唯一的 backup.json": "The archive must contain exactly one backup.json.",
  "不是有效的 RSStT 备份 ZIP 文件": "This is not a valid RSStT backup ZIP.",
  "备份格式或版本不受支持": "Unsupported backup format or version.",
  "备份记录格式无效或过多": "Invalid backup records or too many records.",
  "用户记录无效": "Invalid destination record.",
  "用户 ID 无效或重复": "Invalid or duplicate chat ID.",
  "用户状态无效": "Invalid destination status.",
  "语言字段无效": "Invalid language field.",
  "订阅源记录无效": "Invalid feed record.",
  "订阅源 ID 或地址重复": "Duplicate feed ID or URL.",
  "源标题无效": "Invalid feed title.",
  "文章历史记录无效": "Invalid article history.",
  "订阅记录无效": "Invalid subscription record.",
  "订阅关联的目标或源不存在": "A subscription refers to a missing destination or feed.",
  "重复的订阅记录": "Duplicate subscription record.",
  "运行配置无效": "Invalid runtime settings.",
  "订阅地址无效": "Invalid feed URL.",
  "订阅地址必须是 HTTP 或 HTTPS 链接，且不能包含登录凭据": "Feed URLs must use HTTP or HTTPS and contain no login credentials.",
  "包含不支持的配置字段": "Unsupported settings field.",
  "标题或标签过长": "The title or tags are too long.",
  "长度限制无效": "Invalid length threshold.",
  "全局配置字段无效": "Invalid global setting.",
  "订阅限制提示最多 4096 个字符": "The subscription limit message allows at most 4096 characters."
};

function preference(key, fallback) { try { return localStorage.getItem(key) || fallback; } catch { return fallback; } }
let language = preference('rsstt-language', navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en');
if (!['zh', 'en'].includes(language)) language = 'zh';
let theme = preference('rsstt-theme', window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
if (!['light', 'dark'].includes(theme)) theme = 'light';
const collapsedGroups = new Set();
let previewSummary = null;
function t(key, values = {}) {
  const text = language === 'en' ? (EN[key] || key) : key;
  return text.replace(/\{(\w+)\}/g, (match, name) => values[name] === undefined ? match : String(values[name]));
}
function remember(key, value) { try { localStorage.setItem(key, value); } catch { /* Preferences remain usable without storage. */ } }
function translateError(message) {
  if (language !== 'en') return message;
  if (EN[message]) return EN[message];
  const range = message.match(/^数值必须是 (-?\d+) 到 (-?\d+) 之间的整数$/);
  if (range) return `Enter an integer between ${range[1]} and ${range[2]}.`;
  if (message.endsWith(' 的选项无效')) return `Invalid option: ${message.split(' ')[0]}`;
  return message;
}
function applyTheme() {
  document.documentElement.dataset.theme = theme;
  const button = $('#theme-toggle');
  button.textContent = t(theme === 'dark' ? '切换为浅色' : '切换为深色');
  button.setAttribute('aria-pressed', String(theme === 'dark'));
}
function renderPreview() {
  if (!previewSummary) return;
  const r = previewSummary;
  $('#restore-summary').textContent = [t('校验通过'), t('{users} 个目标 · {feeds} 个 RSS 源 · {subscriptions} 条订阅', r),
    t(r.runtime_included ? '含敏感运行配置' : '不含运行配置'), t('备份时间：{time}', {time: r.created_at || t('未知')})].join('\n');
}
function applyLanguage() {
  document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
  $('#language').value = language;
  document.querySelectorAll('[data-i18n]').forEach(n => { n.textContent = t(n.dataset.i18n); });
  for (const attr of ['placeholder', 'aria-label']) {
    document.querySelectorAll(`[data-i18n-${attr}]`).forEach(n => n.setAttribute(attr, t(n.getAttribute(`data-i18n-${attr}`))));
  }
  applyTheme();
  if (data) {
    const selected = $('#target-filter').value;
    targetOptions($('#target-filter'), true); $('#target-filter').value = selected;
    const f = $('#sub-form'), selectedSubTarget = f.elements.user_id.value;
    targetOptions(f.elements.user_id); f.elements.user_id.value = selectedSubTarget;
    buildOptions($('#sub-options'), true);
    // Destination defaults may contain unsaved edits, including the polling interval.
    const targetContainer = $('#target-defaults');
    const intervalWrap = targetContainer.querySelector('[name="interval"]')?.parentElement;
    if (intervalWrap) intervalWrap.remove();
    buildOptions(targetContainer, false);
    if (intervalWrap) {
      intervalWrap.querySelector('label').textContent = t('检查间隔（分钟）');
      intervalWrap.querySelector('input').placeholder = t('跟随全局');
      targetContainer.prepend(intervalWrap);
    }
    $('#sub-heading').textContent = t(f.elements.id.value ? '编辑订阅' : '添加订阅');
    const targetUser = data.users.find(u => String(u.id) === $('#target-form').elements.id.value);
    $('#target-heading').textContent = targetUser ? `${targetLabel(targetUser)} · ${t('默认设置')}` : t('添加接收目标');
    renderSubs(); renderTargets();
  }
  renderPreview();
}
const formats = () => ({
  notify: [t('通知'), [[1, t('开启')], [0, t('静音')]]],
  send_mode: [t('发送方式'), [[0, t('自动')], [-1, t('链接')], [1, 'Telegraph'], [2, t('Telegram 消息')]]],
  link_preview: [t('链接预览'), [[0, t('自动')], [1, t('启用')]]],
  display_author: [t('作者'), [[0, t('自动')], [1, t('显示')], [-1, t('隐藏')]]],
  display_via: [t('来源'), [[0, t('自动')], [1, t('显示')], [-1, t('仅链接')], [-2, t('隐藏')]]],
  display_title: [t('标题'), [[0, t('自动')], [1, t('显示')], [-1, t('隐藏')]]],
  display_entry_tags: [t('文章标签'), [[0, t('自动')], [1, t('显示')], [-1, t('隐藏')]]],
  style: [t('排版风格'), [[0, 'RSStT'], [1, 'flowerss']]],
  display_media: [t('媒体'), [[0, t('启用')], [-1, t('禁用')]]]
});
function notice(message) { $('#notice').textContent = message; $('#notice').hidden = false; clearTimeout(noticeTimer); noticeTimer = setTimeout(() => $('#notice').hidden = true, 7000); }
async function api(path, {method = 'GET', body, headers = {}} = {}) {
  const opts = {method, headers: {...headers, Authorization: `Bearer ${token}`}};
  if (body !== undefined) { opts.body = body instanceof File ? body : JSON.stringify(body); if (!(body instanceof File)) opts.headers['Content-Type'] = 'application/json'; }
  const res = await fetch(path, opts);
  if (!res.ok) { const info = await res.json().catch(() => ({})); if (res.status === 401) logout(); throw new Error(info.error ? translateError(info.error) : t('请求失败 ({status})', {status: res.status})); }
  return res;
}
function logout() { token = ''; data = null; $('#app').classList.add('hidden'); $('#login').classList.remove('hidden'); $('#token').value = ''; document.querySelectorAll('dialog[open]').forEach(d => d.close()); }
const kind = u => u.state === 50 ? t('频道') : u.state === 51 ? t('群聊') : u.id < 0 ? t('群组') : t('私聊');
const targetLabel = u => `${kind(u)} · ${u.id}`;
function targetOptions(select, all = false) { select.replaceChildren(); if (all) select.append(new Option(t('所有接收目标'), '')); data.users.forEach(u => select.append(new Option(targetLabel(u), String(u.id)))); }
async function refresh() {
  const selected = $('#target-filter').value;
  data = await (await api('/api/state')).json();
  $('#bot-name').textContent = data.bot.username ? `@${data.bot.username}` : t('当前 Bot');
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
  const groups = new Map();
  for (const sub of subs) {
    if (!groups.has(sub.user_id)) groups.set(sub.user_id, []);
    groups.get(sub.user_id).push(sub);
  }
  for (const [uid, subscriptions] of groups) {
    const group = el('details', undefined, 'destination-group');
    group.dataset.userId = String(uid);
    group.open = !!term || !!target || !collapsedGroups.has(String(uid));
    const heading = el('summary'), u = data.users.find(u => u.id === uid);
    heading.append(el('strong', u ? targetLabel(u) : String(uid)), el('span',
      t('{count} 条订阅 · {active} 条启用', {count: subscriptions.length, active: subscriptions.filter(s => s.state === 1).length}), 'group-count'));
    group.append(heading);
    group.addEventListener('toggle', () => {
      if (group.isConnected && !term && !target) {
        if (group.open) collapsedGroups.delete(String(uid)); else collapsedGroups.add(String(uid));
      }
    });
    for (const s of subscriptions) {
      const card = el('div', undefined, 'card subscription'), content = el('div');
      content.append(el('h3', s.title || s.feed.title || t('未命名订阅')), el('div', s.feed.link, 'url'));
      const u = data.users.find(u => u.id === s.user_id);
      content.append(el('span', u ? targetLabel(u) : s.user_id, 'pill'), el('span', s.state ? t('启用中') : t('已暂停'), `pill ${s.state ? '' : 'off'}`));
      const r = s.keyword_filter;
      if (r && (r.include.length || r.exclude.length)) content.append(el('span', t('包含 {include} · 排除 {exclude}', {include: r.include.length, exclude: r.exclude.length}), 'pill'));
      if (s.feed.error_count) content.append(el('span', t('抓取失败 {count} 次', {count: s.feed.error_count}), 'pill off'));
      if (s.state && !s.feed.state) content.append(el('span', t('源已停用，请暂停后重新启用以重试'), 'pill off'));
      const actions = el('div', undefined, 'actions');
      for (const [name, action, cls] of [[t('编辑'), () => openSub(s), 'secondary'], [s.state ? t('暂停') : t('启用'), () => mutate(`/api/subscriptions/${s.id}`, 'PATCH', {state: s.state ? 0 : 1}), 'secondary'], [t('删除'), async () => { if (confirm(t('删除「{title}」的此条订阅？', {title: s.title || s.feed.title}))) await mutate(`/api/subscriptions/${s.id}`, 'DELETE'); }, 'danger']]) {
        const b = el('button', name, cls); b.onclick = () => run(action); actions.append(b);
      }
      card.append(content, actions); group.append(card);
    }
    root.append(group);
  }
  if (!subs.length) root.append(el('div', t('没有符合条件的订阅。可以添加 RSS 地址开始使用。'), 'card empty'));
}
function renderTargets() {
  $('#targets').replaceChildren();
  for (const u of data.users) {
    const row = el('div', undefined, 'row target-row'), text = el('div');
    text.append(el('strong', targetLabel(u)), el('div', t('{count} 条订阅 · 默认间隔 {interval}{banned}', {count: data.subscriptions.filter(s => s.user_id === u.id).length, interval: u.interval ? t('{count} 分钟', {count: u.interval}) : t('跟随全局'), banned: u.state === -1 ? t(' · 已封禁') : ''}), 'muted'));
    const b = el('button', t('默认设置'), 'secondary'); b.onclick = () => openTarget(u); row.append(text, b); $('#targets').append(row);
  }
  if (!data.users.length) $('#targets').append(el('p', t('暂无接收目标，请先向 Bot 发送 /start 或添加频道 / 群聊。'), 'muted'));
}
function buildOptions(container, inherited) {
  const previous = Object.fromEntries([...container.querySelectorAll('[name]')].map(n => [n.name, n.value]));
  container.replaceChildren();
  for (const [key, [label, values]] of Object.entries(formats())) {
    const wrap = el('div'), caption = el('label', label), input = el('select'); input.name = key;
    if (inherited) input.append(new Option(t('继承接收目标'), '-100'));
    values.forEach(([v, text]) => input.append(new Option(text, String(v))));
    wrap.append(caption, input); container.append(wrap);
  }
  const wrap = el('div'), input = el('input'); input.type = 'number'; input.name = 'length_limit'; input.min = inherited ? '-100' : '0'; input.max = '32767';
  wrap.append(el('label', inherited ? t('Telegraph 长度阈值（-100 继承）') : t('Telegraph 长度阈值（0 自动）')), input); container.append(wrap);
  for (const [name, value] of Object.entries(previous)) { const field = container.querySelector(`[name="${name}"]`); if (field) field.value = value; }
}
function openSub(sub = null, selectedTarget = $('#target-filter').value) {
  const f = $('#sub-form'); f.reset(); buildOptions($('#sub-options'), true); targetOptions(f.elements.user_id);
  f.elements.id.value = sub ? sub.id : ''; $('#sub-heading').textContent = sub ? t('编辑订阅') : t('添加订阅');
  for (const name of ['user_id', 'url']) f.elements[name].disabled = !!sub;
  if (sub) {
    for (const key of ['title', 'tags', 'state', 'interval', ...Object.keys(formats()), 'length_limit']) f.elements[key].value = sub[key] ?? '';
    f.elements.user_id.value = String(sub.user_id); f.elements.url.value = sub.feed.link;
  } else { f.elements.length_limit.value = '-100'; if (selectedTarget) f.elements.user_id.value = selectedTarget; }
  const r = sub?.keyword_filter || {}; f.elements.include.value = (r.include || []).join('\n'); f.elements.exclude.value = (r.exclude || []).join('\n'); f.elements.mode.value = r.mode || 'any'; f.elements.scope.value = r.scope || 'all';
  $('#sub-dialog').showModal();
}
function openTarget(user = null) {
  const f = $('#target-form'); f.reset(); f.elements.id.value = user ? user.id : '';
  $('#target-input').hidden = !!user; $('#target-defaults').hidden = !user;
  $('#target-heading').textContent = user ? `${targetLabel(user)} · ${t('默认设置')}` : t('添加接收目标');
  buildOptions($('#target-defaults'), false);
  const wrap = el('div'), input = el('input'); input.name = 'interval'; input.type = 'number'; input.min = '1'; input.max = '32767'; input.placeholder = t('跟随全局'); wrap.append(el('label', t('检查间隔（分钟）')), input); $('#target-defaults').prepend(wrap);
  if (user) for (const key of [...Object.keys(formats()), 'length_limit', 'interval']) f.elements[key].value = user[key] ?? '';
  $('#target-dialog').showModal();
}
async function mutate(path, method, body) { await api(path, {method, body}); await refresh(); notice(t('已保存')); }
async function run(fn) { try { await fn(); } catch (e) { notice(e.message); } }
function readOptions(f) { const out = {}; for (const key of [...Object.keys(formats()), 'length_limit']) out[key] = Number(f.elements[key].value); out.interval = f.elements.interval.value ? Number(f.elements.interval.value) : null; return out; }
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
$('#backup-file').onchange = () => run(async () => { previewFile = null; previewSummary = null; $('#restore').disabled = true; $('#restore-summary').hidden = true; const file = $('#backup-file').files[0]; if (!file) return; if (file.size > 16*1024*1024) throw Error(t('备份文件不能超过 16 MB')); const result = await (await api('/api/restore?preview=1', {method: 'POST', body: file})).json(); previewFile = file; previewSummary = result; renderPreview(); $('#restore-summary').hidden = false; $('#restore').disabled = false; });
$('#restore').onclick = () => run(async () => { if (!previewFile || !confirm(t('确认合并还原？备份中的订阅、默认设置和全局配置将覆盖对应的当前配置。'))) return; $('#restore').disabled = true; try { const r = await (await api(`/api/restore?runtime=${$('#restore-runtime').checked ? 1 : 0}`, {method: 'POST', body: previewFile, headers: {'X-Confirm-Restore': 'merge'}})).json(); await refresh(); notice(t('还原完成，已保存恢复备份 {file}。', {file: r.recovery_backup}) + (r.restart_required ? '\n' + t('运行配置将在重启 Bot 后生效。') : '')); previewFile = null; $('#backup-file').value = ''; } finally { $('#restore').disabled = !previewFile; } });

$('#language').onchange = e => { language = e.target.value; remember('rsstt-language', language); applyLanguage(); };
$('#theme-toggle').onclick = () => { theme = theme === 'dark' ? 'light' : 'dark'; remember('rsstt-theme', theme); applyTheme(); };
applyLanguage();
