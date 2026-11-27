/* PAS 全站公共增强能力库：Ctrl+K 命令面板、单设备 360° 抽屉、断面 Diff、交互式趋势图、SSE 轮询器与三语补强 */
(() => {
  'use strict';

  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  const num = (v, d = 2) => (v == null || Number.isNaN(Number(v)) ? '—' : Number(v).toFixed(d));

  const PAGES = [
    { path: '/overview.html', title: '总览 · SE→LF→CA 联动态势', en: 'Overview Pipeline', ru: 'Обзор конвейера', cat: '页面' },
    { path: '/se-main.html', title: '状态估计 SE · 主画面', en: 'SE Dashboard', ru: 'SE Главная', cat: '页面' },
    { path: '/se-flow.html', title: '状态估计 SE · 接线图', en: 'SE Diagram', ru: 'SE Схема', cat: '页面' },
    { path: '/se-measurements.html', title: '状态估计 SE · 量测与估计明细', en: 'SE Measurements', ru: 'SE Измерения', cat: '页面' },
    { path: '/se-bad.html', title: '状态估计 SE · 坏数据辨识', en: 'SE Bad Data', ru: 'SE Плохие данные', cat: '页面' },
    { path: '/se-prefilter.html', title: '状态估计 SE · 前置过滤规则', en: 'SE Prefilter', ru: 'SE Предфильтр', cat: '页面' },
    { path: '/se-pseudo.html', title: '状态估计 SE · 伪量测配置', en: 'SE Pseudo', ru: 'SE Псевдо', cat: '页面' },
    { path: '/se-curves.html', title: '状态估计 SE · 历史曲线', en: 'SE Curves', ru: 'SE Кривые', cat: '页面' },
    { path: '/se-params.html', title: '状态估计 SE · 算法参数', en: 'SE Parameters', ru: 'SE Параметры', cat: '页面' },
    { path: '/se-logs.html', title: '状态估计 SE · 运行日志', en: 'SE Logs', ru: 'SE Журнал', cat: '页面' },
    { path: '/lf-main.html', title: '潮流分析 LF · 主画面', en: 'LF Dashboard', ru: 'LF Главная', cat: '页面' },
    { path: '/lf-flow.html', title: '潮流分析 LF · 在线潮流图', en: 'LF Flow Diagram', ru: 'LF Схема потоков', cat: '页面' },
    { path: '/lf-results.html', title: '潮流分析 LF · 潮流明细', en: 'LF Results', ru: 'LF Результаты', cat: '页面' },
    { path: '/lf-params.html', title: '潮流分析 LF · 参数与方式', en: 'LF Parameters', ru: 'LF Параметры', cat: '页面' },
    { path: '/lf-logs.html', title: '潮流分析 LF · 运行日志', en: 'LF Logs', ru: 'LF Журнал', cat: '页面' },
    { path: '/ca-main.html', title: '静态安全 CA · 主画面', en: 'CA Dashboard', ru: 'CA Главная', cat: '页面' },
    { path: '/ca-risks.html', title: '静态安全 CA · 风险与图谱', en: 'CA Risks & Graph', ru: 'CA Риски и схема', cat: '页面' },
    { path: '/ca-contingencies.html', title: '静态安全 CA · 预想故障集', en: 'CA Contingencies', ru: 'CA Возмущения', cat: '页面' },
    { path: '/ca-config.html', title: '静态安全 CA · 参数与限值', en: 'CA Config', ru: 'CA Настройки', cat: '页面' },
    { path: '/ca-logs.html', title: '静态安全 CA · 运行日志', en: 'CA Logs', ru: 'CA Журнал', cat: '页面' },
    { path: '/runs.html', title: '运行管理 · 运行历史', en: 'Run History', ru: 'История запусков', cat: '运行管理' },
    { path: '/measurements.html', title: '运行管理 · 设备量测', en: 'Device Measurements', ru: 'Измерения устройств', cat: '运行管理' },
    { path: '/limits.html', title: '运行管理 · 安全限值', en: 'Security Limits', ru: 'Пределы безопасности', cat: '运行管理' },
    { path: '/workspace.html', title: '运行管理 · 工作目录与数据源体检', en: 'Workspace & Health', ru: 'Рабочий каталог', cat: '运行管理' },
    { path: '/settings.html', title: '运行管理 · 系统设置', en: 'System Settings', ru: 'Настройки системы', cat: '运行管理' },
  ];

  /* ==================== 1. 三语通用补强词典（覆盖旧管理 5 页与侧栏） ==================== */
  const LEGACY_DICT = {
    'en-US': {
      '在线分析平台': 'Online Analysis',
      '总览': 'Overview',
      '分析功能': 'Analysis',
      '状态估计 SE': 'State Estimation SE',
      '潮流分析 LF': 'Load Flow LF',
      '静态安全 CA': 'Security CA',
      '运行管理': 'Operations',
      '运行历史': 'Run History',
      '设备量测': 'Measurements',
      '安全限值': 'Security Limits',
      '工作目录': 'Workspace',
      '系统设置': 'Settings',
      '刷新': 'Refresh',
      '立即执行全部': 'Run All',
      '周期调度运行中': 'Daemon Running',
      '周期运行中': 'Daemon Running',
      '服务检查中': 'Checking...',
      '断面对比': 'Snapshot Diff',
      '导出报告': 'Export Report',
      '快速搜索': 'Search',
    },
    'ru-RU': {
      '在线分析平台': 'Онлайн-анализ',
      '总览': 'Обзор',
      '分析功能': 'Анализ',
      '状态估计 SE': 'Оценка сост. SE',
      '潮流分析 LF': 'Потоки LF',
      '静态安全 CA': 'Надежность CA',
      '运行管理': 'Управление',
      '运行历史': 'История',
      '设备量测': 'Измерения',
      '安全限值': 'Пределы',
      '工作目录': 'Каталог',
      '系统设置': 'Настройки',
      '刷新': 'Обновить',
      '立即执行全部': 'Запустить все',
      '周期调度运行中': 'Планировщик активен',
      '周期运行中': 'Планировщик активен',
      '服务检查中': 'Проверка...',
      '断面对比': 'Сравнение',
      '导出报告': 'Отчет',
      '快速搜索': 'Поиск',
    },
  };

  function getLang() {
    const l = localStorage.getItem('pas_se_lang') || localStorage.getItem('se_lang') || document.documentElement.lang || 'zh-CN';
    return ['zh-CN', 'en-US', 'ru-RU'].includes(l) ? l : 'zh-CN';
  }

  function applyLegacyI18n(lang) {
    const cur = lang || getLang();
    document.documentElement.lang = cur;
    // 仅对未带 data-i18n 的旧页面侧栏、顶栏标题与按钮做无侵入双语/三语映射
    const dict = LEGACY_DICT[cur] || null;
    document.querySelectorAll('.sidebar a, .sidebar .nav-group > span, .sidebar .brand small, .topbar h1, .top-actions button').forEach((el) => {
      if (el.hasAttribute('data-i18n') || el.children.length > 0) return;
      if (!el.dataset.pasZhOrig) {
        const txt = (el.textContent || '').trim();
        if (txt) el.dataset.pasZhOrig = txt;
      }
      const orig = el.dataset.pasZhOrig;
      if (!orig) return;
      if (cur === 'zh-CN') {
        el.textContent = orig;
      } else if (dict && dict[orig]) {
        el.textContent = dict[orig];
      }
    });
  }

  /* ==================== 2. SSE 订阅 + 后台标签自动暂停轮询器 ==================== */
  let _sse = null;
  const _sseListeners = new Set();

  function ensureSSE() {
    if (_sse || typeof EventSource === 'undefined') return;
    try {
      _sse = new EventSource('/api/events');
      _sse.addEventListener('update', (ev) => {
        if (document.hidden) return;
        let payload = null;
        try { payload = JSON.parse(ev.data); } catch { /* ignore */ }
        _sseListeners.forEach((fn) => {
          try { fn(payload); } catch { /* ignore */ }
        });
      });
      _sse.onerror = () => {
        // 浏览器自动重连，静默忽略
      };
    } catch {
      /* fallback to polling */
    }
  }

  function createPoller(callback, intervalMs = 10000, { useSSE = true } = {}) {
    let timer = null;
    let lastRunAt = Date.now();
    const trigger = () => {
      if (document.hidden) return;
      lastRunAt = Date.now();
      try { callback(); } catch { /* ignore */ }
    };
    const start = () => {
      stop();
      timer = setInterval(trigger, intervalMs);
    };
    const stop = () => {
      if (timer) { clearInterval(timer); timer = null; }
    };
    const onVis = () => {
      if (document.hidden) {
        stop();
      } else {
        if (Date.now() - lastRunAt >= Math.min(intervalMs, 3000)) trigger();
        start();
      }
    };
    document.addEventListener('visibilitychange', onVis);
    let sseCb = null;
    if (useSSE) {
      ensureSSE();
      sseCb = () => {
        // 节流：避免 SSE 首次连接重复触发
        if (Date.now() - lastRunAt >= 1200) trigger();
      };
      _sseListeners.add(sseCb);
    }
    start();
    return {
      stop() {
        stop();
        document.removeEventListener('visibilitychange', onVis);
        if (sseCb) _sseListeners.delete(sseCb);
      },
      trigger,
    };
  }

  /* ==================== 3. 统一交互式趋势图（渐变面积 + 阈值线 + 悬停十字准星 Tooltip） ==================== */
  let _tipEl = null;
  function getTipEl() {
    if (!_tipEl) {
      _tipEl = document.createElement('div');
      _tipEl.className = 'pas-chart-tip';
      _tipEl.hidden = true;
      document.body.appendChild(_tipEl);
    }
    return _tipEl;
  }

  function renderTrendChart(svg, {
    points = [],
    unit = '',
    color = 'var(--accent)',
    digits = 2,
    yMinForce = null,
    yMaxForce = null,
    threshold = null,
    thresholdLabel = '',
    emptyText = '暂无趋势数据',
  } = {}) {
    if (!svg) return;
    if (!points.length) {
      svg.innerHTML = `<text x="50%" y="50%" text-anchor="middle" fill="var(--text-muted)" font-size="12">${esc(emptyText)}</text>`;
      return;
    }
    const vb = (svg.getAttribute('viewBox') || '0 0 680 150').split(/\s+/).map(Number);
    const W = vb[2] || 680;
    const H = vb[3] || 150;
    const pad = { l: 46, r: 16, t: 16, b: 24 };
    const vals = points.map((p) => Number(p.y)).filter((v) => Number.isFinite(v));
    if (!vals.length) {
      svg.innerHTML = `<text x="50%" y="50%" text-anchor="middle" fill="var(--text-muted)" font-size="12">${esc(emptyText)}</text>`;
      return;
    }
    let minY = yMinForce != null ? yMinForce : Math.min(...vals);
    let maxY = yMaxForce != null ? yMaxForce : Math.max(...vals);
    if (threshold != null && Number.isFinite(threshold)) {
      minY = Math.min(minY, threshold);
      maxY = Math.max(maxY, threshold);
    }
    if (maxY - minY < 1e-6) {
      minY -= 1;
      maxY += 1;
    } else if (yMinForce == null && yMaxForce == null) {
      const m = (maxY - minY) * 0.12;
      minY -= m;
      maxY += m;
    }
    const xPos = (i) => pad.l + (points.length === 1 ? (W - pad.l - pad.r) / 2 : (i / (points.length - 1)) * (W - pad.l - pad.r));
    const yPos = (v) => pad.t + (1 - (v - minY) / (maxY - minY)) * (H - pad.t - pad.b);

    const coords = points.map((p, i) => ({ x: xPos(i), y: yPos(Number(p.y)), raw: p }));
    const linePts = coords.map((c) => `${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ');
    const areaPts = `${coords[0].x.toFixed(1)},${(H - pad.b).toFixed(1)} ${linePts} ${coords[coords.length - 1].x.toFixed(1)},${(H - pad.b).toFixed(1)}`;
    const gradId = `pasGrad_${Math.random().toString(36).slice(2, 8)}`;

    const gridLines = [0, 0.5, 1].map((frac) => {
      const gy = pad.t + frac * (H - pad.t - pad.b);
      const gv = maxY - frac * (maxY - minY);
      return `<line x1="${pad.l}" y1="${gy.toFixed(1)}" x2="${W - pad.r}" y2="${gy.toFixed(1)}" stroke="var(--border-color)" stroke-dasharray="3 3"/>` +
             `<text x="${pad.l - 6}" y="${(gy + 3).toFixed(1)}" text-anchor="end" fill="var(--text-muted)" font-size="10">${gv.toFixed(digits)}</text>`;
    }).join('');

    let thrSvg = '';
    if (threshold != null && Number.isFinite(threshold)) {
      const ty = yPos(threshold);
      thrSvg = `<line x1="${pad.l}" y1="${ty.toFixed(1)}" x2="${W - pad.r}" y2="${ty.toFixed(1)}" stroke="var(--sem-warn)" stroke-width="1.2" stroke-dasharray="5 3"/>` +
        (thresholdLabel ? `<text x="${W - pad.r - 4}" y="${(ty - 4).toFixed(1)}" text-anchor="end" fill="var(--sem-warn)" font-size="10">${esc(thresholdLabel)}</text>` : '');
    }

    const firstLbl = coords[0].raw.xLabel || '';
    const lastLbl = coords[coords.length - 1].raw.xLabel || '';
    const dots = coords.length <= 40
      ? coords.map((c) => `<circle cx="${c.x.toFixed(1)}" cy="${c.y.toFixed(1)}" r="2.6" fill="${color}"/>`).join('')
      : '';

    svg.innerHTML = `
      <defs>
        <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${color}" stop-opacity="0.28"/>
          <stop offset="100%" stop-color="${color}" stop-opacity="0.01"/>
        </linearGradient>
      </defs>
      ${gridLines}
      ${thrSvg}
      <polygon points="${areaPts}" fill="url(#${gradId})"/>
      <polyline fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" points="${linePts}"/>
      ${dots}
      <line class="pas-cross-x" x1="0" y1="${pad.t}" x2="0" y2="${H - pad.b}" stroke="var(--text-muted)" stroke-dasharray="2 2" style="display:none"/>
      <circle class="pas-cross-dot" cx="0" cy="0" r="4.5" fill="${color}" stroke="var(--bg-surface)" stroke-width="2" style="display:none"/>
      <text x="${pad.l}" y="${H - 6}" fill="var(--text-muted)" font-size="10">${esc(firstLbl)}</text>
      <text x="${W - pad.r}" y="${H - 6}" text-anchor="end" fill="var(--text-muted)" font-size="10">${esc(lastLbl)}</text>
      ${unit ? `<text x="${pad.l + 4}" y="${pad.t - 4}" fill="var(--text-muted)" font-size="10">${esc(unit)}</text>` : ''}
      <rect class="pas-hit" x="${pad.l}" y="${pad.t}" width="${W - pad.l - pad.r}" height="${H - pad.t - pad.b}" fill="transparent" style="cursor:crosshair"/>
    `;

    const hit = svg.querySelector('.pas-hit');
    const crossX = svg.querySelector('.pas-cross-x');
    const crossDot = svg.querySelector('.pas-cross-dot');
    const tip = getTipEl();
    if (hit) {
      hit.addEventListener('mousemove', (ev) => {
        const rect = svg.getBoundingClientRect();
        const relX = ((ev.clientX - rect.left) / Math.max(rect.width, 1)) * W;
        let best = coords[0];
        let bestDist = Infinity;
        for (const c of coords) {
          const d = Math.abs(c.x - relX);
          if (d < bestDist) { bestDist = d; best = c; }
        }
        crossX.setAttribute('x1', best.x.toFixed(1));
        crossX.setAttribute('x2', best.x.toFixed(1));
        crossX.style.display = '';
        crossDot.setAttribute('cx', best.x.toFixed(1));
        crossDot.setAttribute('cy', best.y.toFixed(1));
        crossDot.style.display = '';
        const extra = best.raw.extra ? `<div style="color:var(--text-muted)">${esc(best.raw.extra)}</div>` : '';
        tip.innerHTML = `<div><strong>${esc(best.raw.xLabel || '')}</strong></div><div>${Number(best.raw.y).toFixed(digits)} ${esc(unit)}</div>${extra}`;
        tip.hidden = false;
        const tx = Math.min(window.innerWidth - tip.offsetWidth - 12, ev.clientX + 14);
        const ty = Math.max(8, ev.clientY - tip.offsetHeight - 10);
        tip.style.left = `${tx}px`;
        tip.style.top = `${ty}px`;
      });
      hit.addEventListener('mouseleave', () => {
        crossX.style.display = 'none';
        crossDot.style.display = 'none';
        tip.hidden = true;
      });
    }
  }

  /* ==================== 4. 单设备 360° 全景右侧抽屉 ==================== */
  let _activeOverlay = null;
  function closeOverlay() {
    if (_activeOverlay) {
      _activeOverlay.remove();
      _activeOverlay = null;
    }
  }

  async function openDeviceDrawer(deviceName) {
    const name = String(deviceName || '').trim();
    if (!name) return;
    closeOverlay();
    const wrap = document.createElement('div');
    wrap.className = 'pas-drawer-backdrop';
    wrap.innerHTML = `
      <aside class="pas-drawer" role="dialog" aria-label="设备全景档案">
        <div class="pas-drawer-head">
          <h3><span>${esc(name)}</span><span class="se-pill neutral" id="pas-dr-type">加载中…</span></h3>
          <button class="se-btn compact" id="pas-dr-close">✕</button>
        </div>
        <div class="pas-drawer-links" id="pas-dr-links"></div>
        <div class="pas-drawer-body" id="pas-dr-body">
          <div style="color:var(--text-muted);font-size:12px">正在聚合 SE / LF / CA 与安全限值数据…</div>
        </div>
      </aside>`;
    wrap.addEventListener('click', (e) => { if (e.target === wrap) closeOverlay(); });
    wrap.querySelector('#pas-dr-close').addEventListener('click', closeOverlay);
    document.body.appendChild(wrap);
    _activeOverlay = wrap;

    try {
      const resp = await fetch(`/api/device/profile?name=${encodeURIComponent(name)}`);
      const json = await resp.json();
      if (!resp.ok || !json.ok) throw new Error(json.error || `HTTP ${resp.status}`);
      const d = json.data;
      const typeEl = wrap.querySelector('#pas-dr-type');
      if (typeEl) typeEl.textContent = d.device_type || '设备';

      const linksEl = wrap.querySelector('#pas-dr-links');
      if (linksEl) {
        linksEl.innerHTML = [
          `<a class="se-btn compact" href="${esc(d.links.se_flow)}">SE 接线图定位 ↗</a>`,
          `<a class="se-btn compact primary" href="${esc(d.links.lf_flow)}">LF 潮流图定位 ↗</a>`,
          `<a class="se-btn compact" href="${esc(d.links.ca_graph)}">CA 风险图定位 ↗</a>`,
          `<a class="se-btn compact" href="${esc(d.links.se_measurements)}">SE 量测明细 ↗</a>`,
        ].join('');
      }

      const seRows = (d.se_measurements || []).map((m) => `
        <tr><td>${esc(m.meas_type)}</td><td class="tabular">${num(m.meas_value, 3)}</td><td class="tabular">${num(m.est_value, 3)}</td><td class="tabular">${num(m.residual, 3)}</td></tr>`).join('');
      const lfBusRows = (d.lf_buses || []).map((b) => `
        <tr><td>母线 ${esc(b.domain || '')}</td><td class="tabular">${num(b.v_pu, 4)} pu</td><td class="tabular">${num(b.v_actual, 2)} ${esc(b.u_unit || 'V')}</td><td>${b.v_status && b.v_status !== 'normal' ? `<span class="se-pill bad">${esc(b.v_status)}</span>` : '<span class="se-pill ok">正常</span>'}</td></tr>`).join('');
      const lfBrRows = (d.lf_branches || []).map((b) => `
        <tr><td>${esc(b.device_type || '支路')}</td><td class="tabular">${num(b.p_from ?? b.p, 2)} kW</td><td class="tabular">${num(b.loading_pct, 1)}%</td><td>${b.load_status && b.load_status !== 'normal' ? `<span class="se-pill warn">${esc(b.load_status)}</span>` : '<span class="se-pill ok">正常</span>'}</td></tr>`).join('');
      const caRows = (d.ca_risks || []).map((r) => `
        <tr><td><span class="se-pill ${r.severity === 'critical' || r.severity === 'high' ? 'bad' : 'warn'}">${esc(r.severity)}</span></td><td>${esc(r.contingency_name)}</td><td>${esc(r.detail)}</td></tr>`).join('');
      const limRows = (d.limits || []).map((l) => `
        <tr><td>${esc(l.field)}</td><td class="tabular">${l.lower_value ?? '—'} ~ ${l.upper_value ?? '—'} ${esc(l.unit || '')}</td><td>${l.enabled ? '启用' : '停用'}</td></tr>`).join('');

      wrap.querySelector('#pas-dr-body').innerHTML = `
        <section class="pas-drawer-sec">
          <h4><span>潮流分析 LF 状态</span><span class="tabular">LF #${esc(d.run_ids?.lf ?? '—')}</span></h4>
          ${(lfBusRows || lfBrRows) ? `<table class="pas-mini-table"><thead><tr><th>类别</th><th>关键值</th><th>电压/负载</th><th>状态</th></tr></thead><tbody>${lfBusRows}${lfBrRows}</tbody></table>` : '<div style="color:var(--text-muted);font-size:12px">暂无 LF 结果</div>'}
        </section>
        <section class="pas-drawer-sec">
          <h4><span>静态安全 CA 风险 (${(d.ca_risks || []).length})</span><span class="tabular">CA #${esc(d.run_ids?.ca ?? '—')}</span></h4>
          ${caRows ? `<table class="pas-mini-table"><thead><tr><th>等级</th><th>故障场景</th><th>详情</th></tr></thead><tbody>${caRows}</tbody></table>` : '<div style="color:var(--text-muted);font-size:12px">未涉及当前 CA 风险</div>'}
        </section>
        <section class="pas-drawer-sec">
          <h4><span>状态估计 SE 量测 (${(d.se_measurements || []).length})</span><span class="tabular">SE #${esc(d.run_ids?.se ?? '—')}</span></h4>
          ${seRows ? `<table class="pas-mini-table"><thead><tr><th>量测类型</th><th>量测值</th><th>估计值</th><th>残差</th></tr></thead><tbody>${seRows}</tbody></table>` : '<div style="color:var(--text-muted);font-size:12px">暂无 SE 量测明细</div>'}
        </section>
        <section class="pas-drawer-sec">
          <h4><span>安全限值配置 (${(d.limits || []).length})</span></h4>
          ${limRows ? `<table class="pas-mini-table"><thead><tr><th>字段</th><th>限值范围</th><th>状态</th></tr></thead><tbody>${limRows}</tbody></table>` : '<div style="color:var(--text-muted);font-size:12px">未配置专属设备限值（沿用全局阈值）</div>'}
        </section>`;
    } catch (err) {
      wrap.querySelector('#pas-dr-body').innerHTML = `<div style="color:var(--sem-danger);font-size:12.5px">加载设备档案失败：${esc(err.message)}</div>`;
    }
  }

  /* ==================== 5. 历史断面 A/B Diff 对比弹窗 ==================== */
  async function openDiffModal(defaultMod = 'lf') {
    closeOverlay();
    const wrap = document.createElement('div');
    wrap.className = 'pas-cmd-backdrop';
    wrap.style.paddingTop = '6vh';
    wrap.innerHTML = `
      <div class="pas-diff-modal" role="dialog" aria-label="历史断面对比">
        <div class="pas-drawer-head">
          <h3>历史断面 A/B 差异对比 (Snapshot Diff)</h3>
          <button class="se-btn compact" id="pas-diff-close">✕</button>
        </div>
        <div class="pas-diff-bar">
          <select id="pas-diff-mod" class="se-select compact">
            <option value="lf" ${defaultMod === 'lf' ? 'selected' : ''}>潮流分析 LF</option>
            <option value="ca" ${defaultMod === 'ca' ? 'selected' : ''}>静态安全 CA</option>
            <option value="se" ${defaultMod === 'se' ? 'selected' : ''}>状态估计 SE</option>
          </select>
          <span style="font-size:12px;color:var(--text-muted)">基线 A</span>
          <select id="pas-diff-a" class="se-select compact"></select>
          <span style="font-size:12px;color:var(--text-muted)">对比 B</span>
          <select id="pas-diff-b" class="se-select compact"></select>
          <button class="se-btn compact primary" id="pas-diff-go">对比</button>
        </div>
        <div id="pas-diff-kpis" class="pas-diff-kpis"></div>
        <div style="flex:1;overflow:auto;padding:0 14px 14px">
          <table class="pas-mini-table">
            <thead><tr><th>设备 / 场景</th><th>变化指标</th><th>断面 A</th><th>断面 B</th><th>差值 Δ</th></tr></thead>
            <tbody id="pas-diff-rows"><tr><td colspan="5">正在加载…</td></tr></tbody>
          </table>
        </div>
      </div>`;
    wrap.addEventListener('click', (e) => { if (e.target === wrap) closeOverlay(); });
    wrap.querySelector('#pas-diff-close').addEventListener('click', closeOverlay);
    document.body.appendChild(wrap);
    _activeOverlay = wrap;

    const modSel = wrap.querySelector('#pas-diff-mod');
    const aSel = wrap.querySelector('#pas-diff-a');
    const bSel = wrap.querySelector('#pas-diff-b');

    async function loadDiff(keepSelection = false) {
      const mod = modSel.value;
      const qs = new URLSearchParams({ module: mod });
      if (keepSelection && aSel.value) qs.set('a', aSel.value);
      if (keepSelection && bSel.value) qs.set('b', bSel.value);
      try {
        const resp = await fetch(`/api/diff?${qs.toString()}`);
        const json = await resp.json();
        if (!resp.ok || !json.ok) throw new Error(json.error || `HTTP ${resp.status}`);
        const d = json.data;
        const opts = (d.available_runs || []).map((r) => `<option value="${r.run_id}">${esc(r.label)}</option>`).join('');
        aSel.innerHTML = opts || '<option value="">无可用断面</option>';
        bSel.innerHTML = opts || '<option value="">无可用断面</option>';
        if (d.run_a) aSel.value = String(d.run_a);
        if (d.run_b) bSel.value = String(d.run_b);

        wrap.querySelector('#pas-diff-kpis').innerHTML = (d.kpis || []).map((k) => {
          const dv = k.delta;
          const cls = dv == null || Number(dv) === 0 ? 'pas-delta-zero' : (Number(dv) > 0 ? 'pas-delta-pos' : 'pas-delta-neg');
          const sign = dv != null && Number(dv) > 0 ? '+' : '';
          return `<div class="pas-diff-kpi"><div style="color:var(--text-muted);font-size:11px">${esc(k.label)}</div><div class="tabular" style="margin-top:3px;display:flex;justify-content:space-between"><span>${k.a ?? '—'} → <strong>${k.b ?? '—'}</strong></span><span class="${cls}">${dv != null ? `${sign}${dv}` : '—'}</span></div></div>`;
        }).join('');

        wrap.querySelector('#pas-diff-rows').innerHTML = (d.changes || []).map((c) => {
          const dv = c.delta;
          const isNum = typeof dv === 'number';
          const cls = !isNum ? (String(dv).startsWith('+') ? 'pas-delta-pos' : 'pas-delta-neg') : (dv === 0 ? 'pas-delta-zero' : (dv > 0 ? 'pas-delta-pos' : 'pas-delta-neg'));
          const sign = isNum && dv > 0 ? '+' : '';
          return `<tr><td><a class="pas-clickable" data-pas-device="${esc(String(c.device).split(' [')[0])}">${esc(c.device)}</a></td><td>${esc(c.metric)}</td><td class="tabular">${esc(c.a)}</td><td class="tabular">${esc(c.b)}</td><td class="tabular ${cls}">${sign}${esc(dv)}</td></tr>`;
        }).join('') || '<tr><td colspan="5" style="color:var(--text-muted)">两期断面关键指标无显著变化</td></tr>';
      } catch (err) {
        wrap.querySelector('#pas-diff-rows').innerHTML = `<tr><td colspan="5" style="color:var(--sem-danger)">对比加载失败：${esc(err.message)}</td></tr>`;
      }
    }

    modSel.addEventListener('change', () => loadDiff(false));
    wrap.querySelector('#pas-diff-go').addEventListener('click', () => loadDiff(true));
    loadDiff(false);
  }

  /* ==================== 6. Ctrl+K 全站命令面板 ==================== */
  let _cachedDevices = null;
  async function loadDeviceNames() {
    if (_cachedDevices) return _cachedDevices;
    try {
      const resp = await fetch('/api/se/model-catalog');
      const json = await resp.json();
      if (resp.ok && json.ok && json.data) {
        const list = [];
        const seen = new Set();
        const pushDev = (name, type) => {
          const n = String(name || '').trim();
          if (!n || seen.has(n)) return;
          seen.add(n);
          list.push({ name: n, type: String(type || '') });
        };
        if (Array.isArray(json.data.devices)) {
          json.data.devices.forEach((d) => pushDev(d.name || d.device_name, d.device_type || d.table));
        } else if (json.data.devices && typeof json.data.devices === 'object') {
          Object.entries(json.data.devices).forEach(([dt, arr]) => {
            (arr || []).forEach((d) => pushDev(d.name || d.device_name, dt));
          });
        }
        if (json.data.devices_by_type && typeof json.data.devices_by_type === 'object') {
          Object.entries(json.data.devices_by_type).forEach(([dt, arr]) => {
            (arr || []).forEach((d) => pushDev(d.name || d.device_name, dt));
          });
        }
        _cachedDevices = list.slice(0, 500);
        return _cachedDevices;
      }
    } catch { /* ignore */ }
    return [];
  }

  async function openCommandPalette() {
    closeOverlay();
    const wrap = document.createElement('div');
    wrap.className = 'pas-cmd-backdrop';
    wrap.innerHTML = `
      <div class="pas-cmd-modal" role="dialog" aria-label="全站命令面板">
        <input class="pas-cmd-input" id="pas-cmd-q" placeholder="搜索页面、电网设备、14 套风格或操作（如：电化学储能、碳黑琥珀、对比、报告）…" autocomplete="off">
        <div class="pas-cmd-list" id="pas-cmd-list"></div>
        <div class="pas-cmd-foot"><span>↑↓ 选择 · Enter 执行 · Esc 关闭</span><span>快捷键：Ctrl+K 命令 · R 刷新</span></div>
      </div>`;
    wrap.addEventListener('click', (e) => { if (e.target === wrap) closeOverlay(); });
    document.body.appendChild(wrap);
    _activeOverlay = wrap;

    const input = wrap.querySelector('#pas-cmd-q');
    const listEl = wrap.querySelector('#pas-cmd-list');
    let activeIdx = 0;
    let currentItems = [];
    const devices = await loadDeviceNames();
    const themes = (window.PAS_THEME_GROUPS || []).flatMap((g) => g.items.map((it) => ({
      id: it.id,
      label: it.label[getLang()] || it.label['zh-CN'],
      group: g.label[getLang()] || g.label['zh-CN'],
    })));

    function render(qRaw) {
      const q = (qRaw || '').trim().toLowerCase();
      const items = [];
      // 快捷操作
      const actions = [
        { title: '打开历史断面 A/B 对比 (LF / CA / SE)', tag: '操作', run: () => openDiffModal() },
        { title: '导出 SE→LF→CA 综合分析快照报告 (HTML)', tag: '报告', run: () => { closeOverlay(); window.open('/api/report/snapshot', '_blank'); } },
        { title: '查看数据源与数据库健康体检', tag: '诊断', run: () => { window.location.href = '/workspace.html'; } },
      ];
      actions.forEach((a) => {
        if (!q || a.title.toLowerCase().includes(q) || a.tag.toLowerCase().includes(q)) items.push({ group: '快捷操作', ...a });
      });
      // 页面跳转
      PAGES.forEach((p) => {
        const hay = `${p.title} ${p.en} ${p.ru} ${p.path}`.toLowerCase();
        if (!q || hay.includes(q)) {
          items.push({ group: '页面导航', title: p.title, tag: p.path, run: () => { window.location.href = p.path; } });
        }
      });
      // 设备 360° 档案
      devices.forEach((d) => {
        const hay = `${d.name} ${d.type}`.toLowerCase();
        if (q && hay.includes(q)) {
          items.push({ group: '设备 360° 档案', title: d.name, tag: d.type, run: () => openDeviceDrawer(d.name) });
        }
      });
      // 14 套主题
      themes.forEach((th) => {
        const hay = `${th.label} ${th.id} ${th.group}`.toLowerCase();
        if (!q || hay.includes(q)) {
          items.push({
            group: '切换视觉风格',
            title: th.label,
            tag: th.group,
            run: () => {
              if (window.PAS_APPLY_THEME) window.PAS_APPLY_THEME(th.id);
              closeOverlay();
            },
          });
        }
      });

      currentItems = items.slice(0, 40);
      activeIdx = 0;
      let htmlOut = '';
      let lastG = '';
      currentItems.forEach((it, idx) => {
        if (it.group !== lastG) {
          htmlOut += `<div class="pas-cmd-group">${esc(it.group)}</div>`;
          lastG = it.group;
        }
        htmlOut += `<button type="button" class="pas-cmd-item ${idx === 0 ? 'active' : ''}" data-idx="${idx}"><span>${esc(it.title)}</span><span class="pas-cmd-tag">${esc(it.tag)}</span></button>`;
      });
      listEl.innerHTML = htmlOut || '<div style="padding:14px;color:var(--text-muted);text-align:center;font-size:12px">无匹配结果</div>';
      listEl.querySelectorAll('.pas-cmd-item').forEach((btn) => {
        btn.addEventListener('click', () => {
          const item = currentItems[Number(btn.dataset.idx)];
          if (item) item.run();
        });
      });
    }

    input.addEventListener('input', () => render(input.value));
    input.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIdx = Math.min(currentItems.length - 1, activeIdx + 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIdx = Math.max(0, activeIdx - 1);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (currentItems[activeIdx]) currentItems[activeIdx].run();
        return;
      } else {
        return;
      }
      listEl.querySelectorAll('.pas-cmd-item').forEach((el, i) => {
        el.classList.toggle('active', i === activeIdx);
        if (i === activeIdx) el.scrollIntoView({ block: 'nearest' });
      });
    });

    render('');
    input.focus();
  }

  /* ==================== 7. 全局事件与旧页快捷工具条自动增强 ==================== */
  function mountTopbarEnhancements() {
    // 1. 若旧运行管理页缺少 #lang-select，自动补充三语下拉
    const topActions = document.querySelector('.top-actions, .se-top-actions');
    if (topActions && !document.getElementById('pas-cmd-trigger')) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.id = 'pas-cmd-trigger';
      btn.className = 'pas-kbd-btn';
      btn.title = '全站快速搜索 / 设备档案 / 切换风格 (Ctrl+K)';
      btn.innerHTML = '<span>搜索</span><kbd>Ctrl+K</kbd>';
      btn.addEventListener('click', openCommandPalette);
      topActions.insertBefore(btn, topActions.firstChild);
    }
    if (document.querySelector('.top-actions') && !document.getElementById('lang-select')) {
      const sel = document.createElement('select');
      sel.id = 'lang-select';
      sel.className = 'se-select compact';
      sel.setAttribute('aria-label', 'Language');
      sel.innerHTML = '<option value="zh-CN">中文</option><option value="en-US">EN</option><option value="ru-RU">RU</option>';
      sel.value = getLang();
      sel.addEventListener('change', () => {
        const next = sel.value;
        try {
          localStorage.setItem('pas_se_lang', next);
          localStorage.setItem('se_lang', next);
        } catch { /* ignore */ }
        applyLegacyI18n(next);
        if (window.PAS_POPULATE_THEME_SELECT) {
          document.querySelectorAll('#theme-select').forEach((ts) => window.PAS_POPULATE_THEME_SELECT(ts, next));
        }
      });
      const themeSel = document.getElementById('theme-select');
      if (themeSel && themeSel.parentElement) {
        themeSel.insertAdjacentElement('afterend', sel);
      } else if (topActions) {
        topActions.appendChild(sel);
      }
    }
    applyLegacyI18n(getLang());
  }

  // 全局委托：点击任何 data-pas-device 元素直接打开 360° 设备抽屉
  document.addEventListener('click', (e) => {
    const el = e.target.closest?.('[data-pas-device]');
    if (!el) return;
    e.preventDefault();
    openDeviceDrawer(el.dataset.pasDevice);
  });

  // 全局快捷键：Ctrl+K / Cmd+K 打开命令面板，Esc 关闭，R 刷新
  document.addEventListener('keydown', (e) => {
    const tag = (e.target?.tagName || '').toLowerCase();
    const editing = tag === 'input' || tag === 'textarea' || tag === 'select' || e.target?.isContentEditable;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      openCommandPalette();
      return;
    }
    if (e.key === 'Escape' && _activeOverlay) {
      e.preventDefault();
      closeOverlay();
      return;
    }
    if (!editing && !e.ctrlKey && !e.metaKey && !e.altKey && e.key.toLowerCase() === 'r') {
      const refreshBtn = document.querySelector('#btn-refresh, [data-action="refresh"]');
      if (refreshBtn) {
        e.preventDefault();
        refreshBtn.click();
      }
    }
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mountTopbarEnhancements);
  } else {
    mountTopbarEnhancements();
  }

  window.PAS_KIT = {
    openCommandPalette,
    openDeviceDrawer,
    openDiffModal,
    renderTrendChart,
    createPoller,
    applyLegacyI18n,
    exportReport: () => window.open('/api/report/snapshot', '_blank'),
  };
})();
