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
    { path: '/settings.html', title: '运行管理 · 系统设置（调度 / 数据源与目录 / 数据库 / 日志）', en: 'System Settings', ru: 'Настройки системы', cat: '运行管理' },
    { path: '/settings.html?tab=datasource', title: '系统设置 · 数据源健康体检与工作目录', en: 'Datasources & Workspace', ru: 'Источники данных', cat: '运行管理' },
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

  /* ==================== 3B. 多维工程可视化引擎（桑基图 / 环形饼图 / 半圆仪表盘 / 分级柱状图 / 双向偏差柱状图） ==================== */
  function bindSvgTip(el, htmlFn) {
    const tip = getTipEl();
    el.addEventListener('mousemove', (ev) => {
      tip.innerHTML = typeof htmlFn === 'function' ? htmlFn() : String(htmlFn || '');
      tip.hidden = false;
      const tx = Math.min(window.innerWidth - tip.offsetWidth - 12, ev.clientX + 14);
      const ty = Math.max(8, ev.clientY - tip.offsetHeight - 10);
      tip.style.left = `${tx}px`;
      tip.style.top = `${ty}px`;
    });
    el.addEventListener('mouseleave', () => { tip.hidden = true; });
  }

  /**
   * 交直流能量流桑基图（3 列：电源列 -> 汇流中枢 -> 负荷与网损列）
   * 支持 compact 窄栏模式与自动标签防碰撞，确保小份额网损节点零重叠、零裁切。
   */
  function renderSankey(host, {
    leftNodes = [],
    midNode = { label: '混合电网', color: '#38bdf8' },
    rightNodes = [],
    unit = 'kW',
    height = 148,
    compact = false,
    emptyText = '暂无功率流向数据',
  } = {}) {
    if (!host) return;
    const leftClean = leftNodes.filter((n) => Number(n.value) > 0);
    const rightClean = rightNodes.filter((n) => Number(n.value) > 0);
    const sumL = leftClean.reduce((s, n) => s + Number(n.value), 0);
    const sumR = rightClean.reduce((s, n) => s + Number(n.value), 0);
    const total = Math.max(sumL, sumR);
    if (total <= 1e-6) {
      host.innerHTML = `<div class="se-empty">${esc(emptyText)}</div>`;
      return;
    }
    const W = compact ? 276 : 520;
    const H = height;
    const padTop = 18;
    const padBot = 10;
    const usableH = H - padTop - padBot;
    const gap = compact ? 9 : 10;
    const barW = compact ? 9 : 12;
    const xL = compact ? 76 : 108;
    const xM = Math.round(W / 2 - barW / 2);
    const xR = compact ? W - 102 : W - 142;

    const layoutCol = (list, colSum) => {
      const totalGap = gap * Math.max(0, list.length - 1);
      const avail = Math.max(24, usableH - totalGap);
      let y = padTop;
      return list.map((n) => {
        const val = Number(n.value);
        const h = Math.max(7, (val / Math.max(colSum, 1e-6)) * avail);
        const out = { ...n, val, y, h };
        y += h + gap;
        return out;
      });
    };

    // 标签中心 Y 防碰撞分配（保证相邻标签至少间隔 minStep，且不出底边）
    const assignLabelY = (items, minStep) => {
      const ys = items.map((n) => n.y + n.h / 2);
      for (let i = 1; i < ys.length; i++) {
        if (ys[i] - ys[i - 1] < minStep) ys[i] = ys[i - 1] + minStep;
      }
      const maxY = H - 7;
      if (ys.length && ys[ys.length - 1] > maxY) {
        const shift = ys[ys.length - 1] - maxY;
        for (let i = ys.length - 1; i >= 0; i--) {
          ys[i] -= shift;
          if (i > 0 && ys[i] - ys[i - 1] < minStep) ys[i - 1] = ys[i] - minStep;
        }
      }
      return ys.map((y) => Math.max(padTop + 4, Math.min(maxY, y)));
    };

    const lPos = layoutCol(leftClean, sumL);
    const rPos = layoutCol(rightClean, sumR);
    const lLabelYs = assignLabelY(lPos, compact ? 20 : 24);
    const rLabelYs = assignLabelY(rPos, compact ? 16 : 17);

    const midH = Math.max(26, usableH * 0.84);
    const midY = padTop + (usableH - midH) / 2;

    const ribbonPath = (x0, y0, h0, x1, y1, h1) => {
      const mx = (x0 + x1) / 2;
      return `M${x0},${y0} C${mx},${y0} ${mx},${y1} ${x1},${y1} L${x1},${y1 + h1} C${mx},${y1 + h1} ${mx},${y0 + h0} ${x0},${y0 + h0} Z`;
    };

    let midOffL = midY;
    const leftRibbons = lPos.map((n) => {
      const mh = (n.val / Math.max(sumL, 1e-6)) * midH;
      const d = ribbonPath(xL + barW, n.y, n.h, xM, midOffL, mh);
      const cy0 = n.y + n.h / 2;
      const cy1 = midOffL + mh / 2;
      const mx = (xL + barW + xM) / 2;
      const flowD = `M${xL + barW},${cy0.toFixed(1)} C${mx},${cy0.toFixed(1)} ${mx},${cy1.toFixed(1)} ${xM},${cy1.toFixed(1)}`;
      midOffL += mh;
      return `<path class="pas-sk-link" data-sk-tip="${esc(`${n.label} → ${midNode.label}<br><strong>${num(n.val, 2)} ${unit}</strong> (${((n.val / sumL) * 100).toFixed(1)}%)`)}" d="${d}" fill="${n.color}" fill-opacity="0.34" stroke="${n.color}" stroke-opacity="0.62" stroke-width="0.6"/>`
        + `<path class="pas-sk-flow" d="${flowD}" fill="none" stroke="${n.color}" stroke-width="${Math.max(1.2, Math.min(3, n.h * 0.14)).toFixed(1)}" stroke-opacity="0.78" pointer-events="none"/>`;
    }).join('');

    let midOffR = midY;
    const rightRibbons = rPos.map((n) => {
      const mh = (n.val / Math.max(sumR, 1e-6)) * midH;
      const d = ribbonPath(xM + barW, midOffR, mh, xR, n.y, n.h);
      const cy0 = midOffR + mh / 2;
      const cy1 = n.y + n.h / 2;
      const mx = (xM + barW + xR) / 2;
      const flowD = `M${xM + barW},${cy0.toFixed(1)} C${mx},${cy0.toFixed(1)} ${mx},${cy1.toFixed(1)} ${xR},${cy1.toFixed(1)}`;
      midOffR += mh;
      return `<path class="pas-sk-link" data-sk-tip="${esc(`${midNode.label} → ${n.label}<br><strong>${num(n.val, 2)} ${unit}</strong> (${((n.val / sumR) * 100).toFixed(1)}%)`)}" d="${d}" fill="${n.color}" fill-opacity="0.34" stroke="${n.color}" stroke-opacity="0.62" stroke-width="0.6"/>`
        + `<path class="pas-sk-flow" d="${flowD}" fill="none" stroke="${n.color}" stroke-width="${Math.max(1.2, Math.min(3, n.h * 0.14)).toFixed(1)}" stroke-opacity="0.78" pointer-events="none"/>`;
    }).join('');

    const fMain = compact ? 9.5 : 11;
    const fSub = compact ? 8.8 : 10;
    const leftRects = lPos.map((n, idx) => {
      const ly = lLabelYs[idx];
      return `
        <rect x="${xL}" y="${n.y.toFixed(1)}" width="${barW}" height="${n.h.toFixed(1)}" rx="3" fill="${n.color}"/>
        <text x="${xL - 5}" y="${(ly - 2).toFixed(1)}" text-anchor="end" fill="var(--text-primary)" font-size="${fMain}" font-weight="600">${esc(n.label)}</text>
        <text x="${xL - 5}" y="${(ly + 9).toFixed(1)}" text-anchor="end" fill="var(--text-secondary)" font-size="${fSub}" class="tabular">${num(n.val, 1)} ${esc(unit)}</text>`;
    }).join('');

    // 右侧采用防重叠布局：高度充裕时双行，高度紧凑时单行“名称 数值”避免纵向叠加
    const rightRects = rPos.map((n, idx) => {
      const ly = rLabelYs[idx];
      const singleLine = compact || n.h < 22;
      if (singleLine) {
        return `
          <rect x="${xR}" y="${n.y.toFixed(1)}" width="${barW}" height="${n.h.toFixed(1)}" rx="3" fill="${n.color}"/>
          <text x="${xR + barW + 5}" y="${(ly + 3.5).toFixed(1)}" text-anchor="start" fill="var(--text-primary)" font-size="${fMain}" font-weight="600">${esc(n.label)} <tspan fill="var(--text-secondary)" font-weight="500" font-size="${fSub}">${num(n.val, 1)}${compact ? '' : ' ' + esc(unit)}</tspan></text>`;
      }
      return `
        <rect x="${xR}" y="${n.y.toFixed(1)}" width="${barW}" height="${n.h.toFixed(1)}" rx="3" fill="${n.color}"/>
        <text x="${xR + barW + 6}" y="${(ly - 2).toFixed(1)}" text-anchor="start" fill="var(--text-primary)" font-size="${fMain}" font-weight="600">${esc(n.label)}</text>
        <text x="${xR + barW + 6}" y="${(ly + 10).toFixed(1)}" text-anchor="start" fill="var(--text-secondary)" font-size="${fSub}" class="tabular">${num(n.val, 1)} ${esc(unit)}</text>`;
    }).join('');

    host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:${H}px;display:block">
      ${leftRibbons}
      ${rightRibbons}
      ${leftRects}
      <rect x="${xM}" y="${midY.toFixed(1)}" width="${barW}" height="${midH.toFixed(1)}" rx="4" fill="${midNode.color || 'var(--accent)'}"/>
      <text x="${W / 2}" y="${(padTop - 5).toFixed(1)}" text-anchor="middle" fill="var(--text-primary)" font-size="${fSub}" font-weight="600">${esc(midNode.label)} (${num(total, 1)} ${esc(unit)})</text>
      ${rightRects}
    </svg>`;

    host.querySelectorAll('.pas-sk-link').forEach((path) => {
      bindSvgTip(path, () => path.dataset.skTip);
    });
  }

  /**
   * 环形饼图（左侧圆环 + 中心主指标 + 右侧紧凑图例）
   */
  function renderDonut(host, {
    slices = [],
    centerTitle = '总计',
    centerValue = null,
    size = 112,
    emptyText = '暂无数据',
  } = {}) {
    if (!host) return;
    const clean = slices.map((s) => ({ ...s, val: Math.max(0, Number(s.value) || 0) }));
    const total = clean.reduce((sum, s) => sum + s.val, 0);
    const r = 40;
    const cx = 56;
    const cy = 56;
    const circ = 2 * Math.PI * r;
    let offset = 0;

    const segs = total > 0
      ? clean.filter((s) => s.val > 0).map((s) => {
        const frac = s.val / total;
        const len = Math.max(2, frac * circ);
        const dash = `${len.toFixed(2)} ${(circ - len).toFixed(2)}`;
        const curOff = offset;
        offset += len;
        return `<circle class="pas-donut-seg" data-tip="${esc(`<strong>${s.label}</strong><br>${s.val} (${(frac * 100).toFixed(1)}%)`)}" cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${s.color}" stroke-width="13" stroke-dasharray="${dash}" stroke-dashoffset="${(-curOff).toFixed(2)}" transform="rotate(-90 ${cx} ${cy})"/>`;
      }).join('')
      : `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--border-color)" stroke-width="12"/>`;

    const centerVal = centerValue != null ? centerValue : String(total);
    const legendHtml = clean.map((s) => {
      const pct = total > 0 ? `${((s.val / total) * 100).toFixed(0)}%` : '0%';
      return `<div class="pas-donut-leg-row"><span><i style="background:${s.color}"></i>${esc(s.label)}</span><strong class="tabular">${s.val} <small>${pct}</small></strong></div>`;
    }).join('');

    host.innerHTML = `<div class="pas-donut-box">
      <svg viewBox="0 0 112 112" style="width:${size}px;height:${size}px;flex:0 0 ${size}px">
        <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--bg-subtle)" stroke-width="13"/>
        ${segs}
        <text x="${cx}" y="${cy - 1}" text-anchor="middle" fill="var(--text-primary)" font-size="16" font-weight="700" class="tabular">${esc(centerVal)}</text>
        <text x="${cx}" y="${cy + 13}" text-anchor="middle" fill="var(--text-secondary)" font-size="9.5">${esc(centerTitle)}</text>
      </svg>
      <div class="pas-donut-legend">${legendHtml || `<span style="color:var(--text-muted)">${esc(emptyText)}</span>`}</div>
    </div>`;

    host.querySelectorAll('.pas-donut-seg').forEach((seg) => {
      bindSvgTip(seg, () => seg.dataset.tip);
    });
  }

  /**
   * 立体刻度半圆工程仪表盘（安全评分 / 合格率 / 负载指标）
   */
  function renderGauge(host, {
    value = 0,
    max = 100,
    label = '',
    unit = '',
    statusText = '',
    width = 168,
    height = 96,
  } = {}) {
    if (!host) return;
    const v = Math.max(0, Math.min(max, Number(value) || 0));
    const ratio = max > 0 ? v / max : 0;
    const color = ratio >= 0.8 ? '#22c55e' : (ratio >= 0.6 ? '#f59e0b' : '#ef4444');
    const r = 56;
    const cx = 84;
    const cy = 74;
    const arcLen = Math.PI * r;
    const filled = Math.max(0, ratio * arcLen);
    // 末端指示点坐标（从左 180° 顺时针扫到右 0°）
    const angle = Math.PI * (1 - ratio);
    const dotX = cx + r * Math.cos(angle);
    const dotY = cy - r * Math.sin(angle);
    // 外圈刻度线（0, 20, 40, 60, 80, 100）
    const ticks = [0, 0.2, 0.4, 0.6, 0.8, 1].map((frac) => {
      const a = Math.PI * (1 - frac);
      const x1 = cx + (r + 7) * Math.cos(a);
      const y1 = cy - (r + 7) * Math.sin(a);
      const x2 = cx + (r + 11) * Math.cos(a);
      const y2 = cy - (r + 11) * Math.sin(a);
      return `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="var(--text-secondary)" stroke-opacity="0.45" stroke-width="1.3"/>`;
    }).join('');
    // 外圈三色警戒参考细弧（0-60 红，60-80 橙，80-100 绿）
    const rOuter = r + 5.5;
    const arcSeg = (f0, f1, strokeCol) => {
      const a0 = Math.PI * (1 - f0);
      const a1 = Math.PI * (1 - f1);
      const x0 = cx + rOuter * Math.cos(a0);
      const y0 = cy - rOuter * Math.sin(a0);
      const x1 = cx + rOuter * Math.cos(a1);
      const y1 = cy - rOuter * Math.sin(a1);
      return `<path d="M ${x0.toFixed(1)} ${y0.toFixed(1)} A ${rOuter} ${rOuter} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)}" fill="none" stroke="${strokeCol}" stroke-width="2.2" stroke-opacity="0.55"/>`;
    };

    host.innerHTML = `<div class="pas-gauge-box">
      <svg viewBox="0 0 168 96" style="width:${width}px;height:${height}px;display:block;margin:0 auto">
        ${arcSeg(0, 0.59, '#ef4444')}
        ${arcSeg(0.61, 0.79, '#f59e0b')}
        ${arcSeg(0.81, 1.0, '#22c55e')}
        ${ticks}
        <path d="M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}" fill="none" stroke="var(--bg-subtle)" stroke-width="11" stroke-linecap="round"/>
        <path class="pas-gauge-arc" d="M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}" fill="none" stroke="${color}" stroke-width="11" stroke-linecap="round" stroke-dasharray="${filled.toFixed(1)} ${arcLen.toFixed(1)}"/>
        <circle cx="${dotX.toFixed(1)}" cy="${dotY.toFixed(1)}" r="4.5" fill="var(--bg-surface)" stroke="${color}" stroke-width="2.6"/>
        <text x="${cx}" y="${cy - 14}" text-anchor="middle" fill="var(--text-primary)" font-size="24" font-weight="800" class="tabular">${num(v, 1)}<tspan font-size="11" font-weight="600" fill="var(--text-secondary)">${esc(unit)}</tspan></text>
        <text x="${cx}" y="${cy + 5}" text-anchor="middle" fill="${color}" font-size="11" font-weight="700">${esc(statusText || label)}</text>
      </svg>
    </div>`;
  }

  /**
   * 形象化数据流/清洗流水线图（节点 + 动态流光箭头 + 占比进度条 + 点击下钻）
   */
  function renderPipelineFlow(host, { steps = [], emptyText = '—' } = {}) {
    if (!host) return;
    if (!steps.length) {
      host.innerHTML = `<div class="se-empty">${esc(emptyText)}</div>`;
      return;
    }
    const maxVal = Math.max(1, ...steps.map((s) => Number(s.value) || 0));
    host.innerHTML = `<div class="pas-pipe-list">${steps.map((s, idx) => {
      const val = Number(s.value) || 0;
      const pct = s.pct != null ? Math.max(0, Math.min(100, Number(s.pct))) : Math.min(100, (val / maxVal) * 100);
      const tone = s.tone || 'accent';
      const tagOpen = s.href ? `<a class="pas-pipe-node tone-${esc(tone)}" href="${esc(s.href)}"` : `<div class="pas-pipe-node tone-${esc(tone)}"`;
      const tagClose = s.href ? '</a>' : '</div>';
      const tip = s.tip || `${s.label}：${s.display ?? val}`;
      const arrow = idx < steps.length - 1 ? '<div class="pas-pipe-arrow" aria-hidden="true"><span></span></div>' : '';
      return `${tagOpen} data-pipe-tip="${esc(tip)}">
          <div class="pas-pipe-top">
            <span class="pas-pipe-badge">${idx + 1}</span>
            <span class="pas-pipe-name">${esc(s.label)}</span>
            <strong class="pas-pipe-val tabular">${esc(s.display != null ? s.display : String(val))}</strong>
          </div>
          <div class="pas-pipe-bar"><i style="width:${Math.max(val > 0 ? 4 : 0, pct).toFixed(1)}%"></i></div>
        ${tagClose}${arrow}`;
    }).join('')}</div>`;
    host.querySelectorAll('.pas-pipe-node').forEach((node) => {
      bindSvgTip(node, () => node.dataset.pipeTip);
    });
  }

  /**
   * 多维健康画像雷达图（5~6 维工程指标雷达，带渐变多边形与悬停提示）
   */
  function renderRadarChart(host, {
    axes = [],
    size = 172,
    color = 'var(--accent)',
    emptyText = '—',
  } = {}) {
    if (!host) return;
    if (!axes.length) {
      host.innerHTML = `<div class="se-empty">${esc(emptyText)}</div>`;
      return;
    }
    const W = 220;
    const H = 176;
    const cx = W / 2;
    const cy = H / 2 + 4;
    const R = 58;
    const n = axes.length;
    const angleOf = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / n;
    const pt = (i, frac) => {
      const a = angleOf(i);
      return [cx + R * frac * Math.cos(a), cy + R * frac * Math.sin(a)];
    };

    const rings = [0.25, 0.5, 0.75, 1].map((f) => {
      const pts = axes.map((_, i) => pt(i, f).map((v) => v.toFixed(1)).join(',')).join(' ');
      return `<polygon points="${pts}" fill="none" stroke="var(--grid-line)" stroke-width="${f === 1 ? 1.2 : 0.8}" stroke-dasharray="${f === 1 ? 'none' : '2 2'}"/>`;
    }).join('');

    const spokes = axes.map((ax, i) => {
      const [x, y] = pt(i, 1);
      const [lx, ly] = pt(i, 1.24);
      const anchor = Math.abs(lx - cx) < 8 ? 'middle' : (lx > cx ? 'start' : 'end');
      return `<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="var(--grid-line)" stroke-width="0.9"/>`
        + `<text x="${lx.toFixed(1)}" y="${(ly + 3.5).toFixed(1)}" text-anchor="${anchor}" fill="var(--text-secondary)" font-size="10.5" font-weight="600">${esc(ax.label)}</text>`;
    }).join('');

    const dataPts = axes.map((ax, i) => {
      const ratio = Math.max(0.06, Math.min(1, (Number(ax.value) || 0) / (Number(ax.max) || 100)));
      return { xy: pt(i, ratio), ax, ratio };
    });
    const polyPts = dataPts.map((p) => p.xy.map((v) => v.toFixed(1)).join(',')).join(' ');
    const dots = dataPts.map((p) => {
      const tip = `<strong>${p.ax.label}</strong><br>${num(p.ax.value, 1)}${p.ax.unit || '%'}${p.ax.sub ? `<br>${p.ax.sub}` : ''}`;
      return `<circle class="pas-radar-dot" data-rd-tip="${esc(tip)}" cx="${p.xy[0].toFixed(1)}" cy="${p.xy[1].toFixed(1)}" r="3.8" fill="${color}" stroke="var(--bg-surface)" stroke-width="1.6"/>`;
    }).join('');

    host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:${size}px;display:block">
      ${rings}
      ${spokes}
      <polygon points="${polyPts}" fill="${color}" fill-opacity="0.22" stroke="${color}" stroke-width="2" stroke-linejoin="round"/>
      ${dots}
    </svg>`;
    host.querySelectorAll('.pas-radar-dot').forEach((el) => {
      bindSvgTip(el, () => el.dataset.rdTip);
    });
  }

  /**
   * 竖向分段分布直方图（母线电压区间 / 支路负载区间分布）
   */
  function renderHistogram(host, {
    bins = [],
    unit = '',
    height = 104,
    emptyText = '—',
  } = {}) {
    if (!host) return;
    if (!bins.length) {
      host.innerHTML = `<div class="se-empty">${esc(emptyText)}</div>`;
      return;
    }
    const total = bins.reduce((s, b) => s + (Number(b.count) || 0), 0);
    const maxCnt = Math.max(1, ...bins.map((b) => Number(b.count) || 0));
    const toneColor = {
      ok: 'var(--sem-ok)',
      info: '#38bdf8',
      accent: 'var(--accent)',
      warn: 'var(--sem-warn)',
      danger: 'var(--sem-danger)',
    };
    host.innerHTML = `<div class="pas-hist-grid" style="height:${height}px">${bins.map((b) => {
      const cnt = Number(b.count) || 0;
      const pctH = cnt > 0 ? Math.max(10, (cnt / maxCnt) * 100) : 4;
      const share = total > 0 ? ((cnt / total) * 100).toFixed(1) : '0.0';
      const col = b.color || toneColor[b.tone] || 'var(--accent)';
      const tip = `<strong>${b.label}</strong><br>${cnt} ${unit} (${share}%)`;
      return `<div class="pas-hist-col" data-hist-tip="${esc(tip)}">
        <div class="pas-hist-cnt tabular" style="color:${cnt > 0 ? col : 'var(--text-secondary)'}">${cnt}</div>
        <div class="pas-hist-track">
          <div class="pas-hist-bar" style="height:${pctH.toFixed(1)}%;background:${col};opacity:${cnt > 0 ? '0.88' : '0.18'}"></div>
        </div>
        <div class="pas-hist-lbl tabular" title="${esc(b.label)}">${esc(b.label)}</div>
      </div>`;
    }).join('')}</div>`;
    host.querySelectorAll('.pas-hist-col').forEach((el) => {
      bindSvgTip(el, () => el.dataset.histTip);
    });
  }

  /**
   * 预想故障全景热力矩阵墙（N-0 / N-1 / N-k 状态瓷砖阵列 + 悬停明细 + 点击下钻）
   */
  function renderHeatMatrix(host, {
    cells = [],
    onClickCell = null,
    emptyText = '—',
  } = {}) {
    if (!host) return;
    if (!cells.length) {
      host.innerHTML = `<div class="se-empty">${esc(emptyText)}</div>`;
      return;
    }
    const sevMeta = {
      critical: { cls: 'sev-critical', badge: '危' },
      high: { cls: 'sev-high', badge: '高' },
      medium: { cls: 'sev-medium', badge: '中' },
      low: { cls: 'sev-low', badge: '低' },
      normal: { cls: 'sev-ok', badge: '安' },
    };
    host.innerHTML = `<div class="pas-heat-matrix">${cells.map((c, idx) => {
      const sev = !c.converged ? 'critical' : (c.severity || (c.risk_count > 0 ? 'medium' : 'normal'));
      const meta = sevMeta[sev] || sevMeta.normal;
      const isWeather = String(c.category || '') === 'Weather';
      const shortName = String(c.contingency_name || '').replace(/^(N-[01k]|气象)\s*[:：\-]?\s*/i, '');
      const catTag = isWeather ? '❄ 气象' : c.category;
      const tip = [
        `<strong>${esc(c.contingency_name)}</strong> (${esc(isWeather ? '气象/负荷扰动' : c.category)})`,
        c.target_desc ? `<span style="color:var(--text-secondary)">${esc(c.target_desc)}</span>` : '',
        `收敛: <strong>${c.converged ? 'OK' : '发散'}</strong> · 风险: <strong>${c.risk_count}</strong>`,
        `最大负载: <strong>${num(c.max_loading_pct, 1)}%</strong> · 失电: <strong>${num(c.load_loss_kw, 1)}</strong>`,
        c.min_v_pu != null ? `最低电压: <strong>${num(c.min_v_pu, 4)} pu</strong>` : '',
      ].filter(Boolean).join('<br>');
      return `<button type="button" class="pas-heat-tile ${meta.cls}${isWeather ? ' is-weather' : ''}" data-heat-idx="${idx}" data-heat-tip="${esc(tip)}">
        <span class="pas-heat-cat">${esc(catTag)}</span>
        <span class="pas-heat-name">${esc(shortName || c.contingency_name)}</span>
        <span class="pas-heat-num tabular">${c.converged ? (c.risk_count > 0 ? `${c.risk_count}险` : '✓') : '发散'}</span>
      </button>`;
    }).join('')}</div>`;
    host.querySelectorAll('.pas-heat-tile').forEach((tile) => {
      bindSvgTip(tile, () => tile.dataset.heatTip);
      if (typeof onClickCell === 'function') {
        tile.addEventListener('click', () => {
          const item = cells[Number(tile.dataset.heatIdx)];
          if (item) onClickCell(item);
        });
      }
    });
  }

  /**
   * 水平分级柱状图（支持阈值参考线、点击联动设备 360° 抽屉）
   */
  function renderBarChart(host, {
    items = [],
    maxVal = null,
    unit = '%',
    threshold = null,
    digits = 1,
    emptyText = '暂无数据',
  } = {}) {
    if (!host) return;
    if (!items.length) {
      host.innerHTML = `<div class="se-empty">${esc(emptyText)}</div>`;
      return;
    }
    const peak = Math.max(
      maxVal || 0,
      threshold ? threshold * 1.15 : 0,
      ...items.map((x) => Number(x.value) || 0),
      1e-6,
    );
    const thrPct = threshold != null ? Math.min(100, (threshold / peak) * 100) : null;

    host.innerHTML = `<div class="pas-bar-list">${items.map((it) => {
      const val = Math.max(0, Number(it.value) || 0);
      const pct = Math.min(100, (val / peak) * 100);
      const color = it.color || (threshold != null
        ? (val >= threshold * 1.25 ? '#ef4444' : (val >= threshold ? '#f59e0b' : 'var(--accent)'))
        : 'var(--accent)');
      const labelHtml = it.device
        ? `<a class="pas-clickable" data-pas-device="${esc(it.device)}" title="打开 ${esc(it.device)} 360° 全景档案">${esc(it.label)}</a>`
        : `<span>${esc(it.label)}</span>`;
      return `<div class="pas-bar-row" data-bar-tip="${esc(`<strong>${it.label}</strong><br>${num(val, digits)} ${unit}${it.sub ? `<br>${it.sub}` : ''}`)}">
        <div class="pas-bar-label">${labelHtml}</div>
        <div class="pas-bar-track">
          ${thrPct != null ? `<span class="pas-bar-thr" style="left:${thrPct.toFixed(1)}%"></span>` : ''}
          <span class="pas-bar-fill" style="width:${Math.max(2, pct).toFixed(1)}%;background:${color}"></span>
        </div>
        <div class="pas-bar-val tabular">${num(val, digits)}${esc(unit)}${it.subShort ? ` <small>${esc(it.subShort)}</small>` : ''}</div>
      </div>`;
    }).join('')}</div>`;

    host.querySelectorAll('.pas-bar-row').forEach((row) => {
      bindSvgTip(row, () => row.dataset.barTip);
    });
  }

  /**
   * 双向偏差柱状图（例如以 1.00 pu 为中轴展现电压偏低/偏高幅度）
   */
  function renderDivergingBar(host, {
    items = [],
    center = 1.0,
    span = 0.22,
    lowWarn = 0.93,
    highWarn = 1.07,
    unit = 'pu',
    emptyText = '暂无电压越限设备',
  } = {}) {
    if (!host) return;
    if (!items.length) {
      host.innerHTML = `<div class="se-empty">${esc(emptyText)}</div>`;
      return;
    }
    const maxDev = Math.max(span, ...items.map((x) => Math.abs((Number(x.value) || center) - center)));
    host.innerHTML = `<div class="pas-bar-list">${items.map((it) => {
      const val = Number(it.value) || center;
      const dev = val - center;
      const pct = Math.min(50, (Math.abs(dev) / maxDev) * 50);
      const isBad = val < lowWarn || val > highWarn;
      const color = isBad ? '#ef4444' : (dev < 0 ? '#f59e0b' : '#38bdf8');
      const leftPos = dev < 0 ? (50 - pct) : 50;
      const labelHtml = it.device
        ? `<a class="pas-clickable" data-pas-device="${esc(it.device)}" title="打开 ${esc(it.device)} 360° 全景档案">${esc(it.label)}</a>`
        : `<span>${esc(it.label)}</span>`;
      const sign = dev >= 0 ? '+' : '';
      return `<div class="pas-bar-row" data-bar-tip="${esc(`<strong>${it.label}</strong><br>${val.toFixed(4)} ${unit}（偏差 ${sign}${(dev * 100).toFixed(2)}%）${it.sub ? `<br>${it.sub}` : ''}`)}">
        <div class="pas-bar-label">${labelHtml}</div>
        <div class="pas-bar-track pas-div-track">
          <span class="pas-div-zero"></span>
          <span class="pas-bar-fill" style="position:absolute;left:${leftPos.toFixed(1)}%;width:${Math.max(2, pct).toFixed(1)}%;background:${color}"></span>
        </div>
        <div class="pas-bar-val tabular ${isBad ? 'bad' : ''}">${val.toFixed(4)} ${esc(unit)}</div>
      </div>`;
    }).join('')}</div>`;

    host.querySelectorAll('.pas-bar-row').forEach((row) => {
      bindSvgTip(row, () => row.dataset.barTip);
    });
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
      const sbModeNow = getSidebarMode();
      const sbHiddenNow = sbModeNow === 'docked' ? getSidebarHidden() : !document.documentElement.classList.contains('pas-sidebar-open');
      const actions = [
        { title: '设置南极环境气象工况（辐照 / 风速 / 气温 / 暴风雪）', tag: '气象', run: () => openWeatherModal() },
        { title: sbModeNow === 'float' ? '切换左栏模式：改为内嵌固定' : '切换左栏模式：改为边缘悬浮', tag: '左栏', run: () => { setSidebarMode(sbModeNow === 'float' ? 'docked' : 'float'); closeOverlay(); } },
        { title: sbHiddenNow ? '显示左侧导航栏' : '隐藏左侧导航栏', tag: '左栏', run: () => { setSidebarHidden(!sbHiddenNow); closeOverlay(); } },
        { title: '打开历史断面 A/B 对比 (LF / CA / SE)', tag: '操作', run: () => openDiffModal() },
        { title: '导出 SE→LF→CA 综合分析快照报告 (HTML)', tag: '报告', run: () => { closeOverlay(); window.open('/api/report/snapshot', '_blank'); } },
        { title: '查看数据源健康体检与工作目录', tag: '诊断', run: () => { window.location.href = '/settings.html?tab=datasource'; } },
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

  /* ==================== 7. 全局事件、左栏双模式（悬浮/内嵌+均可隐藏）、大屏投放模式与快捷工具条 ==================== */
  const SB_MODE_KEY = 'pas_sidebar_mode'; // 'float' | 'docked'
  const SB_HIDDEN_KEY = 'pas_sidebar_hidden'; // '0' | '1'
  let _wallClockTimer = null;
  let _sbApi = null;

  function getSidebarMode() {
    try {
      const v = localStorage.getItem(SB_MODE_KEY);
      return v === 'docked' ? 'docked' : 'float';
    } catch {
      return 'float';
    }
  }

  function getSidebarHidden() {
    try {
      return localStorage.getItem(SB_HIDDEN_KEY) === '1';
    } catch {
      return false;
    }
  }

  function applySidebarRootClasses(mode, hidden) {
    const root = document.documentElement;
    root.classList.add('pas-sb-managed');
    root.classList.toggle('pas-sb-float', mode === 'float');
    root.classList.toggle('pas-sb-docked', mode === 'docked');
    root.classList.toggle('pas-sb-hidden', mode === 'docked' && Boolean(hidden));
  }

  // 首屏 <head> 阶段同步挂载状态类，杜绝首帧左栏闪现或跳动
  applySidebarRootClasses(getSidebarMode(), getSidebarHidden());

  function sbText(key) {
    const lang = getLang();
    const dict = {
      'zh-CN': {
        to_docked: '切换为内嵌模式（固定占栏）',
        to_float: '切换为悬浮模式（靠左滑出）',
        hide: '隐藏左栏',
        edge_float: '移至此处悬浮展开导航栏',
        edge_docked: '点击展开左侧导航栏',
      },
      'en-US': {
        to_docked: 'Switch to Docked Sidebar',
        to_float: 'Switch to Floating Sidebar',
        hide: 'Hide Sidebar',
        edge_float: 'Hover to peek navigation',
        edge_docked: 'Click to expand sidebar',
      },
      'ru-RU': {
        to_docked: 'Закрепить панель (встроенная)',
        to_float: 'Плавающая панель (по наведению)',
        hide: 'Скрыть панель',
        edge_float: 'Наведите для показа меню',
        edge_docked: 'Нажмите для показа меню',
      },
    };
    return (dict[lang] || dict['zh-CN'])[key] || key;
  }

  function setSidebarMode(nextMode) {
    const mode = nextMode === 'docked' ? 'docked' : 'float';
    try { localStorage.setItem(SB_MODE_KEY, mode); } catch { /* ignore */ }
    if (mode === 'docked') {
      // 切到内嵌时默认展开，方便立即看到切换反馈
      try { localStorage.setItem(SB_HIDDEN_KEY, '0'); } catch { /* ignore */ }
    }
    if (_sbApi) _sbApi.sync({ mode, hidden: mode === 'docked' ? false : true, triggerResize: true });
    else applySidebarRootClasses(mode, mode === 'float');
  }

  function setSidebarHidden(hidden) {
    const isHide = Boolean(hidden);
    const mode = getSidebarMode();
    if (mode === 'docked') {
      try { localStorage.setItem(SB_HIDDEN_KEY, isHide ? '1' : '0'); } catch { /* ignore */ }
      if (_sbApi) _sbApi.sync({ mode: 'docked', hidden: isHide, triggerResize: true });
      else applySidebarRootClasses('docked', isHide);
    } else if (_sbApi) {
      if (isHide) _sbApi.hideFloatNow();
      else _sbApi.showFloatNow();
    }
  }

  /**
   * 将顶栏无损提升至 .app-shell 顶部全宽通栏，并将 .sidebar 与 <main> 归入下方 .pas-shell-body，
   * 确保左侧栏无论悬浮或内嵌均严格位于顶栏之下、绝不遮挡或挤压顶栏。
   */
  function promoteTopbarAboveSidebar() {
    const shell = document.querySelector('.app-shell');
    if (!shell || shell.dataset.pasTopbarPromoted === '1') return shell?.querySelector(':scope > .se-topbar, :scope > .topbar') || null;
    const sidebar = shell.querySelector(':scope > .sidebar');
    const main = shell.querySelector(':scope > .main, :scope > main');
    const topbar = main?.querySelector(':scope > .se-topbar, :scope > .topbar');
    if (!sidebar || !main || !topbar) return topbar || null;

    shell.dataset.pasTopbarPromoted = '1';
    shell.classList.add('pas-topbar-first');

    const bodyWrap = document.createElement('div');
    bodyWrap.className = 'pas-shell-body';

    // 将顶栏移至 .app-shell 最顶部，其余原有子节点（sidebar / resizer / main）整体归入下方 .pas-shell-body
    const rest = Array.from(shell.children);
    shell.insertBefore(topbar, shell.firstChild);
    shell.appendChild(bodyWrap);
    rest.forEach((child) => {
      if (child !== topbar && child !== bodyWrap) bodyWrap.appendChild(child);
    });

    const syncTopbarHeight = () => {
      const h = Math.round(topbar.getBoundingClientRect().height);
      if (h > 0) document.documentElement.style.setProperty('--pas-topbar-h', `${h}px`);
    };
    syncTopbarHeight();
    if (typeof ResizeObserver !== 'undefined') {
      const ro = new ResizeObserver(() => requestAnimationFrame(syncTopbarHeight));
      ro.observe(topbar);
    }
    window.addEventListener('resize', syncTopbarHeight);
    return topbar;
  }

  /**
   * 左侧导航栏双模式控制器：
   * - 悬浮模式（默认）：默认隐藏使主内容满屏，鼠标移至顶栏下方左边框附近悬浮滑出，离开自动隐藏，亦支持手动一键隐藏；
   * - 内嵌模式：固定于顶栏下方左侧，支持一键隐藏使主内容满屏、点击左缘手柄重新展开，亦可一键切回悬浮。
   */
  function initSidebarController() {
    const topbar = promoteTopbarAboveSidebar();
    const sidebar = document.querySelector('.app-shell .sidebar');
    if (!sidebar || sidebar.dataset.pasSbBound === '1') return;
    sidebar.dataset.pasSbBound = '1';

    let hotzone = document.querySelector('.pas-edge-hotzone');
    if (!hotzone) {
      hotzone = document.createElement('div');
      hotzone.className = 'pas-edge-hotzone';
      hotzone.setAttribute('aria-hidden', 'true');
      document.body.appendChild(hotzone);
    }

    // 在 .sidebar .brand 右侧挂载模式切换（悬浮⇄内嵌）与隐藏双图标按钮
    const brand = sidebar.querySelector('.brand');
    let btnMode = null;
    let btnHide = null;
    if (brand && !brand.querySelector('.pas-sb-tools')) {
      const tools = document.createElement('div');
      tools.className = 'pas-sb-tools';
      tools.innerHTML = `
        <button type="button" class="pas-sb-icon-btn" id="pas-sb-mode-btn" aria-label="Sidebar Mode"></button>
        <button type="button" class="pas-sb-icon-btn" id="pas-sb-hide-btn" aria-label="Hide Sidebar">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"/><path d="M19 4v16"/></svg>
        </button>`;
      brand.appendChild(tools);
      btnMode = tools.querySelector('#pas-sb-mode-btn');
      btnHide = tools.querySelector('#pas-sb-hide-btn');
    }

    const SVG_PIN = '<svg width="13.5" height="13.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><line x1="9" y1="4" x2="9" y2="20"/></svg>';
    const SVG_FLOAT = '<svg width="13.5" height="13.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2" stroke-dasharray="3 2"/><rect x="5" y="6" width="6" height="12" rx="1" fill="currentColor" fill-opacity="0.22"/></svg>';

    let hideTimer = null;
    let isPeeking = false;
    let suppressEdgeUntil = 0;
    const TRIGGER_X = 14;
    const HIDE_DELAY_MS = 220;

    const isEffectiveFloat = () => getSidebarMode() === 'float' || document.body.classList.contains('pas-wall-mode');

    const cancelHide = () => {
      if (hideTimer) {
        clearTimeout(hideTimer);
        hideTimer = null;
      }
    };

    const showFloat = () => {
      if (!isEffectiveFloat()) return;
      cancelHide();
      if (isPeeking) return;
      isPeeking = true;
      sidebar.classList.remove('is-collapsed');
      sidebar.classList.add('is-peek');
      document.documentElement.classList.add('pas-sidebar-open');
    };

    const hideFloatImmediate = () => {
      cancelHide();
      isPeeking = false;
      sidebar.classList.remove('is-peek');
      document.documentElement.classList.remove('pas-sidebar-open');
    };

    const scheduleHideFloat = (delay = HIDE_DELAY_MS) => {
      if (!isEffectiveFloat()) return;
      cancelHide();
      hideTimer = setTimeout(() => {
        hideTimer = null;
        if (!isPeeking || !isEffectiveFloat()) return;
        isPeeking = false;
        sidebar.classList.remove('is-peek');
        document.documentElement.classList.remove('pas-sidebar-open');
      }, delay);
    };

    const refreshButtons = () => {
      const mode = getSidebarMode();
      const effFloat = isEffectiveFloat();
      if (btnMode) {
        const isDocked = mode === 'docked';
        btnMode.innerHTML = isDocked ? SVG_FLOAT : SVG_PIN;
        btnMode.classList.toggle('is-active', isDocked);
        btnMode.title = sbText(isDocked ? 'to_float' : 'to_docked');
      }
      if (btnHide) {
        btnHide.title = sbText('hide');
      }
      hotzone.title = sbText(effFloat ? 'edge_float' : 'edge_docked');
    };

    const sync = ({ mode = getSidebarMode(), hidden = getSidebarHidden(), triggerResize = false } = {}) => {
      cancelHide();
      applySidebarRootClasses(mode, hidden);
      sidebar.classList.remove('is-collapsed');
      if (mode === 'docked' && !document.body.classList.contains('pas-wall-mode')) {
        isPeeking = false;
        sidebar.classList.remove('is-peek');
        document.documentElement.classList.remove('pas-sidebar-open');
      } else {
        hideFloatImmediate();
      }
      refreshButtons();
      if (triggerResize) {
        setTimeout(() => window.dispatchEvent(new Event('resize')), 40);
        setTimeout(() => window.dispatchEvent(new Event('resize')), 240);
      }
    };

    _sbApi = {
      sync,
      showFloatNow: showFloat,
      hideFloatNow: () => {
        suppressEdgeUntil = Date.now() + 450;
        hideFloatImmediate();
      },
      refreshButtons,
    };

    if (btnMode) {
      btnMode.addEventListener('click', (e) => {
        e.stopPropagation();
        const next = getSidebarMode() === 'float' ? 'docked' : 'float';
        setSidebarMode(next);
      });
    }
    if (btnHide) {
      btnHide.addEventListener('click', (e) => {
        e.stopPropagation();
        if (isEffectiveFloat()) {
          suppressEdgeUntil = Date.now() + 450;
          hideFloatImmediate();
        } else {
          setSidebarHidden(true);
        }
      });
    }

    hotzone.addEventListener('mouseenter', () => {
      if (isEffectiveFloat() && Date.now() >= suppressEdgeUntil) showFloat();
    });
    hotzone.addEventListener('click', () => {
      if (isEffectiveFloat()) {
        showFloat();
      } else if (getSidebarHidden()) {
        setSidebarHidden(false);
      }
    });

    sidebar.addEventListener('mouseenter', () => {
      if (isEffectiveFloat()) showFloat();
    });
    sidebar.addEventListener('mouseleave', () => {
      if (isEffectiveFloat()) scheduleHideFloat();
    });
    sidebar.addEventListener('focusin', () => {
      if (isEffectiveFloat()) showFloat();
    });
    sidebar.addEventListener('focusout', (e) => {
      if (isEffectiveFloat() && !sidebar.contains(e.relatedTarget)) scheduleHideFloat(160);
    });

    const getTopbarBottom = () => (topbar ? Math.round(topbar.getBoundingClientRect().bottom) : 0);

    document.addEventListener('mousemove', (e) => {
      if (!isEffectiveFloat()) return;
      const tbBottom = getTopbarBottom();
      if (e.clientX <= TRIGGER_X && e.clientY >= tbBottom) {
        if (Date.now() >= suppressEdgeUntil) showFloat();
        return;
      }
      if (isPeeking) {
        const rect = sidebar.getBoundingClientRect();
        if (e.clientY >= tbBottom && e.clientX <= rect.right + 10) {
          cancelHide();
        } else if (!hideTimer) {
          scheduleHideFloat();
        }
      }
    }, { passive: true });

    document.addEventListener('mouseleave', () => {
      if (isEffectiveFloat() && isPeeking) scheduleHideFloat(120);
    });

    const langSel = document.getElementById('lang-select');
    if (langSel && !langSel.dataset.pasSbLangBound) {
      langSel.dataset.pasSbLangBound = '1';
      langSel.addEventListener('change', refreshButtons);
    }

    sync({ mode: getSidebarMode(), hidden: getSidebarHidden(), triggerResize: false });
  }

  function wallBtnText(isFull) {
    const lang = getLang();
    if (lang === 'en-US') return isFull ? 'Exit Fullscreen' : 'Fullscreen';
    if (lang === 'ru-RU') return isFull ? 'Выйти из полного экрана' : 'Полный экран';
    return isFull ? '退出全屏' : '全屏显示';
  }

  const WALL_ICO_MAX = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>';
  const WALL_ICO_MIN = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 14h6v6M20 10h-6V4M14 10l7-7M10 14l-7 7"/></svg>';

  function getFullscreenEl() {
    return document.fullscreenElement || document.webkitFullscreenElement || null;
  }

  function isWallCapablePage() {
    const page = document.body?.dataset?.page || '';
    return ['/se-main', '/lf-main', '/ca-main'].includes(page) || document.body?.dataset?.wallReady === '1';
  }

  function syncFullscreenBtnUI(active) {
    const btn = document.getElementById('btn-wall-mode');
    if (!btn) return;
    btn.classList.toggle('active', active);
    const tip = `${wallBtnText(active)} (F)`;
    btn.title = tip;
    btn.setAttribute('aria-label', tip);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    btn.innerHTML = `<span class="pas-btn-ico">${active ? WALL_ICO_MIN : WALL_ICO_MAX}</span>`;
  }

  function setWallMode(enable, { syncFullscreen = true } = {}) {
    const active = Boolean(enable);
    const wallCapable = isWallCapablePage();
    if (wallCapable) {
      document.body.classList.toggle('pas-wall-mode', active);
      try { localStorage.setItem('pas_wall_mode', active ? '1' : '0'); } catch { /* ignore */ }
    }
    document.documentElement.classList.toggle('pas-sb-wall', active);
    if (_sbApi) _sbApi.sync({ mode: getSidebarMode(), hidden: getSidebarHidden(), triggerResize: false });
    syncFullscreenBtnUI(active);
    if (syncFullscreen) {
      try {
        const fsEl = getFullscreenEl();
        const root = document.documentElement;
        if (active && !fsEl) {
          const req = root.requestFullscreen || root.webkitRequestFullscreen;
          if (req) Promise.resolve(req.call(root)).catch(() => {});
        } else if (!active && fsEl) {
          const exit = document.exitFullscreen || document.webkitExitFullscreen;
          if (exit) Promise.resolve(exit.call(document)).catch(() => {});
        }
      } catch { /* ignore */ }
    }
    // 触发所有自适应 SVG 图表与顶栏居中徽牌重新计算宽高
    setTimeout(() => window.dispatchEvent(new Event('resize')), 60);
    setTimeout(() => window.dispatchEvent(new Event('resize')), 260);
  }

  function initWallMode() {
    const isMainScreen = isWallCapablePage();
    const topActions = document.querySelector('.se-top-actions, .top-actions');
    const titleRow = document.querySelector('.se-title-row');

    // 1. 仅在核心态势主画面注入实时呼吸状态灯 + 大屏电子时钟
    if (isMainScreen && titleRow && !document.getElementById('pas-live-dot')) {
      const dot = document.createElement('span');
      dot.id = 'pas-live-dot';
      dot.className = 'pas-live-dot';
      dot.title = '实时在线监控';
      titleRow.insertBefore(dot, titleRow.firstChild);
    }
    if (isMainScreen && topActions && !document.getElementById('pas-wall-clock')) {
      const clk = document.createElement('span');
      clk.id = 'pas-wall-clock';
      clk.className = 'pas-wall-clock tabular';
      topActions.insertBefore(clk, topActions.firstChild);
      const tick = () => {
        const d = new Date();
        const p = (n) => String(n).padStart(2, '0');
        clk.textContent = `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
      };
      tick();
      if (_wallClockTimer) clearInterval(_wallClockTimer);
      _wallClockTimer = setInterval(tick, 1000);
    }

    // 2. 全站所有页面顶栏最右侧统一注入「全屏显示 / 退出全屏」纯图标按钮
    if (topActions && !document.getElementById('btn-wall-mode')) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.id = 'btn-wall-mode';
      btn.className = topActions.classList.contains('se-top-actions')
        ? 'se-chip-btn pas-wall-btn pas-icon-only'
        : 'pas-kbd-btn pas-wall-btn pas-icon-only';
      btn.addEventListener('click', () => {
        const currentlyActive = Boolean(getFullscreenEl()) || document.documentElement.classList.contains('pas-sb-wall') || document.body.classList.contains('pas-wall-mode');
        setWallMode(!currentlyActive, { syncFullscreen: true });
      });
      topActions.appendChild(btn);
      syncFullscreenBtnUI(Boolean(getFullscreenEl()));
    }

    // 监听语言切换更新全屏按钮三语提示
    const langSel = document.getElementById('lang-select');
    if (langSel && !langSel.dataset.pasWallLangBound) {
      langSel.dataset.pasWallLangBound = '1';
      langSel.addEventListener('change', () => {
        const active = Boolean(getFullscreenEl()) || document.documentElement.classList.contains('pas-sb-wall') || document.body.classList.contains('pas-wall-mode');
        setTimeout(() => syncFullscreenBtnUI(active), 0);
      });
    }

    // 浏览器原生进入/退出全屏（如按 Esc / F11）时实时同步图标与页面状态
    if (!document.documentElement.dataset.pasFsChangeBound) {
      document.documentElement.dataset.pasFsChangeBound = '1';
      const onFsChange = () => {
        const inFs = Boolean(getFullscreenEl());
        if (!inFs && (document.body.classList.contains('pas-wall-mode') || document.documentElement.classList.contains('pas-sb-wall'))) {
          setWallMode(false, { syncFullscreen: false });
        } else if (inFs) {
          syncFullscreenBtnUI(true);
          setTimeout(() => window.dispatchEvent(new Event('resize')), 80);
        }
      };
      document.addEventListener('fullscreenchange', onFsChange);
      document.addEventListener('webkitfullscreenchange', onFsChange);
    }

    // 若 URL 显式带 ?wall=1 则默认以大屏布局打开（不强制弹窗请求 fullscreen）
    if (isMainScreen && new URLSearchParams(window.location.search).get('wall') === '1') {
      setWallMode(true, { syncFullscreen: false });
    }
  }

  /* ==================== 7.2 全站统一多级可折叠树形导航目录（无分析功能/运行管理冗余层级） ==================== */
  const NAV_TREE_KEY = 'pas_nav_tree_open';
  const NAV_ICONS = {
    overview: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
    se: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 20 9 4 6 12 2 12"/></svg>',
    lf: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    ca: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    runs: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 15"/></svg>',
    settings: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.6.85 1 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    folder: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
    chevron: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>',
  };

  const NAV_TREE_SPEC = [
    { id: 'overview', icon: 'overview', href: '/overview.html', label: { 'zh-CN': '总览', 'en-US': 'Overview', 'ru-RU': 'Обзор' } },
    {
      id: 'se',
      icon: 'se',
      href: '/se-main.html',
      label: { 'zh-CN': '状态估计 SE', 'en-US': 'State Estimation SE', 'ru-RU': 'Оценка сост. SE' },
      children: [
        { id: 'se-main', href: '/se-main.html', label: { 'zh-CN': '主画面', 'en-US': 'Dashboard', 'ru-RU': 'Главная' } },
        { id: 'se-flow', href: '/se-flow.html', label: { 'zh-CN': '潮流图', 'en-US': 'Topology', 'ru-RU': 'Схема' } },
        { id: 'se-curves', href: '/se-curves.html', label: { 'zh-CN': '历史曲线', 'en-US': 'Curves', 'ru-RU': 'Графики' } },
        {
          id: 'se-meas-group',
          icon: 'folder',
          label: { 'zh-CN': '量测管理', 'en-US': 'Measurements', 'ru-RU': 'Измерения' },
          children: [
            { id: 'se-measurements', href: '/se-measurements.html', label: { 'zh-CN': '全量测分析', 'en-US': 'All Measurements', 'ru-RU': 'Все измерения' } },
            { id: 'se-prefilter', href: '/se-prefilter.html', label: { 'zh-CN': '预过滤量测', 'en-US': 'Pre-filter', 'ru-RU': 'Фильтрация' } },
            { id: 'se-pseudo', href: '/se-pseudo.html', label: { 'zh-CN': '伪量测', 'en-US': 'Pseudo Meas', 'ru-RU': 'Псевдоизм.' } },
            { id: 'se-bad', href: '/se-bad.html', label: { 'zh-CN': '坏量测', 'en-US': 'Bad Data', 'ru-RU': 'Плохие данные' } },
          ],
        },
        { id: 'se-params', href: '/se-params.html', label: { 'zh-CN': '算法参数', 'en-US': 'Parameters', 'ru-RU': 'Параметры' } },
        { id: 'se-logs', href: '/se-logs.html', label: { 'zh-CN': '运行日志', 'en-US': 'Logs', 'ru-RU': 'Журнал' } },
      ],
    },
    {
      id: 'lf',
      icon: 'lf',
      href: '/lf-main.html',
      label: { 'zh-CN': '潮流分析 LF', 'en-US': 'Load Flow LF', 'ru-RU': 'Потоки LF' },
      children: [
        { id: 'lf-main', href: '/lf-main.html', label: { 'zh-CN': '主画面', 'en-US': 'Dashboard', 'ru-RU': 'Главная' } },
        { id: 'lf-flow', href: '/lf-flow.html', label: { 'zh-CN': '潮流图', 'en-US': 'Flow Map', 'ru-RU': 'Схема потоков' } },
        { id: 'lf-results', href: '/lf-results.html', label: { 'zh-CN': '潮流明细', 'en-US': 'Results', 'ru-RU': 'Результаты' } },
        { id: 'lf-params', href: '/lf-params.html', label: { 'zh-CN': '参数与方式', 'en-US': 'Params & Study', 'ru-RU': 'Параметры' } },
        { id: 'lf-logs', href: '/lf-logs.html', label: { 'zh-CN': '运行日志', 'en-US': 'Logs', 'ru-RU': 'Журнал' } },
      ],
    },
    {
      id: 'ca',
      icon: 'ca',
      href: '/ca-main.html',
      label: { 'zh-CN': '静态安全 CA', 'en-US': 'Security CA', 'ru-RU': 'Надежность CA' },
      children: [
        { id: 'ca-main', href: '/ca-main.html', label: { 'zh-CN': '主画面', 'en-US': 'Dashboard', 'ru-RU': 'Главная' } },
        { id: 'ca-risks', href: '/ca-risks.html', label: { 'zh-CN': '风险与图谱', 'en-US': 'Risks & Map', 'ru-RU': 'Риски и схема' } },
        { id: 'ca-contingencies', href: '/ca-contingencies.html', label: { 'zh-CN': '预想故障集', 'en-US': 'Contingencies', 'ru-RU': 'Сценарии N-1' } },
        { id: 'ca-config', href: '/ca-config.html', label: { 'zh-CN': '参数与限值', 'en-US': 'Params & Limits', 'ru-RU': 'Параметры' } },
        { id: 'ca-logs', href: '/ca-logs.html', label: { 'zh-CN': '运行日志', 'en-US': 'Logs', 'ru-RU': 'Журнал' } },
      ],
    },
    { sep: true },
    { id: 'runs', icon: 'runs', href: '/runs.html', label: { 'zh-CN': '运行历史', 'en-US': 'Run History', 'ru-RU': 'История' } },
    {
      id: 'settings',
      icon: 'settings',
      href: '/settings.html',
      label: { 'zh-CN': '系统设置', 'en-US': 'Settings', 'ru-RU': 'Настройки' },
      children: [
        { id: 'settings-schedule', href: '/settings.html?tab=schedule', label: { 'zh-CN': '调度参数', 'en-US': 'Schedules', 'ru-RU': 'Расписание' } },
        { id: 'settings-datasource', href: '/settings.html?tab=datasource', label: { 'zh-CN': '数据源与目录', 'en-US': 'Data Sources', 'ru-RU': 'Источники' } },
        { id: 'settings-database', href: '/settings.html?tab=database', label: { 'zh-CN': '数据库状态', 'en-US': 'Database', 'ru-RU': 'База данных' } },
        { id: 'settings-logs', href: '/settings.html?tab=logs', label: { 'zh-CN': '系统日志', 'en-US': 'System Logs', 'ru-RU': 'Сист. журнал' } },
      ],
    },
  ];

  function loadNavOpenMap() {
    try {
      const raw = JSON.parse(localStorage.getItem(NAV_TREE_KEY) || '{}');
      return (raw && typeof raw === 'object') ? raw : {};
    } catch {
      return {};
    }
  }

  function saveNavOpenMap(map) {
    try { localStorage.setItem(NAV_TREE_KEY, JSON.stringify(map)); } catch { /* ignore */ }
  }

  function matchNavHref(href) {
    if (!href) return false;
    const curPath = window.location.pathname || '/overview.html';
    const curTab = new URLSearchParams(window.location.search).get('tab') || '';
    const [hPath, hQuery] = href.split('?');
    if (hPath === '/overview.html' && (curPath === '/' || curPath === '/index.html')) return true;
    if (curPath !== hPath) return false;
    if (hQuery) {
      const targetTab = new URLSearchParams(hQuery).get('tab') || '';
      return curTab ? curTab === targetTab : targetTab === 'schedule';
    }
    return true;
  }

  function renderSidebarTree() {
    const nav = document.querySelector('.sidebar > nav');
    if (!nav) return;
    const lang = getLang();
    const openMap = loadNavOpenMap();
    const tLbl = (node) => (node.label && (node.label[lang] || node.label['zh-CN'])) || '';

    const hasActiveDesc = (node) => {
      if (!node.children) return matchNavHref(node.href);
      return node.children.some((ch) => hasActiveDesc(ch));
    };

    // 确保当前所在页面的所有祖先分支自动处于展开状态
    const ensureOpenForActive = (nodes) => {
      nodes.forEach((n) => {
        if (n.children) {
          const activeInside = hasActiveDesc(n);
          if (activeInside && openMap[n.id] !== true) openMap[n.id] = true;
          ensureOpenForActive(n.children);
        }
      });
    };
    ensureOpenForActive(NAV_TREE_SPEC);

    const buildNodes = (nodes, depth) => nodes.map((node) => {
      if (node.sep) return '<div class="pas-tree-sep" role="separator"></div>';
      const hasKids = Array.isArray(node.children) && node.children.length > 0;
      const isOpen = hasKids ? Boolean(openMap[node.id]) : false;
      const isActiveLeaf = !hasKids && matchNavHref(node.href);
      const isAncestor = hasKids && hasActiveDesc(node);
      const icoHtml = node.icon && NAV_ICONS[node.icon] ? `<span class="pas-tree-ico">${NAV_ICONS[node.icon]}</span>` : '';

      if (hasKids) {
        const labelEl = node.href
          ? `<a class="pas-tree-link" href="${esc(node.href)}">${icoHtml}<span class="pas-tree-lbl">${esc(tLbl(node))}</span></a>`
          : `<button type="button" class="pas-tree-link pas-tree-folder-btn" data-tree-toggle="${esc(node.id)}">${icoHtml}<span class="pas-tree-lbl">${esc(tLbl(node))}</span></button>`;
        return `<div class="pas-tree-branch depth-${depth}${isOpen ? ' is-open' : ''}${isAncestor ? ' has-active' : ''}" data-tree-id="${esc(node.id)}">
          <div class="pas-tree-row">
            ${labelEl}
            <button type="button" class="pas-tree-chevron" data-tree-toggle="${esc(node.id)}" aria-expanded="${isOpen ? 'true' : 'false'}" aria-label="展开/折叠">${NAV_ICONS.chevron}</button>
          </div>
          <div class="pas-tree-children"${isOpen ? '' : ' hidden'}>${buildNodes(node.children, depth + 1)}</div>
        </div>`;
      }
      return `<a class="pas-tree-leaf depth-${depth}${isActiveLeaf ? ' active' : ''}" href="${esc(node.href)}">${icoHtml}<span class="pas-tree-lbl">${esc(tLbl(node))}</span></a>`;
    }).join('');

    nav.className = 'pas-tree';
    nav.innerHTML = buildNodes(NAV_TREE_SPEC, 1);

    nav.querySelectorAll('[data-tree-toggle]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const id = btn.dataset.treeToggle;
        const branch = nav.querySelector(`.pas-tree-branch[data-tree-id="${CSS.escape(id)}"]`);
        if (!branch) return;
        const nextOpen = !branch.classList.contains('is-open');
        branch.classList.toggle('is-open', nextOpen);
        const kids = branch.querySelector(':scope > .pas-tree-children');
        if (kids) kids.hidden = !nextOpen;
        const chev = branch.querySelector(':scope > .pas-tree-row > .pas-tree-chevron');
        if (chev) chev.setAttribute('aria-expanded', nextOpen ? 'true' : 'false');
        const map = loadNavOpenMap();
        map[id] = nextOpen;
        saveNavOpenMap(map);
      });
    });

    // 语言切换时同步刷新目录树文案
    const langSel = document.getElementById('lang-select');
    if (langSel && !langSel.dataset.pasTreeLangBound) {
      langSel.dataset.pasTreeLangBound = '1';
      langSel.addEventListener('change', () => setTimeout(renderSidebarTree, 0));
    }
  }

  /* ==================== 7.5 南极极地气象与环境工况胶囊条 + 快捷输入弹窗 ==================== */
  let _cachedWeather = null;
  let _weatherFetchInFlight = null;

  function weatherRegimeIcon(regime, icing) {
    if (icing >= 3 || regime === 'blizzard') return '❄️';
    if (regime === 'katabatic') return '💨';
    if (regime === 'polar_night') return '🌙';
    if (regime === 'polar_day') return '☀️';
    if (regime === 'extreme_cold') return '🥶';
    return '🌬️';
  }

  function weatherAlertTone(alertLevel) {
    if (alertLevel === 'extreme') return 'bad';
    if (alertLevel === 'warning') return 'warn';
    if (alertLevel === 'advisory') return 'accent';
    return 'ok';
  }

  async function fetchWeatherState(force = false) {
    if (_cachedWeather && !force) return _cachedWeather;
    if (_weatherFetchInFlight && !force) return _weatherFetchInFlight;
    _weatherFetchInFlight = fetch('/api/weather/current')
      .then((r) => r.json())
      .then((j) => {
        if (j && j.ok && j.data) {
          _cachedWeather = j.data;
          updateWeatherBadgeDOM(_cachedWeather);
          return _cachedWeather;
        }
        return _cachedWeather;
      })
      .catch(() => _cachedWeather)
      .finally(() => { _weatherFetchInFlight = null; });
    return _weatherFetchInFlight;
  }

  const WX_SVG_SUN = '<svg class="pas-wx-ico-sun" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>';
  const WX_SVG_WIND = '<svg class="pas-wx-ico-wind" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.7 7.7A2.5 2.5 0 1 1 19 12H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/><path d="M12.6 19.4A2 2 0 1 0 14 16H2"/></svg>';
  const WX_SVG_TEMP = '<svg class="pas-wx-ico-temp" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0Z"/></svg>';

  function updateWeatherBadgeDOM(w) {
    const btn = document.getElementById('pas-weather-pill');
    if (!btn || !w) return;
    const tone = weatherAlertTone(w.alert_level);
    btn.className = `pas-weather-pill tone-${tone}`;
    const c = w.coupling || {};
    const tip = `${w.polar_regime_label || '南极工况'}（${w.alert_label || '—'}）· 吹雪/覆冰：${w.snow_icing_label || '—'}\n` +
      `辐照 ${Math.round(Number(w.irradiance_wm2 || 0))} W/m² · 风速 ${Number(w.wind_speed_ms || 0).toFixed(1)} m/s · 气温 ${Number(w.ambient_temp_c ?? -18.5).toFixed(1)} ℃\n` +
      `理论风电：${c.wind_avail_kw ?? '—'}/${c.wind_rated_kw ?? '—'} kW (${c.wind_avail_pct ?? '—'}%) | 理论光伏：${c.pv_avail_kw ?? '—'}/${c.pv_rated_kw ?? '—'} kW (${c.pv_avail_pct ?? '—'}%)\n` +
      `极寒电池可用率：${c.storage_avail_pct ?? '—'}% | 负荷系数：×${w.load_factor ?? 1.0}\n点击设置/切换南极环境气象工况`;
    btn.title = tip;
    btn.innerHTML = `<span class="pas-w-dot ${tone}"></span>` +
      `<span class="pas-w-vals tabular"><span class="pas-wx-seg">${WX_SVG_SUN}${Math.round(Number(w.irradiance_wm2 || 0))}</span><span class="pas-wx-seg">${WX_SVG_WIND}${Number(w.wind_speed_ms || 0).toFixed(1)}</span><span class="pas-wx-seg">${WX_SVG_TEMP}${Number(w.ambient_temp_c ?? -18.5).toFixed(0)}°</span></span>` +
      `<span class="pas-w-extra tabular">${WX_SVG_WIND}${Number(c.wind_avail_kw || 0).toFixed(0)}kW · ${WX_SVG_SUN}${Number(c.pv_avail_kw || 0).toFixed(0)}kW</span>`;
  }

  function mountWeatherBadge() {
    // 若页面已有专属南极环境气象耦合条（如 overview.html 的 #ov-weather-strip），顶栏不再重复挂载
    if (document.getElementById('ov-weather-strip')) return;
    const topActions = document.querySelector('.se-top-actions');
    if (!topActions || document.getElementById('pas-weather-pill')) return;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'pas-weather-pill';
    btn.className = 'pas-weather-pill tone-ok';
    btn.innerHTML = '<span class="pas-w-dot ok"></span><span class="pas-w-vals tabular">气象加载中…</span>';
    btn.addEventListener('click', () => openWeatherModal());
    const cmdBtn = document.getElementById('pas-cmd-trigger');
    const wallClk = document.getElementById('pas-wall-clock');
    const anchor = wallClk ? wallClk.nextSibling : (cmdBtn ? cmdBtn.nextSibling : topActions.firstChild);
    topActions.insertBefore(btn, anchor);
    fetchWeatherState(true);
  }

  async function openWeatherModal() {
    closeOverlay();
    const w = (await fetchWeatherState(true)) || {};
    const presets = w.presets || [];
    const c = w.coupling || {};
    const wrap = document.createElement('div');
    wrap.className = 'pas-cmd-backdrop';
    wrap.style.paddingTop = '5vh';
    wrap.innerHTML = `
      <div class="pas-diff-modal pas-weather-modal" role="dialog" aria-label="南极气象与环境工况输入">
        <div class="pas-drawer-head">
          <h3><span>南极极端气象与环境工况输入</span><span class="se-pill ${weatherAlertTone(w.alert_level)}" id="pw-alert-pill">${esc(w.polar_regime_label || '常规南极工况')} · ${esc(w.alert_label || '适宜')}</span></h3>
          <button type="button" class="se-btn compact" id="pw-close">✕</button>
        </div>
        <div class="pas-w-presets" id="pw-presets">
          ${presets.map((p) => `
            <button type="button" class="pas-w-preset-btn ${p.key === w.polar_regime ? 'active' : ''}" data-preset="${esc(p.key)}" title="${esc(p.note || '')}">
              <strong>${weatherRegimeIcon(p.polar_regime, p.snow_icing_level)} ${esc(p.label)}</strong>
              <span class="tabular">${p.irradiance_wm2}W/m² · ${p.wind_speed_ms}m/s · ${p.ambient_temp_c}℃</span>
            </button>`).join('')}
        </div>
        <form id="pw-form" class="pas-w-form">
          <input type="hidden" id="pw-preset-key" value="">
          <label class="se-field"><span>太阳辐照度 (W/m²)</span><input id="pw-irr" class="tabular" type="number" min="0" max="1400" step="any" value="${w.irradiance_wm2 ?? 420}" required></label>
          <label class="se-field"><span>风速 (m/s)</span><input id="pw-wind" class="tabular" type="number" min="0" max="65" step="any" value="${w.wind_speed_ms ?? 9.5}" required></label>
          <label class="se-field"><span>环境气温 (℃)</span><input id="pw-temp" class="tabular" type="number" min="-85" max="30" step="any" value="${w.ambient_temp_c ?? -18.5}" required></label>
          <label class="se-field"><span>大气压强 (hPa)</span><input id="pw-pres" class="tabular" type="number" min="850" max="1060" step="any" value="${w.pressure_hpa ?? 982}"></label>
          <label class="se-field"><span>相对湿度 (%)</span><input id="pw-hum" class="tabular" type="number" min="0" max="100" step="any" value="${w.humidity_pct ?? 58}"></label>
          <label class="se-field"><span>吹雪 / 覆冰等级</span>
            <select id="pw-icing">
              <option value="0" ${Number(w.snow_icing_level) === 0 ? 'selected' : ''}>0 · 晴朗无冰</option>
              <option value="1" ${Number(w.snow_icing_level) === 1 ? 'selected' : ''}>1 · 轻度吹雪</option>
              <option value="2" ${Number(w.snow_icing_level) === 2 ? 'selected' : ''}>2 · 中度覆冰</option>
              <option value="3" ${Number(w.snow_icing_level) === 3 ? 'selected' : ''}>3 · 极端暴风雪</option>
            </select>
          </label>
          <label class="se-field"><span>负荷环境系数 (×)</span><input id="pw-lfac" class="tabular" type="number" min="0.2" max="2.5" step="any" value="${w.load_factor ?? 1.0}"></label>
          <label class="se-field" style="grid-column:span 2"><span>工况备注</span><input id="pw-note" type="text" maxlength="200" value="${esc(w.note || '')}" placeholder="可选备注"></label>
          <div class="pas-w-coupling-bar" id="pw-coupling-bar" style="grid-column:1 / -1">
            <span>理论风电 <strong class="tabular">${c.wind_avail_kw ?? 0} / ${c.wind_rated_kw ?? 0} kW</strong> (${c.wind_avail_pct ?? 0}%)</span>
            <span>理论光伏 <strong class="tabular">${c.pv_avail_kw ?? 0} / ${c.pv_rated_kw ?? 0} kW</strong> (${c.pv_avail_pct ?? 0}%)</span>
            <span>极寒电池可用 <strong class="tabular">${c.storage_avail_pct ?? 100}%</strong></span>
            <span>采暖负荷增量 <strong class="tabular">+${c.cold_heating_delta_pct ?? 0}%</strong></span>
          </div>
          <div class="se-modal-actions" style="grid-column:1 / -1">
            <span id="pw-err" style="margin-right:auto;font-size:12px;color:var(--sem-danger)"></span>
            <button type="button" class="se-btn ghost" id="pw-cancel">取消</button>
            <button type="submit" class="se-btn" data-trigger-ca="0">保存工况</button>
            <button type="submit" class="se-btn primary" data-trigger-ca="1">保存并扫描 CA</button>
          </div>
        </form>
      </div>`;
    wrap.addEventListener('click', (e) => { if (e.target === wrap) closeOverlay(); });
    wrap.querySelector('#pw-close').addEventListener('click', closeOverlay);
    wrap.querySelector('#pw-cancel').addEventListener('click', closeOverlay);
    document.body.appendChild(wrap);
    _activeOverlay = wrap;

    const presetMap = Object.fromEntries(presets.map((p) => [p.key, p]));
    const windRated = Number(c.wind_rated_kw || 151);
    const pvRated = Number(c.pv_rated_kw || 170);
    const updatePreview = () => {
      const g = Math.max(0, Number(wrap.querySelector('#pw-irr')?.value || 0));
      const v = Math.max(0, Number(wrap.querySelector('#pw-wind')?.value || 0));
      const temp = Number(wrap.querySelector('#pw-temp')?.value ?? -18.5);
      const icing = Number(wrap.querySelector('#pw-icing')?.value || 0);
      const iceLoss = [0, 0.06, 0.18, 0.45][icing] || 0;
      const snowLoss = [0, 0.12, 0.35, 0.85][icing] || 0;
      // 近似风功率曲线（3m/s 切入，12m/s 额定，35m/s 切出；含 50kW 主风机 25m/s 切出估算）
      const wRatio = (v < 3 || v >= 35) ? 0 : (v >= 12 ? 1 : Math.max(0, Math.min(1, (v ** 3 - 27) / (1728 - 27)))) * (1 - iceLoss);
      const wEffRatio = (v >= 25 && v < 35) ? wRatio * 0.67 : wRatio;
      const wKw = windRated * wEffRatio;
      const tCell = temp + 0.025 * g;
      const tFac = Math.max(0.3, Math.min(1.18, 1 - 0.004 * (tCell - 25)));
      const pvRatio = g <= 1e-6 ? 0 : Math.max(0, Math.min(1.15, (g / 1000) * tFac * (1 - snowLoss)));
      const pvKw = pvRated * pvRatio;
      const stoPct = temp >= -10 ? 100 : Math.max(50, 100 - (-10 - temp) * 0.85);
      const heatPct = Math.max(0, (-20 - temp) * 0.8);
      const bar = wrap.querySelector('#pw-coupling-bar');
      if (bar) {
        bar.innerHTML = `
          <span>理论风电 <strong class="tabular">${wKw.toFixed(1)} / ${windRated.toFixed(0)} kW</strong> (${(wEffRatio * 100).toFixed(1)}%)</span>
          <span>理论光伏 <strong class="tabular">${pvKw.toFixed(1)} / ${pvRated.toFixed(0)} kW</strong> (${(pvRatio * 100).toFixed(1)}%)</span>
          <span>极寒电池可用 <strong class="tabular">${stoPct.toFixed(1)}%</strong></span>
          <span>采暖负荷增量 <strong class="tabular">+${heatPct.toFixed(1)}%</strong></span>`;
      }
      const alertPill = wrap.querySelector('#pw-alert-pill');
      if (alertPill) {
        let lvl = 'normal'; let lbl = '气象适宜';
        if (icing >= 3 || v >= 32 || temp <= -48 || (g <= 5 && (v < 3 || v >= 30))) { lvl = 'extreme'; lbl = '极端严酷'; }
        else if (icing >= 2 || v >= 24 || temp <= -35 || g <= 5) { lvl = 'warning'; lbl = '气象警戒'; }
        else if (icing === 1 || v < 3 || temp <= -25) { lvl = 'advisory'; lbl = '工况关注'; }
        alertPill.className = `se-pill ${weatherAlertTone(lvl)}`;
        alertPill.textContent = lbl;
      }
    };
    ['#pw-irr', '#pw-wind', '#pw-temp', '#pw-icing'].forEach((sel) => {
      wrap.querySelector(sel)?.addEventListener('input', updatePreview);
      wrap.querySelector(sel)?.addEventListener('change', updatePreview);
    });
    wrap.querySelectorAll('.pas-w-preset-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const p = presetMap[btn.dataset.preset];
        if (!p) return;
        wrap.querySelectorAll('.pas-w-preset-btn').forEach((b) => b.classList.toggle('active', b === btn));
        wrap.querySelector('#pw-preset-key').value = p.key;
        wrap.querySelector('#pw-irr').value = p.irradiance_wm2;
        wrap.querySelector('#pw-wind').value = p.wind_speed_ms;
        wrap.querySelector('#pw-temp').value = p.ambient_temp_c;
        wrap.querySelector('#pw-pres').value = p.pressure_hpa;
        wrap.querySelector('#pw-hum').value = p.humidity_pct;
        wrap.querySelector('#pw-icing').value = String(p.snow_icing_level);
        wrap.querySelector('#pw-lfac').value = p.load_factor;
        wrap.querySelector('#pw-note').value = p.note || '';
        updatePreview();
      });
    });

    let triggerCa = false;
    wrap.querySelectorAll('#pw-form button[type="submit"]').forEach((b) => {
      b.addEventListener('click', () => { triggerCa = b.dataset.triggerCa === '1'; });
    });

    wrap.querySelector('#pw-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const errEl = wrap.querySelector('#pw-err');
      errEl.textContent = '';
      const payload = {
        irradiance_wm2: Number(wrap.querySelector('#pw-irr').value),
        wind_speed_ms: Number(wrap.querySelector('#pw-wind').value),
        ambient_temp_c: Number(wrap.querySelector('#pw-temp').value),
        pressure_hpa: Number(wrap.querySelector('#pw-pres').value),
        humidity_pct: Number(wrap.querySelector('#pw-hum').value),
        snow_icing_level: Number(wrap.querySelector('#pw-icing').value),
        load_factor: Number(wrap.querySelector('#pw-lfac').value),
        note: wrap.querySelector('#pw-note').value.trim(),
        trigger_ca: triggerCa,
      };
      const pk = wrap.querySelector('#pw-preset-key').value;
      if (pk && presetMap[pk]) {
        const pr = presetMap[pk];
        if (
          pr.irradiance_wm2 === payload.irradiance_wm2 &&
          pr.wind_speed_ms === payload.wind_speed_ms &&
          pr.ambient_temp_c === payload.ambient_temp_c &&
          Number(pr.snow_icing_level) === payload.snow_icing_level
        ) {
          payload.polar_regime = pr.polar_regime;
          payload.source = 'preset';
        }
      }
      try {
        const resp = await fetch('/api/weather/current', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const json = await resp.json();
        if (!resp.ok || !json.ok) throw new Error(json.error || `HTTP ${resp.status}`);
        _cachedWeather = json.data;
        updateWeatherBadgeDOM(_cachedWeather);
        window.dispatchEvent(new CustomEvent('pas-weather-updated', { detail: _cachedWeather }));
        closeOverlay();
      } catch (err) {
        errEl.textContent = err.message || '保存失败';
      }
    });
  }

  /* ==================== 7.6 顶栏「外观与语言」紧凑整合弹出面板（全站 26 页统一生效） ==================== */
  const PREFS_SWATCHES = [
    { id: 'ethereal-aurora', bg: '#070b1a', fg: '#67e8f9', zh: '极光仙境 · 琉璃夜', en: 'Ethereal Aurora', ru: 'Эфирное сияние' },
    { id: 'celestial-mist', bg: '#f1f6fd', fg: '#8b5cf6', zh: '云巅琉璃 · 晨雾白', en: 'Celestial Mist', ru: 'Небесный туман' },
    { id: 'sci-fi-cyan', bg: '#070e1e', fg: '#5eead4', zh: '星穹 · 冰湖青', en: 'Astral Cyan', ru: 'Астральный циан' },
    { id: 'sci-fi-purple', bg: '#0d091d', fg: '#c4b5fd', zh: '星穹 · 紫雾澜', en: 'Astral Violet', ru: 'Астральный фиолет' },
    { id: 'warm-paper', bg: '#f6f2e9', fg: '#15803d', zh: '护眼暖纸', en: 'Warm Paper', ru: 'Теплая бумага' },
    { id: 'minimalist-light', bg: '#f6f9fd', fg: '#3b82f6', zh: '极简明亮', en: 'Minimalist Light', ru: 'Светлый минимализм' },
  ];

  const PREFS_I18N = {
    'zh-CN': { title: '外观与语言', lang: '语言', theme: '主题', brand: '顶栏标题' },
    'en-US': { title: 'Appearance & Language', lang: 'Language', theme: 'Theme', brand: 'Banner Title' },
    'ru-RU': { title: 'Тема и язык', lang: 'Язык', theme: 'Тема', brand: 'Заголовок' },
  };

  let _prefsPopoverEl = null;
  let _prefsTriggerEl = null;

  function closePrefsPopover() {
    if (!_prefsPopoverEl) return;
    _prefsPopoverEl.hidden = true;
    if (_prefsTriggerEl) {
      _prefsTriggerEl.classList.remove('active');
      _prefsTriggerEl.setAttribute('aria-expanded', 'false');
    }
  }

  function positionPrefsPopover() {
    if (!_prefsPopoverEl || !_prefsTriggerEl || _prefsPopoverEl.hidden) return;
    const rect = _prefsTriggerEl.getBoundingClientRect();
    const popW = _prefsPopoverEl.offsetWidth || 228;
    const rightGap = Math.max(8, window.innerWidth - rect.right);
    const maxRight = Math.max(8, window.innerWidth - popW - 8);
    _prefsPopoverEl.style.top = `${Math.round(rect.bottom + 6)}px`;
    _prefsPopoverEl.style.right = `${Math.min(rightGap, maxRight)}px`;
  }

  function mountPrefsPopover() {
    const topActions = document.querySelector('.se-top-actions, .top-actions');
    if (!topActions || document.getElementById('pas-prefs-trigger')) return;

    const themeSel = document.getElementById('theme-select');
    const langSel = document.getElementById('lang-select');
    if (!themeSel && !langSel) return;

    // 1. 顶栏紧凑图标按钮（26x25 / 28x28，统一置尾）
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'pas-prefs-trigger';
    btn.className = 'pas-kbd-btn pas-prefs-btn';
    btn.setAttribute('aria-haspopup', 'true');
    btn.setAttribute('aria-expanded', 'false');
    btn.innerHTML =
      '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<circle cx="12" cy="12" r="9"/><path d="M3.6 9h16.8M3.6 15h16.8"/><path d="M12 3a14 14 0 0 0 0 18M12 3a14 14 0 0 1 0 18"/>' +
      '</svg><span class="pas-prefs-dot" aria-hidden="true"></span>';
    topActions.appendChild(btn);

    // 2. 挂在 body 下的轻量定锚浮层，防止任何顶栏 overflow 裁切
    const pop = document.createElement('div');
    pop.id = 'pas-prefs-popover';
    pop.className = 'pas-prefs-popover';
    pop.setAttribute('role', 'dialog');
    pop.hidden = true;
    pop.innerHTML = `
      <div class="pas-prefs-sec" data-prefs-lang-sec>
        <span class="pas-prefs-lbl" data-prefs-lbl="lang">语言</span>
        <div class="pas-prefs-seg" role="radiogroup">
          <button type="button" class="pas-prefs-seg-btn" data-lang-val="zh-CN">中文</button>
          <button type="button" class="pas-prefs-seg-btn" data-lang-val="en-US">EN</button>
          <button type="button" class="pas-prefs-seg-btn" data-lang-val="ru-RU">RU</button>
        </div>
      </div>
      <div class="pas-prefs-sec" data-prefs-theme-sec>
        <span class="pas-prefs-lbl" data-prefs-lbl="theme">主题</span>
        <div class="pas-prefs-theme-slot"></div>
        <div class="pas-prefs-swatches">
          ${PREFS_SWATCHES.map((s) => `<button type="button" class="pas-prefs-swatch" data-theme-val="${s.id}" style="--sw-bg:${s.bg};--sw-fg:${s.fg}" title="${esc(s.zh)}"></button>`).join('')}
        </div>
      </div>
      <div class="pas-prefs-foot">
        <button type="button" class="pas-prefs-brand-btn" id="pas-prefs-brand-btn">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 1 1 3 3L7 19l-4 1 1-4Z"/></svg>
          <span data-prefs-lbl="brand">顶栏标题</span>
        </button>
      </div>
      <div class="pas-prefs-hidden-slot" hidden></div>
    `;
    document.body.appendChild(pop);
    _prefsPopoverEl = pop;
    _prefsTriggerEl = btn;
    pop.querySelector('#pas-prefs-brand-btn')?.addEventListener('click', () => {
      closePrefsPopover();
      openBrandingModal();
    });

    // 迁入原 DOM 节点，完整保留全站各页面已绑定的 change 监听器
    if (themeSel) {
      themeSel.classList.add('pas-prefs-select');
      pop.querySelector('.pas-prefs-theme-slot').appendChild(themeSel);
    } else {
      pop.querySelector('[data-prefs-theme-sec]').hidden = true;
    }
    if (langSel) {
      pop.querySelector('.pas-prefs-hidden-slot').appendChild(langSel);
    } else {
      pop.querySelector('[data-prefs-lang-sec]').hidden = true;
    }

    const syncUI = () => {
      const curLang = (langSel && langSel.value) || getLang();
      const curTheme = document.documentElement.getAttribute('data-theme') || (themeSel && themeSel.value) || 'minimalist-light';
      const dict = PREFS_I18N[curLang] || PREFS_I18N['zh-CN'];
      pop.setAttribute('aria-label', dict.title);
      const lblLang = pop.querySelector('[data-prefs-lbl="lang"]');
      const lblTheme = pop.querySelector('[data-prefs-lbl="theme"]');
      const lblBrand = pop.querySelector('[data-prefs-lbl="brand"]');
      if (lblLang) lblLang.textContent = dict.lang;
      if (lblTheme) lblTheme.textContent = dict.theme;
      if (lblBrand) lblBrand.textContent = dict.brand;

      pop.querySelectorAll('.pas-prefs-seg-btn').forEach((b) => {
        const active = b.dataset.langVal === curLang;
        b.classList.toggle('active', active);
        b.setAttribute('aria-checked', active ? 'true' : 'false');
      });

      const lk = curLang === 'en-US' ? 'en' : (curLang === 'ru-RU' ? 'ru' : 'zh');
      pop.querySelectorAll('.pas-prefs-swatch').forEach((b) => {
        const sw = PREFS_SWATCHES.find((x) => x.id === b.dataset.themeVal);
        if (sw) b.title = sw[lk] || sw.zh;
        b.classList.toggle('active', b.dataset.themeVal === curTheme);
      });

      const themeText = (themeSel && themeSel.selectedOptions && themeSel.selectedOptions[0])
        ? themeSel.selectedOptions[0].textContent.trim()
        : curTheme;
      const langText = curLang === 'en-US' ? 'EN' : (curLang === 'ru-RU' ? 'RU' : '中文');
      btn.title = `${dict.title} · ${themeText} / ${langText}`;
      btn.setAttribute('aria-label', btn.title);
    };

    pop.querySelectorAll('.pas-prefs-seg-btn').forEach((b) => {
      b.addEventListener('click', () => {
        const next = b.dataset.langVal;
        if (!langSel || langSel.value === next) return;
        langSel.value = next;
        langSel.dispatchEvent(new Event('change', { bubbles: true }));
        setTimeout(syncUI, 0);
      });
    });

    pop.querySelectorAll('.pas-prefs-swatch').forEach((b) => {
      b.addEventListener('click', () => {
        const next = b.dataset.themeVal;
        if (window.PAS_APPLY_THEME) {
          window.PAS_APPLY_THEME(next);
        }
        if (themeSel && themeSel.value !== next) {
          themeSel.value = next;
          themeSel.dispatchEvent(new Event('change', { bubbles: true }));
        }
        syncUI();
      });
    });

    if (themeSel) themeSel.addEventListener('change', () => setTimeout(syncUI, 0));
    if (langSel) langSel.addEventListener('change', () => setTimeout(syncUI, 0));
    window.addEventListener('pas:theme-change', syncUI);

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const willOpen = pop.hidden;
      if (willOpen) {
        syncUI();
        pop.hidden = false;
        btn.classList.add('active');
        btn.setAttribute('aria-expanded', 'true');
        positionPrefsPopover();
      } else {
        closePrefsPopover();
      }
    });

    document.addEventListener('click', (e) => {
      if (pop.hidden) return;
      if (pop.contains(e.target) || btn.contains(e.target)) return;
      closePrefsPopover();
    });
    window.addEventListener('resize', positionPrefsPopover);

    // 等待 theme-registry.js / 各页脚本完成初始填充后再刷新一次 tooltip
    syncUI();
    setTimeout(syncUI, 0);
  }

  /* ==================== 7.7 全站高可读性线性矢量图标化增强（兼容三语与动态文案） ==================== */
  const UI_ICONS = {
    refresh: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/></svg>',
    auto: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4"/><circle cx="12" cy="12" r="3"/></svg>',
    pause: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>',
    play: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="6 4 20 12 6 20 6 4"/></svg>',
    zap: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    diff: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="7" height="16" rx="1.5"/><rect x="14" y="4" width="7" height="16" rx="1.5"/><path d="M10 12h4"/></svg>',
    download: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
    funnel: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>',
    radar: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 20.5 8.5 17.5 19 6.5 19 3.5 8.5 12 2"/><circle cx="12" cy="12" r="2.2"/></svg>',
    trend: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 17 9 11 13 15 21 7"/><polyline points="15 7 21 7 21 13"/></svg>',
    shield: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    grid: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
    activity: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    gauge: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 14l4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/></svg>',
    alert: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    layers: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
    clock: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 15"/></svg>',
    sparkle: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3z"/></svg>',
    terminal: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>',
  };

  function pickSemanticIcon(text, key = '') {
    const s = `${key} ${text}`.toLowerCase();
    if (/清洗|meas_flow|漏斗|量测|clean/.test(s)) return UI_ICONS.funnel;
    if (/雷达|radar|画像|质量|health/.test(s)) return UI_ICONS.radar;
    if (/健康|安全|shield|defense|security|合格|score/.test(s)) return UI_ICONS.shield;
    if (/矩阵|matrix|故障|contingenc|扫描|scan/.test(s)) return UI_ICONS.grid;
    if (/趋势|curve|trend|历史|hist/.test(s)) return UI_ICONS.trend;
    if (/能量|sankey|发电|power|流向|energy|hub|潮流|lf/.test(s)) return UI_ICONS.zap;
    if (/电压|负载|load|volt|仪表|分布|v_dist/.test(s)) return UI_ICONS.gauge;
    if (/坏|告警|风险|残差|alert|risk|bad|alarm|越限/.test(s)) return UI_ICONS.alert;
    if (/冗余|收敛|redund|conv|拓扑|layers/.test(s)) return UI_ICONS.layers;
    if (/耗时|迭代|time|elapsed|运行|clock|日志|log/.test(s)) return UI_ICONS.clock;
    if (/排行|top|求解|指标|stat/.test(s)) return UI_ICONS.activity;
    return UI_ICONS.sparkle;
  }

  function convertToIconButton(btn, iconResolver, extraTip = '') {
    if (!btn || btn.dataset.pasIconBtnBound) return;
    btn.dataset.pasIconBtnBound = '1';
    btn.classList.add('pas-icon-only');

    let obs = null;
    const observe = () => {
      if (obs) obs.observe(btn, { childList: true, characterData: true, subtree: true });
    };

    const sync = () => {
      if (obs) obs.disconnect();
      try {
        const srEl = btn.querySelector(':scope > .pas-sr-lbl');
        const icoEl = btn.querySelector(':scope > .pas-btn-ico');
        const rawText = (srEl ? srEl.textContent : btn.textContent || '').trim();
        const i18nKey = btn.getAttribute('data-i18n') || (srEl && srEl.getAttribute('data-i18n')) || '';
        const tip = rawText ? (extraTip ? `${rawText} (${extraTip})` : rawText) : (btn.title || extraTip);
        if (tip && btn.title !== tip) {
          btn.title = tip;
          btn.setAttribute('aria-label', tip);
        }
        const svgHtml = typeof iconResolver === 'function' ? iconResolver(rawText, btn) : iconResolver;
        if (!icoEl || !srEl) {
          if (btn.hasAttribute('data-i18n')) btn.removeAttribute('data-i18n');
          btn.innerHTML = `<span class="pas-btn-ico">${svgHtml}</span><span class="pas-sr-lbl"${i18nKey ? ` data-i18n="${esc(i18nKey)}"` : ''}>${esc(rawText)}</span>`;
          const newIco = btn.querySelector(':scope > .pas-btn-ico');
          if (newIco) newIco.dataset.pasIcoHtml = svgHtml;
        } else if (icoEl.dataset.pasIcoHtml !== svgHtml) {
          icoEl.innerHTML = svgHtml;
          icoEl.dataset.pasIcoHtml = svgHtml;
        }
      } finally {
        if (obs) {
          obs.takeRecords();
          observe();
        }
      }
    };

    obs = new MutationObserver(() => sync());
    sync();
  }

  function enhancePrimaryCtaIcon(btn) {
    if (!btn || btn.dataset.pasCtaIconBound) return;
    btn.dataset.pasCtaIconBound = '1';
    let obs = null;
    const observe = () => {
      if (obs) obs.observe(btn, { childList: true });
    };
    const ensure = () => {
      if (btn.querySelector(':scope > .pas-btn-ico')) return;
      if (obs) obs.disconnect();
      try {
        const txt = (btn.textContent || '').trim();
        const i18nKey = btn.getAttribute('data-i18n') || '';
        if (btn.hasAttribute('data-i18n')) btn.removeAttribute('data-i18n');
        btn.innerHTML = `<span class="pas-btn-ico">${UI_ICONS.zap}</span><span${i18nKey ? ` data-i18n="${esc(i18nKey)}"` : ''}>${esc(txt)}</span>`;
      } finally {
        if (obs) {
          obs.takeRecords();
          observe();
        }
      }
    };
    obs = new MutationObserver(() => ensure());
    ensure();
  }

  function decorateHeroTiles(strip) {
    if (!strip) return;
    strip.querySelectorAll('.pas-hero-tile').forEach((tile) => {
      const lbl = tile.querySelector('.pas-hero-lbl');
      if (!lbl || tile.querySelector('.pas-hero-ico')) return;
      const svg = pickSemanticIcon(lbl.textContent || '');
      const wrap = document.createElement('span');
      wrap.className = 'pas-hero-lbl-wrap';
      const ico = document.createElement('span');
      ico.className = 'pas-hero-ico';
      ico.innerHTML = svg;
      lbl.parentNode.insertBefore(wrap, lbl);
      wrap.appendChild(ico);
      wrap.appendChild(lbl);
    });
  }

  function enhanceVisualIcons() {
    // 1. 顶栏低频/状态按钮转为纯线性图标按钮，释放横向空间并提升视觉识别
    document.querySelectorAll('#btn-refresh, [data-action="refresh"]').forEach((b) => convertToIconButton(b, UI_ICONS.refresh, 'R'));
    const autoBtn = document.getElementById('btn-auto-refresh');
    if (autoBtn) convertToIconButton(autoBtn, UI_ICONS.auto);
    const daemonBtn = document.getElementById('btn-home-toggle-daemon');
    if (daemonBtn) {
      convertToIconButton(daemonBtn, (txt) => (/恢复|继续|启动|resume|start|продолж/i.test(txt) ? UI_ICONS.play : UI_ICONS.pause));
    }
    const diffBtn = document.getElementById('btn-diff');
    if (diffBtn) convertToIconButton(diffBtn, UI_ICONS.diff);
    const exportBtn = document.getElementById('btn-export');
    if (exportBtn) convertToIconButton(exportBtn, UI_ICONS.download);

    // 2. 主执行按钮前置柔光闪电图标
    document.querySelectorAll('#btn-home-start, #btn-run-lf, #btn-run-ca, #btn-run-chain, [data-action="run-all"]').forEach(enhancePrimaryCtaIcon);

    // 3. 分栏面板标题前置柔光语义图标（同级包裹，不破坏 data-i18n）
    document.querySelectorAll('.se-home-panel-head h2').forEach((h2) => {
      if (h2.dataset.pasIcoBound) return;
      h2.dataset.pasIcoBound = '1';
      const svg = pickSemanticIcon(h2.textContent || '', h2.getAttribute('data-i18n') || '');
      const wrap = document.createElement('span');
      wrap.className = 'pas-head-title-wrap';
      const ico = document.createElement('span');
      ico.className = 'pas-panel-ico';
      ico.innerHTML = svg;
      h2.parentNode.insertBefore(wrap, h2);
      wrap.appendChild(ico);
      wrap.appendChild(h2);
    });

    // 4. 顶部 5 格英雄态势卡自动前置语义微图标（支持异步渲染重建）
    document.querySelectorAll('.pas-hero-strip').forEach((strip) => {
      decorateHeroTiles(strip);
      if (!strip.dataset.pasHeroObs) {
        strip.dataset.pasHeroObs = '1';
        const obs = new MutationObserver(() => {
          obs.disconnect();
          try {
            decorateHeroTiles(strip);
          } finally {
            obs.takeRecords();
            obs.observe(strip, { childList: true });
          }
        });
        obs.observe(strip, { childList: true });
      }
    });

    // 5. 底部运行状态条左侧「运行信息」文字替换为精致终端图标
    document.querySelectorAll('.se-home-logbar .se-log-title, .se-home-logbar > strong').forEach((el) => {
      if (el.dataset.pasLogIcoBound) return;
      el.dataset.pasLogIcoBound = '1';
      const txt = (el.textContent || '').trim();
      el.title = txt || '运行信息';
      el.setAttribute('aria-label', el.title);
      if (el.hasAttribute('data-i18n')) el.removeAttribute('data-i18n');
      el.innerHTML = `<span class="pas-ico" style="color:var(--accent)">${UI_ICONS.terminal}</span>`;
    });
  }

  /* ==================== 7.8 顶栏中央仙气科幻光翼主标题徽牌（可定制 + 持久化 + 智能防碰撞） ==================== */
  const BRANDING_STORE_KEY = 'pas_ui_branding';
  const DEFAULT_BRANDING = {
    title: '南极秦岭站综合能量管理系统',
    badge: '秦岭站',
    enabled: true,
    presets: [
      { title: '南极秦岭站综合能量管理系统', badge: '秦岭站' },
      { title: '极地微电网在线分析主控台', badge: 'PAS' },
      { title: '交直流混合微电网能量管理系统', badge: 'EMS' },
    ],
  };

  let _brandingState = null;

  function loadLocalBranding() {
    try {
      const raw = JSON.parse(localStorage.getItem(BRANDING_STORE_KEY) || 'null');
      if (raw && typeof raw === 'object') {
        return {
          ...DEFAULT_BRANDING,
          title: typeof raw.title === 'string' && raw.title.trim() ? raw.title.trim() : DEFAULT_BRANDING.title,
          badge: typeof raw.badge === 'string' ? raw.badge.trim() : DEFAULT_BRANDING.badge,
          enabled: raw.enabled !== false,
        };
      }
    } catch { /* ignore */ }
    return { ...DEFAULT_BRANDING };
  }

  function saveLocalBranding(cfg) {
    try {
      localStorage.setItem(BRANDING_STORE_KEY, JSON.stringify({
        title: cfg.title,
        badge: cfg.badge,
        enabled: cfg.enabled !== false,
      }));
    } catch { /* ignore */ }
  }

  function applyBrandingToDOM(cfg) {
    _brandingState = { ...DEFAULT_BRANDING, ...(cfg || {}) };
    const crest = document.getElementById('pas-center-crest');
    if (!crest) return;
    const enabled = _brandingState.enabled !== false && Boolean(_brandingState.title);
    crest.hidden = !enabled;
    if (!enabled) return;
    const titleEl = crest.querySelector('.pas-crest-title');
    const badgeEl = crest.querySelector('.pas-crest-badge');
    if (titleEl) titleEl.textContent = _brandingState.title;
    if (badgeEl) {
      const bText = (_brandingState.badge || '').trim();
      badgeEl.textContent = bText;
      badgeEl.hidden = !bText;
    }
    crest.title = `${_brandingState.title}${_brandingState.badge ? ` · ${_brandingState.badge}` : ''}（点击定制）`;
    if (typeof crest._relayout === 'function') crest._relayout();
  }

  function mountCenterCrest() {
    const bar = document.querySelector('.se-topbar, .topbar');
    if (!bar || document.getElementById('pas-center-crest')) return;

    const crest = document.createElement('button');
    crest.type = 'button';
    crest.id = 'pas-center-crest';
    crest.className = 'pas-center-crest';
    crest.setAttribute('aria-label', '定制顶栏主标题');
    crest.innerHTML = `
      <svg class="pas-crest-frame" viewBox="0 0 420 34" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="pas-crest-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.10"/>
            <stop offset="100%" stop-color="var(--accent-2, var(--accent))" stop-opacity="0.03"/>
          </linearGradient>
          <linearGradient id="pas-crest-stroke" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="var(--accent)" stop-opacity="0"/>
            <stop offset="14%" stop-color="var(--accent)" stop-opacity="0.48"/>
            <stop offset="50%" stop-color="var(--accent-2, var(--accent))" stop-opacity="0.68"/>
            <stop offset="86%" stop-color="var(--accent)" stop-opacity="0.48"/>
            <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"/>
          </linearGradient>
          <linearGradient id="pas-crest-glow" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="var(--accent)" stop-opacity="0"/>
            <stop offset="50%" stop-color="var(--accent)" stop-opacity="0.95"/>
            <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"/>
          </linearGradient>
        </defs>
        <path d="M 8 0 L 412 0 L 392 27 Q 388 32 380 32 L 40 32 Q 32 32 28 27 Z" fill="url(#pas-crest-fill)"/>
        <path d="M 1 1 L 12 1 L 29 27 Q 33 32 41 32 L 379 32 Q 387 32 391 27 L 408 1 L 419 1" fill="none" stroke="url(#pas-crest-stroke)" stroke-width="1.25"/>
        <line x1="128" y1="32" x2="292" y2="32" stroke="url(#pas-crest-glow)" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <span class="pas-crest-inner">
        <span class="pas-crest-wing" aria-hidden="true"></span>
        <span class="pas-crest-title"></span>
        <span class="pas-crest-badge"></span>
        <span class="pas-crest-wing" aria-hidden="true"></span>
        <span class="pas-crest-edit-ico" aria-hidden="true">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 1 1 3 3L7 19l-4 1 1-4Z"/></svg>
        </span>
      </span>
    `;
    crest.addEventListener('click', () => openBrandingModal());
    bar.appendChild(crest);

    const relayout = () => {
      if (crest.hidden) return;
      const barRect = bar.getBoundingClientRect();
      if (!barRect.width) return;
      const leftEl = bar.querySelector('.se-title-group') || bar.firstElementChild;
      const rightEl = bar.querySelector('.se-top-actions, .top-actions');
      const lRight = (leftEl && leftEl !== crest) ? (leftEl.getBoundingClientRect().right - barRect.left) : 0;
      const rLeft = (rightEl && rightEl !== crest) ? (rightEl.getBoundingClientRect().left - barRect.left) : barRect.width;
      const gapSpace = Math.floor(rLeft - lRight - 18);
      if (gapSpace < 140) {
        crest.dataset.crowded = '1';
        return;
      }
      crest.dataset.crowded = '0';
      const mid = barRect.width / 2;
      const symSpace = Math.floor(Math.min(mid - lRight, rLeft - mid) * 2 - 18);
      let avail = symSpace;
      if (symSpace >= 250) {
        crest.style.left = '50%';
      } else {
        // 两侧按钮略不对称时平滑对齐于实际空档中点，保证视觉平衡且零重叠
        crest.style.left = `${Math.round((lRight + rLeft) / 2)}px`;
        avail = gapSpace;
      }
      crest.style.maxWidth = `${Math.max(140, Math.min(avail, 520))}px`;
      crest.dataset.compact = avail < 290 ? '1' : '0';
    };
    crest._relayout = relayout;

    // 首屏立即可见（使用本地缓存或默认值，零闪烁），随后静默同步后端持久化配置
    applyBrandingToDOM(loadLocalBranding());
    if (typeof ResizeObserver !== 'undefined') {
      const ro = new ResizeObserver(() => requestAnimationFrame(relayout));
      ro.observe(bar);
      const leftEl = bar.querySelector('.se-title-group') || bar.firstElementChild;
      const rightEl = bar.querySelector('.se-top-actions, .top-actions');
      if (leftEl && leftEl !== crest) ro.observe(leftEl);
      if (rightEl && rightEl !== crest) ro.observe(rightEl);
    }
    window.addEventListener('resize', relayout);
    setTimeout(relayout, 80);
    setTimeout(relayout, 360);

    fetch('/api/ui/branding')
      .then((r) => r.json())
      .then((j) => {
        if (j && j.ok && j.data) {
          saveLocalBranding(j.data);
          applyBrandingToDOM(j.data);
        }
      })
      .catch(() => { /* fallback to local cache */ });

    window.addEventListener('storage', (e) => {
      if (e.key === BRANDING_STORE_KEY) applyBrandingToDOM(loadLocalBranding());
    });
  }

  function openBrandingModal() {
    closeOverlay();
    const cur = _brandingState || loadLocalBranding();
    const presets = (cur.presets && cur.presets.length) ? cur.presets : DEFAULT_BRANDING.presets;
    const wrap = document.createElement('div');
    wrap.className = 'pas-cmd-backdrop';
    wrap.style.paddingTop = '10vh';
    wrap.innerHTML = `
      <div class="pas-diff-modal pas-brand-modal" role="dialog" aria-label="定制顶栏主标题">
        <div class="pas-drawer-head">
          <h3><span>顶栏主标题定制</span></h3>
          <button type="button" class="se-btn compact" id="pb-close">✕</button>
        </div>
        <div class="pas-brand-presets">
          ${presets.map((p, i) => `
            <button type="button" class="pas-brand-preset-btn${p.title === cur.title ? ' active' : ''}" data-idx="${i}">
              <strong>${esc(p.title)}</strong>
              ${p.badge ? `<span>${esc(p.badge)}</span>` : ''}
            </button>`).join('')}
        </div>
        <form id="pb-form" class="pas-brand-form">
          <label class="se-field">
            <span>主标题</span>
            <input id="pb-title" type="text" maxlength="40" required value="${esc(cur.title || DEFAULT_BRANDING.title)}" placeholder="如：南极秦岭站综合能量管理系统">
          </label>
          <label class="se-field">
            <span>副徽标（可选）</span>
            <input id="pb-badge" type="text" maxlength="16" value="${esc(cur.badge || '')}" placeholder="如：秦岭站 / PAS">
          </label>
          <label class="pas-brand-toggle">
            <input id="pb-enabled" type="checkbox" ${cur.enabled !== false ? 'checked' : ''}>
            <span>在顶栏居中显示主标题徽牌</span>
          </label>
          <div class="se-modal-actions">
            <button type="button" class="se-btn ghost" id="pb-reset" style="margin-right:auto">恢复默认</button>
            <button type="button" class="se-btn ghost" id="pb-cancel">取消</button>
            <button type="submit" class="se-btn primary">保存生效</button>
          </div>
        </form>
      </div>`;
    wrap.addEventListener('click', (e) => { if (e.target === wrap) closeOverlay(); });
    wrap.querySelector('#pb-close').addEventListener('click', closeOverlay);
    wrap.querySelector('#pb-cancel').addEventListener('click', closeOverlay);
    document.body.appendChild(wrap);
    _activeOverlay = wrap;

    const titleInput = wrap.querySelector('#pb-title');
    const badgeInput = wrap.querySelector('#pb-badge');
    const enabledInput = wrap.querySelector('#pb-enabled');

    wrap.querySelectorAll('.pas-brand-preset-btn').forEach((b) => {
      b.addEventListener('click', () => {
        const p = presets[Number(b.dataset.idx)];
        if (!p) return;
        titleInput.value = p.title;
        badgeInput.value = p.badge || '';
        enabledInput.checked = true;
        wrap.querySelectorAll('.pas-brand-preset-btn').forEach((x) => x.classList.toggle('active', x === b));
      });
    });

    const persist = async (payload) => {
      const nextLocal = payload.reset
        ? { ...DEFAULT_BRANDING }
        : { ...DEFAULT_BRANDING, title: payload.title, badge: payload.badge, enabled: payload.enabled };
      saveLocalBranding(nextLocal);
      applyBrandingToDOM(nextLocal);
      try {
        const resp = await fetch('/api/ui/branding', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const j = await resp.json();
        if (resp.ok && j && j.ok && j.data) {
          saveLocalBranding(j.data);
          applyBrandingToDOM(j.data);
        }
      } catch { /* keep local */ }
      closeOverlay();
    };

    wrap.querySelector('#pb-reset').addEventListener('click', () => persist({ reset: true }));
    wrap.querySelector('#pb-form').addEventListener('submit', (e) => {
      e.preventDefault();
      const title = titleInput.value.trim();
      if (!title) return;
      persist({ title, badge: badgeInput.value.trim(), enabled: enabledInput.checked });
    });
    titleInput.focus();
    titleInput.select();
  }

  function mountTopbarEnhancements() {
    // 1. 若旧运行管理页缺少 #lang-select，自动补充三语下拉
    const topActions = document.querySelector('.top-actions, .se-top-actions');
    if (topActions && !document.getElementById('pas-cmd-trigger')) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.id = 'pas-cmd-trigger';
      btn.className = 'pas-kbd-btn';
      btn.title = '全站快速搜索 / 设备档案 / 切换风格 (Ctrl+K)';
      btn.setAttribute('aria-label', '搜索 Ctrl+K');
      btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/></svg>';
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
    mountPrefsPopover();
    initSidebarController();
    renderSidebarTree();
    initWallMode();
    mountWeatherBadge();
    enhanceVisualIcons();
    mountCenterCrest();
    applyLegacyI18n(getLang());
  }

  // 全局委托：点击任何 data-pas-device 元素直接打开 360° 设备抽屉
  document.addEventListener('click', (e) => {
    const el = e.target.closest?.('[data-pas-device]');
    if (!el) return;
    e.preventDefault();
    openDeviceDrawer(el.dataset.pasDevice);
  });

  // 全局快捷键：Ctrl+K / Cmd+K 打开命令面板，Esc 关闭，R 刷新，F 切换大屏投放
  document.addEventListener('keydown', (e) => {
    const tag = (e.target?.tagName || '').toLowerCase();
    const editing = tag === 'input' || tag === 'textarea' || tag === 'select' || e.target?.isContentEditable;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      closePrefsPopover();
      openCommandPalette();
      return;
    }
    if (e.key === 'Escape') {
      if (_prefsPopoverEl && !_prefsPopoverEl.hidden) {
        e.preventDefault();
        closePrefsPopover();
        return;
      }
      if (_activeOverlay) {
        e.preventDefault();
        closeOverlay();
        return;
      }
    }
    if (!editing && !e.ctrlKey && !e.metaKey && !e.altKey && e.key.toLowerCase() === 'r') {
      const refreshBtn = document.querySelector('#btn-refresh, [data-action="refresh"]');
      if (refreshBtn) {
        e.preventDefault();
        refreshBtn.click();
      }
      return;
    }
    if (!editing && !e.ctrlKey && !e.metaKey && !e.altKey && e.key.toLowerCase() === 'f') {
      const wallBtn = document.getElementById('btn-wall-mode');
      if (wallBtn) {
        e.preventDefault();
        wallBtn.click();
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
    openWeatherModal,
    openBrandingModal,
    getWeather: () => fetchWeatherState(false),
    refreshWeather: () => fetchWeatherState(true),
    renderTrendChart,
    renderSankey,
    renderDonut,
    renderGauge,
    renderBarChart,
    renderDivergingBar,
    renderPipelineFlow,
    renderRadarChart,
    renderHistogram,
    renderHeatMatrix,
    setWallMode,
    setSidebarMode,
    setSidebarHidden,
    getSidebarMode,
    createPoller,
    applyLegacyI18n,
    exportReport: () => window.open('/api/report/snapshot', '_blank'),
  };
})();
