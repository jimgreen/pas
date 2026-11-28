/* PAS 未来 24 小时 96 点安全预警与绿电维生分析（EW）前端核心应用 */
(() => {
  'use strict';

  const PAGE_I18N = {
    'zh-CN': {
      'title.ew_main': '安全预警 EW',
      'title.ew_scenario': '态势推演',
      'title.ew_risks': '风险预警',
      'title.ew_green': '绿电维生',
      'title.ew_config': '预测与参数配置',
      'title.ew_logs': 'EW 运行日志与历史',
      'nav.ew': '安全预警 EW',
      'nav.ew_main': '主画面',
      'nav.ew_scenario': '态势推演',
      'nav.ew_risks': '风险预警',
      'nav.ew_green': '绿电维生',
      'nav.ew_config': '预测与参数',
      'nav.ew_logs': '运行日志',
      'action.run_ew': '执行 EW',
      'action.reset': '恢复默认',
      'action.more': '全部 →',
      'ew.btn_params': '预测与覆写',
      'ew.sim_snapshot': '当刻演化断面',
      'ew.sim_risks': '当刻潜在风险',
      'ew.sim_device': '设备演化态',
      'ew.sim_curve_title': '未来 24h 96 点趋势演化曲线',
      'ew.green_title': '绿电维生能力',
      'ew.storage_units': '储能单元实时 SOC',
      'ew.scenario': '预测演变剧本',
      'ew.recalc': '重算',
      'ew.matrix_title': '未来 24h 96点预警矩阵',
      'ew.top_events': '高频风险源 / 扰动 Top',
      'ew.curve_title': '未来 96 点绿电维生与安全轨迹',
      'ew.tab_green': '绿电维生',
      'ew.tab_ren': '风光预测',
      'ew.tab_load': 'N-1负载',
      'ew.tab_score': '电压/评分',
      'ew.top_risks': '潜在风险提示 Top',
      'ew.slot_inspect': '重点时段断面详情',
      'ew.tab_risk_list': '潜在风险清单',
      'ew.tab_96_points': '未来 96 点全表',
      'ew.tab_audit_logs': 'EW 运行审计日志',
      'ew.tab_green_history': '历史绿电维生与预警记录',
      'ew.save_run': '保存并重算 EW',
      'col.severity': '等级',
      'col.time': '时刻',
      'col.event': '扰动/风险',
      'col.advice': '处置提示',
    },
    'en-US': {
      'title.ew_main': 'Early Warning EW',
      'title.ew_scenario': 'Scenario Evolution',
      'title.ew_risks': 'Risk Alerts',
      'title.ew_green': 'Green Autonomy',
      'title.ew_config': 'EW Forecast & Config',
      'title.ew_logs': 'EW Run Logs & History',
      'nav.ew': 'Early Warning EW',
      'nav.ew_main': 'Dashboard',
      'nav.ew_scenario': 'Scenario Sim',
      'nav.ew_risks': 'Risk Alerts',
      'nav.ew_green': 'Green Autonomy',
      'nav.ew_config': 'Forecast & Params',
      'nav.ew_logs': 'Run Logs',
      'action.run_ew': 'Run EW',
      'action.reset': 'Reset',
      'action.more': 'All →',
      'ew.btn_params': 'Forecast & Overrides',
      'ew.sim_snapshot': 'Slot Snapshot',
      'ew.sim_risks': 'Slot Risks',
      'ew.sim_device': 'Device Evolution',
      'ew.sim_curve_title': '24h 96-Point Forecast Evolution',
      'ew.green_title': 'Green Autonomy',
      'ew.storage_units': 'Live Storage SOC',
      'ew.scenario': 'Forecast Scenario',
      'ew.recalc': 'Run',
      'ew.matrix_title': '24h 96-Point Risk Matrix',
      'ew.top_events': 'Top Risk Drivers',
      'ew.curve_title': '96-Point Autonomy & Security',
      'ew.tab_green': 'Autonomy',
      'ew.tab_ren': 'Wind/PV',
      'ew.tab_load': 'N-1 Load%',
      'ew.tab_score': 'Volt/Score',
      'ew.top_risks': 'Potential Risk Alerts',
      'ew.slot_inspect': 'Selected Slot Detail',
      'ew.tab_risk_list': 'Risk Alerts',
      'ew.tab_96_points': '96-Point Table',
      'ew.tab_audit_logs': 'EW Audit Logs',
      'ew.tab_green_history': 'Green Autonomy History',
      'ew.save_run': 'Save & Run EW',
      'col.severity': 'Sev',
      'col.time': 'Time',
      'col.event': 'Event',
      'col.advice': 'Advice',
    },
    'ru-RU': {
      'title.ew_main': 'Предупреждение EW',
      'title.ew_scenario': 'Эволюция режимов',
      'title.ew_risks': 'Риски EW',
      'title.ew_green': 'Зелёная автономность',
      'title.ew_config': 'Прогноз и параметры EW',
      'title.ew_logs': 'Журнал и история EW',
      'nav.ew': 'Прогноз EW',
      'nav.ew_main': 'Главная',
      'nav.ew_scenario': 'Моделирование',
      'nav.ew_risks': 'Риски',
      'nav.ew_green': 'Автономность',
      'nav.ew_config': 'Параметры',
      'nav.ew_logs': 'Журнал',
      'action.run_ew': 'Запуск EW',
      'action.reset': 'Сброс',
      'action.more': 'Все →',
      'ew.btn_params': 'Прогноз и правки',
      'ew.sim_snapshot': 'Срез момента',
      'ew.sim_risks': 'Риски момента',
      'ew.sim_device': 'Динамика объекта',
      'ew.sim_curve_title': 'Прогнозная траектория 24ч (96 точек)',
      'ew.green_title': 'Зелёная автономность',
      'ew.storage_units': 'SOC накопителей',
      'ew.scenario': 'Сценарий прогноза',
      'ew.recalc': 'Расчёт',
      'ew.matrix_title': 'Матрица рисков 24ч (96 т.)',
      'ew.top_events': 'Частые источники риска',
      'ew.curve_title': 'Траектория автономности и N-1',
      'ew.tab_green': 'Автономность',
      'ew.tab_ren': 'Ветер/СЭС',
      'ew.tab_load': 'Нагрузка N-1',
      'ew.tab_score': 'Напр./Балл',
      'ew.top_risks': 'Потенциальные риски',
      'ew.slot_inspect': 'Детали интервала',
      'ew.tab_risk_list': 'Список рисков',
      'ew.tab_96_points': 'Таблица 96 точек',
      'ew.tab_audit_logs': 'Журнал аудита EW',
      'ew.tab_green_history': 'История автономности',
      'ew.save_run': 'Сохранить и запуск',
      'col.severity': 'Уров.',
      'col.time': 'Время',
      'col.event': 'Событие',
      'col.advice': 'Рекомендация',
    },
  };

  const view = document.body?.dataset?.ewView || 'home';
  const common = typeof window.createSECommon === 'function' ? window.createSECommon(PAGE_I18N, () => reloadPage()) : null;
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  const fmt = (v, d = 1) => (v == null || Number.isNaN(Number(v)) ? '—' : Number(v).toFixed(d));

  let _homeData = null;
  let _chartMode = 'green';
  let _selectedSlot = null;

  function showNotice(msg, isErr = false) {
    if (common?.notify) {
      common.notify(msg, isErr);
      return;
    }
    const el = document.getElementById('notice');
    if (!el) return;
    el.textContent = msg;
    el.className = isErr ? 'notice error' : 'notice';
    el.hidden = false;
    setTimeout(() => { el.hidden = true; }, 3200);
  }

  async function apiGet(url) {
    const r = await fetch(url);
    const j = await r.json();
    if (!r.ok || !j.ok) throw new Error(j.error || `HTTP ${r.status}`);
    return j.data;
  }

  async function apiPost(url, body = {}) {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const j = await r.json();
    if (!r.ok || !j.ok) throw new Error(j.error || `HTTP ${r.status}`);
    return j;
  }

  function sevBadge(sev) {
    const s = String(sev || 'normal');
    if (s === 'critical') return '<span class="se-pill bad">危急</span>';
    if (s === 'high') return '<span class="se-pill warn" style="color:#fb923c">高危</span>';
    if (s === 'medium') return '<span class="se-pill warn">中危</span>';
    if (s === 'low') return '<span class="se-pill neutral">低危</span>';
    return '<span class="se-pill ok">安全</span>';
  }

  function levelTone(lvl) {
    if (lvl === '危急') return 'bad';
    if (lvl === '警戒') return 'warn';
    if (lvl === '关注') return 'accent';
    return 'ok';
  }

  function survTone(hours, capped) {
    if (capped || hours >= 24) return 'ok';
    if (hours >= 12) return 'accent';
    if (hours >= 6) return 'warn';
    return 'bad';
  }

  function srcLabel(src) {
    if (src === 'forecast_db') return '三大预测库直连';
    if (src === 'partial_forecast_db') return '部分预测库直连';
    return '预测库缺失';
  }

  /* ==================== 1. EW 主画面渲染 ==================== */
  function renderHeroStrip(latest) {
    const strip = document.getElementById('ew-hero-strip');
    if (!strip || !latest) return;
    const hasSurv = latest.green_survival_hours != null && Number.isFinite(Number(latest.green_survival_hours));
    const h = hasSurv ? Number(latest.green_survival_hours) : null;
    const capped = Number(latest.green_survival_capped) === 1;
    const gTone = hasSurv ? survTone(h, capped) : 'neutral';
    const gValHtml = !hasSurv
      ? '—'
      : (capped ? `≥${h.toFixed(1)}<small>h</small>` : `${h.toFixed(2)}<small>h</small>`);
    const gBadge = !hasSurv
      ? '无数据'
      : (capped ? `外推 ${fmt(latest.green_survival_extrap_hours, 1)}h` : `${latest.green_exhaust_time || '—'} 触底`);
    const h2Txt = latest.green_survival_with_h2_hours != null ? `${fmt(latest.green_survival_with_h2_hours, 1)}h` : '—';
    const gSub = hasSurv
      ? `纯储保底 ${latest.green_survival_no_ren_hours != null ? `${fmt(latest.green_survival_no_ren_hours, 1)}h` : '—'} · 含氢 ${h2Txt}`
      : '缺少预测库或储能实时 SOC';

    const hasSc = latest.security_score != null && Number.isFinite(Number(latest.security_score));
    const sc = hasSc ? Number(latest.security_score) : null;
    const scTone = hasSc ? levelTone(latest.risk_level) : 'neutral';
    const riskSlots = Number(latest.risk_slots_count || 0);
    const totalSlots = Number(latest.horizon_points || 0);
    const slotTone = totalSlots === 0 ? 'neutral' : (riskSlots === 0 ? 'ok' : (Number(latest.critical_count) > 0 ? 'bad' : 'warn'));
    const hasMinSoc = latest.storage_min_soc_24h_pct != null && Number.isFinite(Number(latest.storage_min_soc_24h_pct));
    const minSoc = hasMinSoc ? Number(latest.storage_min_soc_24h_pct) : null;
    const socTone = !hasMinSoc ? 'neutral' : (minSoc <= 16 ? 'bad' : (minSoc <= 28 ? 'warn' : 'ok'));
    const hasMaxLd = latest.max_loading_pct != null && Number.isFinite(Number(latest.max_loading_pct));
    const maxLd = hasMaxLd ? Number(latest.max_loading_pct) : null;
    const ldTone = !hasMaxLd ? 'neutral' : (maxLd >= 100 ? 'bad' : (maxLd >= 80 ? 'warn' : 'ok'));

    const tiles = [
      {
        tone: gTone, lbl: '绿电维生时长', badge: gBadge, badgeTone: gTone,
        val: gValHtml, sub: gSub, pct: hasSurv ? Math.min(100, (h / 24) * 100) : 0,
      },
      {
        tone: scTone, lbl: '未来 24h 预警评分', badge: hasSc ? `${latest.health_grade || '—'}级 · ${latest.risk_level || '—'}` : '无预测数据', badgeTone: scTone,
        val: hasSc ? `${sc.toFixed(1)}<small>/100</small>` : '—',
        sub: latest.green_renewable_share_pct != null ? `绿电占比 ${fmt(latest.green_renewable_share_pct, 1)}%` : '待接入预测库',
        pct: hasSc ? sc : 0,
      },
      {
        tone: slotTone, lbl: '风险时段统计', badge: totalSlots ? `危 ${latest.critical_count || 0} · 高 ${latest.high_count || 0}` : '0 点', badgeTone: slotTone,
        val: totalSlots ? `${riskSlots}<small> / ${totalSlots}</small>` : '—',
        sub: totalSlots ? `N-1:${latest.n1_risk_count || 0} · 气象:${latest.weather_risk_count || 0} · 绿电:${latest.green_risk_count || 0}` : '请配置预测库或录入覆写',
        pct: totalSlots ? Math.min(100, (riskSlots / totalSlots) * 100) : 0,
      },
      {
        tone: socTone, lbl: '未来 24h 最低 SOC', badge: latest.storage_init_soc_pct != null ? `初 ${fmt(latest.storage_init_soc_pct, 1)}%` : '无SOC', badgeTone: socTone,
        val: hasMinSoc ? `${minSoc.toFixed(1)}<small>%</small>` : '—',
        sub: latest.storage_total_kwh ? `可用 ${fmt(latest.storage_usable_kwh, 0)} / ${fmt(latest.storage_total_kwh, 0)} kWh` : 'devices.db 无储能数据',
        pct: hasMinSoc ? minSoc : 0,
      },
      {
        tone: ldTone, lbl: 'N-1 峰值负载 / 最低V', badge: latest.max_loading_time || (hasMaxLd ? '—' : '无LF断面'), badgeTone: ldTone,
        val: hasMaxLd ? `${maxLd.toFixed(1)}<small>%</small>` : '—',
        sub: latest.min_v_pu != null ? `最低 ${fmt(latest.min_v_pu, 3)} pu (${latest.min_v_time || '—'})` : '缺少收敛 LF 断面',
        pct: hasMaxLd ? Math.min(100, maxLd) : 0,
      },
    ];

    strip.innerHTML = tiles.map((t) => `
      <div class="pas-hero-tile tone-${t.tone}">
        <div class="pas-hero-top">
          <span class="pas-hero-lbl">${esc(t.lbl)}</span>
          <span class="pas-hero-badge ${t.badgeTone} tabular">${esc(t.badge)}</span>
        </div>
        <div class="pas-hero-val-row">
          <div class="pas-hero-val ${t.tone === 'bad' ? 'bad' : (t.tone === 'warn' ? 'warn' : (t.tone === 'ok' ? 'ok' : ''))} tabular">${t.val}</div>
          <div class="pas-hero-sub tabular" title="${esc(t.sub)}">${esc(t.sub)}</div>
        </div>
        <div class="pas-hero-meter"><i style="width:${t.pct > 0 ? Math.max(4, Math.min(100, t.pct)).toFixed(1) : '0'}%"></i></div>
      </div>`).join('');
  }

  function renderGreenGaugeAndStorage(latest) {
    const gaugeEl = document.getElementById('ew-green-gauge');
    const chipsEl = document.getElementById('ew-green-chips');
    const badgeEl = document.getElementById('ew-green-badge');
    const barsEl = document.getElementById('ew-storage-bars');
    const stMeta = document.getElementById('ew-storage-meta');
    const srcTag = document.getElementById('ew-src-tag');
    if (!latest) return;

    const hasSurv = latest.green_survival_hours != null && Number.isFinite(Number(latest.green_survival_hours));
    const h = hasSurv ? Number(latest.green_survival_hours) : null;
    const capped = Number(latest.green_survival_capped) === 1;
    const tone = hasSurv ? survTone(h, capped) : 'neutral';
    if (badgeEl) {
      badgeEl.className = `se-pill ${tone} tabular`;
      badgeEl.textContent = !hasSurv ? '无数据' : (capped ? '24h+ 可持续' : `${h.toFixed(2)}h 维生`);
    }
    if (srcTag) srcTag.textContent = srcLabel(latest.forecast_source);

    if (gaugeEl) {
      if (!hasSurv) {
        gaugeEl.innerHTML = '<div class="ew-gauge-fallback tabular"><strong style="color:var(--text-muted)">—</strong><span>缺少预测库或储能实时 SOC</span></div>';
      } else if (window.PAS_KIT?.renderGauge) {
        window.PAS_KIT.renderGauge(gaugeEl, {
          value: Math.min(24, h),
          max: 24,
          label: capped ? `≥24h（外推 ${fmt(latest.green_survival_extrap_hours, 1)}h）` : `纯绿电维生 · ${latest.green_exhaust_time || '—'} 触底`,
          unit: 'h',
          color: tone === 'ok' ? 'var(--sem-ok)' : (tone === 'bad' ? 'var(--sem-danger)' : (tone === 'warn' ? 'var(--sem-warn)' : 'var(--accent)')),
        });
      } else {
        gaugeEl.innerHTML = `<div class="ew-gauge-fallback tabular"><strong>${capped ? '≥24.0' : h.toFixed(2)} h</strong><span>绿电占比 ${fmt(latest.green_renewable_share_pct, 1)}%</span></div>`;
      }
    }

    if (chipsEl) {
      const noRenTxt = latest.green_survival_no_ren_hours != null ? `${fmt(latest.green_survival_no_ren_hours, 2)} h` : '—';
      const h2Txt = latest.green_survival_with_h2_hours != null ? `${fmt(latest.green_survival_with_h2_hours, 1)} h` : '—';
      const coldTxt = latest.storage_cold_factor != null ? `${fmt(Number(latest.storage_cold_factor) * 100, 1)}%` : '—';
      const defTxt = latest.deficit_total_kwh != null ? `${fmt(latest.deficit_total_kwh, 1)} kWh` : '—';
      const defCol = latest.deficit_total_kwh == null ? 'var(--text-muted)' : (Number(latest.deficit_total_kwh) > 0 ? 'var(--sem-danger)' : 'var(--sem-ok)');
      chipsEl.innerHTML = `
        <div class="pas-stat-chip"><span>无风光保底</span><strong class="tabular">${noRenTxt}</strong></div>
        <div class="pas-stat-chip" title="${latest.green_survival_with_h2_hours == null ? 'devices.db HydroStorage 未定义电容量' : ''}"><span>含储氢维生</span><strong class="tabular">${h2Txt}</strong></div>
        <div class="pas-stat-chip"><span>极寒电池折减</span><strong class="tabular">${coldTxt}</strong></div>
        <div class="pas-stat-chip"><span>24h 绿电缺口</span><strong class="tabular" style="color:${defCol}">${defTxt}</strong></div>`;
    }

    const units = Array.isArray(latest.storage_units) ? latest.storage_units : [];
    if (stMeta) stMeta.textContent = units.length ? `${units.length} 台 · ${fmt(latest.storage_total_kwh, 0)} kWh` : '0 台';
    if (barsEl) {
      barsEl.innerHTML = units.slice(0, 6).map((u) => {
        const hasSoc = u.soc_pct != null && Number.isFinite(Number(u.soc_pct));
        const pct = hasSoc ? Math.max(0, Math.min(100, Number(u.soc_pct))) : 0;
        const col = u.domain === 'H2' ? 'var(--accent-2, #a78bfa)' : (pct < 25 ? 'var(--sem-danger)' : (pct < 45 ? 'var(--sem-warn)' : 'var(--sem-ok)'));
        return `<div class="pas-bar-row">
          <span class="lbl" title="${esc(u.name)}">${esc(u.name)}</span>
          <div class="track"><i style="width:${hasSoc ? pct.toFixed(1) : '0'}%;background:${col}"></i></div>
          <span class="val tabular">${hasSoc ? `${pct.toFixed(0)}%` : '—'}</span>
        </div>`;
      }).join('') || '<div class="se-empty">未检出储能单元</div>';
    }
  }

  function renderHeatMatrix(points, latest) {
    const el = document.getElementById('ew-heat-matrix');
    const meta = document.getElementById('ew-matrix-meta');
    if (!el) return;
    if (!points || !points.length) {
      el.innerHTML = '<div class="se-empty">—</div>';
      return;
    }
    if (meta) meta.textContent = `${latest?.risk_slots_count || 0}/${points.length} · ${latest?.scenario_label || ''}`;
    if (_selectedSlot == null) {
      _selectedSlot = latest?.worst_slot != null ? Number(latest.worst_slot) : (latest?.green_exhaust_slot != null ? Number(latest.green_exhaust_slot) : 0);
    }

    el.innerHTML = points.map((p) => {
      const sev = p.risk_level || 'normal';
      const cls = sev === 'critical' ? 'lv-bad' : (sev === 'high' ? 'lv-high' : (sev === 'medium' ? 'lv-warn' : 'lv-ok'));
      const sel = Number(p.slot_idx) === Number(_selectedSlot) ? ' is-selected' : '';
      const depleted = Number(p.green_alive) === 0 ? ' is-depleted' : '';
      const tip = `#${p.slot_idx} ${p.time_label}\n风电 ${fmt(p.wind_kw, 1)}kW · 光伏 ${fmt(p.pv_kw, 1)}kW · 负荷 ${fmt(p.load_kw, 1)}kW\n储能 SOC ${fmt(p.storage_soc_pct, 1)}% · N-1负载 ${fmt(p.n1_max_loading_pct, 1)}% · 最低V ${fmt(p.n1_min_v_pu, 3)}pu\n${p.worst_event || '安全'}`;
      return `<button type="button" class="ew-slot-cell ${cls}${sel}${depleted}" data-slot="${p.slot_idx}" title="${esc(tip)}">${esc(p.time_label)}</button>`;
    }).join('');

    el.querySelectorAll('.ew-slot-cell').forEach((btn) => {
      btn.addEventListener('click', () => {
        _selectedSlot = Number(btn.dataset.slot);
        el.querySelectorAll('.ew-slot-cell').forEach((b) => b.classList.toggle('is-selected', b === btn));
        renderSlotInspector(points);
      });
    });
    renderSlotInspector(points);
  }

  function renderSlotInspector(points) {
    const el = document.getElementById('ew-slot-inspector');
    const pill = document.getElementById('ew-slot-pill');
    if (!el || !points || !points.length) return;
    const pt = points.find((x) => Number(x.slot_idx) === Number(_selectedSlot)) || points[0];
    if (!pt) return;
    if (pill) {
      const sev = pt.risk_level || 'normal';
      pill.className = `se-pill ${sev === 'critical' ? 'bad' : (sev === 'high' || sev === 'medium' ? 'warn' : 'ok')} tabular`;
      pill.textContent = `#${pt.slot_idx} · ${pt.time_label}`;
    }
    el.innerHTML = `
      <div class="pas-chip-grid cols-3" style="margin-bottom:6px">
        <div class="pas-stat-chip"><span>风 / 光</span><strong class="tabular">${fmt(pt.wind_kw, 0)} / ${fmt(pt.pv_kw, 0)} kW</strong></div>
        <div class="pas-stat-chip"><span>预测负荷</span><strong class="tabular">${fmt(pt.load_kw, 1)} kW</strong></div>
        <div class="pas-stat-chip"><span>储能 SOC</span><strong class="tabular" style="color:${pt.green_alive ? 'var(--sem-ok)' : 'var(--sem-danger)'}">${fmt(pt.storage_soc_pct, 1)}%</strong></div>
        <div class="pas-stat-chip"><span>气象</span><strong class="tabular">${fmt(pt.irradiance_wm2, 0)}W · ${fmt(pt.wind_speed_ms, 1)}m/s</strong></div>
        <div class="pas-stat-chip"><span>N-1 负载</span><strong class="tabular" style="color:${Number(pt.n1_max_loading_pct) >= 100 ? 'var(--sem-danger)' : (Number(pt.n1_max_loading_pct) >= 80 ? 'var(--sem-warn)' : 'var(--text-primary)')}">${fmt(pt.n1_max_loading_pct, 1)}%</strong></div>
        <div class="pas-stat-chip"><span>N-1 最低V</span><strong class="tabular">${fmt(pt.n1_min_v_pu, 3)} pu</strong></div>
      </div>
      <div class="ew-slot-event ${pt.worst_event ? 'has-risk' : ''}">
        <strong>${pt.worst_event ? esc(pt.worst_event) : '该时段 N-0 / N-1 与绿电维生均满足安全约束'}</strong>
        <span class="tabular">绿电缺口 ${fmt(pt.green_deficit_kw, 1)} kW · 气温 ${fmt(pt.ambient_temp_c, 1)}℃ · 评分 ${fmt(pt.security_score, 0)}</span>
      </div>`;
  }

  function renderTopEvents(events) {
    const el = document.getElementById('ew-events-bars');
    const meta = document.getElementById('ew-events-meta');
    if (!el) return;
    if (meta) meta.textContent = `${(events || []).length} 类`;
    if (!events || !events.length) {
      el.innerHTML = '<div class="se-empty">未来 24h 无显著越限风险源</div>';
      return;
    }
    const maxCnt = Math.max(1, ...events.map((x) => Number(x.count || 0)));
    el.innerHTML = events.slice(0, 6).map((ev) => {
      const col = ev.max_sev === 'critical' ? 'var(--sem-danger)' : (ev.max_sev === 'high' ? '#fb923c' : 'var(--sem-warn)');
      return `<div class="pas-bar-row">
        <span class="lbl" title="${esc(ev.name)}（首次 ${esc(ev.first_time)}）">${esc(ev.name)}</span>
        <div class="track"><i style="width:${(Number(ev.count) / maxCnt * 100).toFixed(1)}%;background:${col}"></i></div>
        <span class="val tabular">${ev.count}点</span>
      </div>`;
    }).join('');
  }

  /**
   * 专用高密度交互式多序列双轴 SVG 趋势图（支持面积渐变、右轴 SOC%、触底红线与悬停十字浮标）。
   */
  function renderMultiLineChart(host, {
    labels = [],
    series = [],
    unit = '',
    rightUnit = '%',
    threshold = null,
    exhaustSlot = null,
    exhaustLabel = '',
  } = {}) {
    if (!host) return;
    if (!labels.length || !series.length) {
      host.innerHTML = '<div class="se-empty">暂无趋势数据</div>';
      return;
    }
    const rect = host.getBoundingClientRect();
    const W = Math.max(360, Math.floor(rect.width || 720));
    const H = Math.max(168, Math.floor(rect.height || 205));
    const hasRight = series.some((s) => s.rightAxis);
    const pad = { l: 46, r: hasRight ? 42 : 16, t: 24, b: 24 };
    const pw = Math.max(80, W - pad.l - pad.r);
    const ph = Math.max(60, H - pad.t - pad.b);

    const leftVals = series.filter((s) => !s.rightAxis).flatMap((s) => s.data.map(Number).filter(Number.isFinite));
    let minL = leftVals.length ? Math.min(...leftVals, 0) : 0;
    let maxL = leftVals.length ? Math.max(...leftVals, 10) : 100;
    if (threshold != null && Number.isFinite(threshold)) {
      minL = Math.min(minL, threshold);
      maxL = Math.max(maxL, threshold);
    }
    if (maxL - minL < 1) maxL = minL + 10;
    else maxL += (maxL - minL) * 0.08;

    const xAt = (i) => pad.l + (i / Math.max(1, labels.length - 1)) * pw;
    const yL = (v) => pad.t + ph - ((v - minL) / (maxL - minL)) * ph;
    const yR = (v) => pad.t + ph - (Math.max(0, Math.min(100, v)) / 100) * ph;

    const uid = `ewc_${Math.random().toString(36).slice(2, 8)}`;
    const defs = series.map((s, idx) => s.area ? `
      <linearGradient id="${uid}_g${idx}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${s.color}" stop-opacity="0.28"/>
        <stop offset="100%" stop-color="${s.color}" stop-opacity="0.02"/>
      </linearGradient>` : '').join('');

    const gridY = [0, 0.25, 0.5, 0.75, 1].map((r) => {
      const y = pad.t + ph * (1 - r);
      const valL = minL + (maxL - minL) * r;
      const rightTxt = hasRight
        ? `<text x="${W - pad.r + 5}" y="${(y + 3).toFixed(1)}" text-anchor="start" fill="var(--accent)" font-size="10" opacity="0.85">${Math.round(r * 100)}${esc(rightUnit)}</text>`
        : '';
      return `<line x1="${pad.l}" y1="${y.toFixed(1)}" x2="${W - pad.r}" y2="${y.toFixed(1)}" stroke="var(--border-color)" stroke-dasharray="2 3" opacity="0.55"/>
        <text x="${pad.l - 6}" y="${(y + 3).toFixed(1)}" text-anchor="end" fill="var(--text-muted)" font-size="10">${valL.toFixed(maxL - minL >= 20 ? 0 : 1)}</text>${rightTxt}`;
    }).join('');

    const stepTick = Math.max(1, Math.floor(labels.length / 8));
    const tickIdxs = [];
    for (let i = 0; i < labels.length; i += stepTick) tickIdxs.push(i);
    if (tickIdxs[tickIdxs.length - 1] !== labels.length - 1) tickIdxs.push(labels.length - 1);
    const xTicks = tickIdxs.map((i) => `<text x="${xAt(i).toFixed(1)}" y="${H - 6}" text-anchor="middle" fill="var(--text-muted)" font-size="10">${esc(labels[i])}</text>`).join('');

    const threshLine = (threshold != null && Number.isFinite(threshold))
      ? `<line x1="${pad.l}" y1="${yL(threshold).toFixed(1)}" x2="${W - pad.r}" y2="${yL(threshold).toFixed(1)}" stroke="var(--sem-danger)" stroke-dasharray="4 3" stroke-width="1.2" opacity="0.75"/>`
      : '';

    const exhaustMark = (exhaustSlot != null && exhaustSlot >= 0 && exhaustSlot < labels.length) ? (() => {
      const ex = xAt(exhaustSlot);
      const bx = Math.min(W - pad.r - 82, Math.max(pad.l + 4, ex - 40));
      return `<line x1="${ex.toFixed(1)}" y1="${pad.t}" x2="${ex.toFixed(1)}" y2="${pad.t + ph}" stroke="var(--sem-danger)" stroke-width="1.5" stroke-dasharray="4 2"/>
        <rect x="${bx.toFixed(1)}" y="${pad.t + 2}" width="80" height="16" rx="4" fill="var(--sem-danger)"/>
        <text x="${(bx + 40).toFixed(1)}" y="${pad.t + 13.5}" text-anchor="middle" fill="#fff" font-size="10" font-weight="600">${esc(exhaustLabel || `${labels[exhaustSlot]} 触底`)}</text>`;
    })() : '';

    const areasAndLines = series.map((s, idx) => {
      const ptsXY = s.data.map((v, i) => [xAt(i), s.rightAxis ? yR(Number(v || 0)) : yL(Number(v || 0))]);
      const d = ptsXY.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
      const area = s.area
        ? `<path d="${d} L${ptsXY[ptsXY.length - 1][0].toFixed(1)},${(pad.t + ph).toFixed(1)} L${ptsXY[0][0].toFixed(1)},${(pad.t + ph).toFixed(1)} Z" fill="url(#${uid}_g${idx})"/>`
        : '';
      return `${area}<path d="${d}" fill="none" stroke="${s.color}" stroke-width="${s.rightAxis ? 1.8 : 2}" ${s.rightAxis ? 'stroke-dasharray="4 3"' : ''}/>`;
    }).join('');

    const legend = series.map((s, idx) => `
      <g transform="translate(${pad.l + idx * 126}, 13)">
        <line x1="0" y1="-3" x2="14" y2="-3" stroke="${s.color}" stroke-width="2" ${s.rightAxis ? 'stroke-dasharray="3 2"' : ''}/>
        <text x="18" y="0" fill="var(--text-secondary)" font-size="10.5">${esc(s.name)}</text>
      </g>`).join('');

    const unitTag = unit ? `<text x="${pad.l - 6}" y="13" text-anchor="end" fill="var(--text-muted)" font-size="10">${esc(unit)}</text>` : '';

    host.style.position = 'relative';
    host.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" style="display:block;width:100%;height:100%">
      <defs>${defs}</defs>
      ${gridY}${xTicks}${threshLine}${areasAndLines}${exhaustMark}${unitTag}${legend}
      <line class="ewc-hover-line" x1="0" y1="${pad.t}" x2="0" y2="${pad.t + ph}" stroke="var(--accent)" stroke-width="1.2" stroke-dasharray="3 2" visibility="hidden"/>
      ${series.map((s) => `<circle class="ewc-hover-dot" cx="0" cy="0" r="3.8" fill="${s.color}" stroke="var(--bg-surface)" stroke-width="1.5" visibility="hidden"/>`).join('')}
    </svg><div class="pas-chart-tip" hidden></div>`;

    const svgEl = host.querySelector('svg');
    const hLine = svgEl?.querySelector('.ewc-hover-line');
    const hDots = Array.from(svgEl?.querySelectorAll('.ewc-hover-dot') || []);
    const tip = host.querySelector('.pas-chart-tip');

    host.onpointermove = (ev) => {
      const box = host.getBoundingClientRect();
      const rx = ev.clientX - box.left;
      const ratio = Math.max(0, Math.min(1, (rx - pad.l) / pw));
      const idx = Math.round(ratio * (labels.length - 1));
      const cx = xAt(idx);
      if (hLine) {
        hLine.setAttribute('x1', cx.toFixed(1));
        hLine.setAttribute('x2', cx.toFixed(1));
        hLine.setAttribute('visibility', 'visible');
      }
      series.forEach((s, si) => {
        const dot = hDots[si];
        if (!dot) return;
        const val = Number(s.data[idx] || 0);
        dot.setAttribute('cx', cx.toFixed(1));
        dot.setAttribute('cy', (s.rightAxis ? yR(val) : yL(val)).toFixed(1));
        dot.setAttribute('visibility', 'visible');
      });
      if (tip) {
        tip.innerHTML = `<div style="font-weight:700;margin-bottom:2px">${esc(labels[idx])} (#${idx})</div>`
          + series.map((s) => `<div style="display:flex;justify-content:space-between;gap:10px"><span style="color:${s.color}">● ${esc(s.name)}</span><strong class="tabular">${fmt(s.data[idx], 1)}${s.rightAxis ? esc(rightUnit) : esc(unit)}</strong></div>`).join('');
        tip.hidden = false;
        const tw = tip.offsetWidth || 150;
        const tx = Math.min(window.innerWidth - tw - 12, ev.clientX + 14);
        const ty = Math.max(12, ev.clientY - 26);
        tip.style.left = `${tx}px`;
        tip.style.top = `${ty}px`;
      }
    };
    host.onpointerleave = () => {
      if (hLine) hLine.setAttribute('visibility', 'hidden');
      hDots.forEach((d) => d.setAttribute('visibility', 'hidden'));
      if (tip) tip.hidden = true;
    };
  }

  function renderMainCurve(points, latest) {
    const el = document.getElementById('ew-home-trend');
    if (!el) return;
    if (!points || !points.length) {
      el.innerHTML = '<div class="se-empty">—</div>';
      return;
    }
    const labels = points.map((p) => p.time_label);
    let series = [];
    let yUnit = 'kW';
    let threshold = null;
    const exhaustSlot = (latest && Number(latest.green_survival_capped) === 0 && latest.green_exhaust_slot != null)
      ? Number(latest.green_exhaust_slot) : null;

    if (_chartMode === 'green') {
      series = [
        { name: '预测负荷(kW)', color: 'var(--sem-warn)', data: points.map((p) => Number(p.load_kw || 0)), area: true },
        { name: '绿电出力(kW)', color: 'var(--sem-ok)', data: points.map((p) => Number(p.renewable_kw || 0)), area: true },
        { name: '储能SOC(%)', color: 'var(--accent)', data: points.map((p) => Number(p.storage_soc_pct || 0)), rightAxis: true },
      ];
      yUnit = 'kW';
    } else if (_chartMode === 'renewable') {
      series = [
        { name: '风电预测(kW)', color: 'var(--accent)', data: points.map((p) => Number(p.wind_kw || 0)), area: true },
        { name: '光伏预测(kW)', color: 'var(--sem-warn)', data: points.map((p) => Number(p.pv_kw || 0)), area: true },
        { name: '净负荷(kW)', color: '#a78bfa', data: points.map((p) => Number(p.net_load_kw || 0)) },
      ];
      yUnit = 'kW';
    } else if (_chartMode === 'loading') {
      series = [
        { name: 'N-1极限负载(%)', color: 'var(--sem-danger)', data: points.map((p) => Number(p.n1_max_loading_pct || 0)), area: true },
        { name: 'N-0基态负载(%)', color: 'var(--accent)', data: points.map((p) => Number(p.n0_max_loading_pct || 0)) },
      ];
      yUnit = '%';
      threshold = 100;
    } else {
      series = [
        { name: '时段安全分', color: 'var(--sem-ok)', data: points.map((p) => Number(p.security_score || 0)), area: true },
        { name: '储能SOC(%)', color: 'var(--accent)', data: points.map((p) => Number(p.storage_soc_pct || 0)), rightAxis: true },
      ];
      yUnit = '分';
      threshold = 80;
    }

    renderMultiLineChart(el, {
      labels,
      series,
      unit: yUnit,
      threshold,
      exhaustSlot: _chartMode === 'green' ? exhaustSlot : null,
      exhaustLabel: latest?.green_exhaust_time ? `${latest.green_exhaust_time} 触底` : '',
    });
  }

  function renderTopRisks(risks) {
    const tb = document.getElementById('ew-home-top-risks');
    if (!tb) return;
    if (!risks || !risks.length) {
      tb.innerHTML = '<tr><td colspan="4" class="se-empty">未来 24h 无潜在越限风险</td></tr>';
      return;
    }
    tb.innerHTML = risks.slice(0, 10).map((r) => `
      <tr class="${r.severity === 'critical' ? 'row-bad' : ''}">
        <td>${sevBadge(r.severity)}</td>
        <td class="tabular">${esc(r.time_label)}</td>
        <td title="${esc(r.detail)}">${esc(r.contingency_name || r.device_name)}</td>
        <td class="se-muted" title="${esc(r.advice)}">${esc(r.advice || r.detail)}</td>
      </tr>`).join('');
  }

  async function loadHome() {
    const data = await apiGet('/api/ew/home');
    _homeData = data;
    const latest = data.latest;
    const pill = document.getElementById('ew-level-pill');
    const meta = document.getElementById('ew-run-meta');
    if (pill && latest) {
      pill.className = `se-pill ${levelTone(latest.risk_level)}`;
      pill.textContent = `${latest.risk_level} · ${latest.health_grade}级`;
    }
    if (meta && latest) {
      meta.textContent = `#${latest.ew_run_id} · ${latest.scenario_label} · ${(latest.calc_time || '').slice(11, 19)}`;
    }
    const sel = document.getElementById('ew-scenario-select');
    if (sel && Array.isArray(data.scenarios)) {
      sel.innerHTML = data.scenarios.map((s) => `<option value="${esc(s.key)}">${esc(s.label)}</option>`).join('');
      sel.value = (data.params && data.params.forecast_scenario) || 'auto';
    }
    renderHeroStrip(latest);
    renderGreenGaugeAndStorage(latest);
    renderHeatMatrix(data.points || [], latest);
    renderTopEvents(data.top_events || []);
    renderMainCurve(data.points || [], latest);
    renderTopRisks(data.top_risks || []);

    const log = data.latest_log;
    const lt = document.getElementById('ew-log-tag');
    const ltime = document.getElementById('ew-log-time');
    const lmsg = document.getElementById('ew-log-msg');
    if (log && lt && ltime && lmsg) {
      lt.textContent = log.level || 'INFO';
      ltime.textContent = (log.calc_time || '').slice(0, 19).replace('T', ' ');
      lmsg.textContent = log.message || latest?.summary_text || '—';
    }
  }

  /* ==================== 2. 风险与 96 点全表页 ==================== */
  async function loadRisksPage() {
    const cat = document.getElementById('ew-f-cat')?.value || 'all';
    const sev = document.getElementById('ew-f-sev')?.value || 'all';
    const q = document.getElementById('ew-f-q')?.value || '';
    const [risksData, ptsSnap] = await Promise.all([
      apiGet(`/api/ew/risks?category=${encodeURIComponent(cat)}&severity=${encodeURIComponent(sev)}&q=${encodeURIComponent(q)}&limit=300`),
      apiGet('/api/ew/points'),
    ]);
    const latest = risksData.latest || ptsSnap.latest;
    const meta = document.getElementById('ew-risks-meta');
    if (meta && latest) {
      meta.textContent = `#${latest.ew_run_id} · 风险 ${risksData.meta?.total || 0} 项 · 绿电维生 ${latest.green_survival_capped ? '≥' : ''}${fmt(latest.green_survival_hours, 2)}h`;
    }
    const rtb = document.getElementById('ew-risks-tbody');
    if (rtb) {
      const rows = risksData.rows || [];
      rtb.innerHTML = rows.length ? rows.map((r) => `
        <tr class="${r.severity === 'critical' ? 'row-bad' : ''}">
          <td class="tabular">${esc(r.time_label)} (#${r.slot_idx})</td>
          <td>${sevBadge(r.severity)}</td>
          <td>${esc(r.category)}</td>
          <td>${esc(r.contingency_name)}</td>
          <td>${esc(r.device_name)}</td>
          <td class="tabular">${fmt(r.actual_value, 2)}${esc(r.unit)}</td>
          <td class="tabular">${fmt(r.limit_value, 2)}${esc(r.unit)}</td>
          <td class="tabular">${fmt(r.violation_pct, 1)}%</td>
          <td title="${esc(r.advice)}">${esc(r.detail)} <span class="se-muted">→ ${esc(r.advice)}</span></td>
        </tr>`).join('') : '<tr><td colspan="9" class="se-empty">无匹配预警记录</td></tr>';
    }
    const ptb = document.getElementById('ew-points-tbody');
    if (ptb) {
      const pts = ptsSnap.points || [];
      ptb.innerHTML = pts.map((p) => `
        <tr class="${p.risk_level === 'critical' ? 'row-bad' : ''}">
          <td class="tabular">${p.slot_idx}</td>
          <td class="tabular">${esc(p.time_label)}</td>
          <td class="tabular">${fmt(p.irradiance_wm2, 0)}</td>
          <td class="tabular">${fmt(p.wind_speed_ms, 1)}</td>
          <td class="tabular">${fmt(p.ambient_temp_c, 1)}</td>
          <td class="tabular">${fmt(p.wind_kw, 1)}</td>
          <td class="tabular">${fmt(p.pv_kw, 1)}</td>
          <td class="tabular">${fmt(p.load_kw, 1)}</td>
          <td class="tabular">${fmt(p.net_load_kw, 1)}</td>
          <td class="tabular" style="color:${p.green_alive ? 'var(--sem-ok)' : 'var(--sem-danger)'}">${fmt(p.storage_soc_pct, 1)}%</td>
          <td class="tabular">${fmt(p.storage_power_kw, 1)}</td>
          <td class="tabular" style="color:${Number(p.green_deficit_kw) > 0 ? 'var(--sem-danger)' : 'var(--text-secondary)'}">${fmt(p.green_deficit_kw, 1)}</td>
          <td class="tabular">${fmt(p.n0_max_loading_pct, 1)}%</td>
          <td class="tabular">${fmt(p.n1_max_loading_pct, 1)}%</td>
          <td class="tabular">${fmt(p.n1_min_v_pu, 3)}</td>
          <td>${sevBadge(p.risk_level)}</td>
          <td>${esc(p.worst_event || '—')}</td>
        </tr>`).join('');
    }
  }

  function slotOptionLabel(i, pts) {
    const pt = Array.isArray(pts) ? pts.find((p) => Number(p.slot_idx) === i) : null;
    if (pt && pt.time_label) return `#${i} (${pt.time_label})`;
    const hh = String(Math.floor((i * 15) / 60)).padStart(2, '0');
    const mm = String((i * 15) % 60).padStart(2, '0');
    return `#${i} (${hh}:${mm})`;
  }

  function populateSlotSelects(pts) {
    const sf = document.getElementById('ovr-slot-from');
    const st = document.getElementById('ovr-slot-to');
    if (!sf || !st) return;
    const prevF = sf.value || '0';
    const prevT = st.value || prevF;
    const opts = Array.from({ length: 96 }, (_, i) => `<option value="${i}">${esc(slotOptionLabel(i, pts))}</option>`).join('');
    sf.innerHTML = opts;
    st.innerHTML = opts;
    sf.value = prevF;
    st.value = Number(prevT) >= Number(prevF) ? prevT : prevF;
    if (!sf.dataset.boundSync) {
      sf.dataset.boundSync = '1';
      sf.addEventListener('change', () => {
        if (Number(st.value) < Number(sf.value)) st.value = sf.value;
      });
    }
  }

  /* ==================== 3. 预测与参数配置页 ==================== */
  async function loadConfigPage() {
    const [home, overrides, dbFiles] = await Promise.all([
      apiGet('/api/ew/home'),
      apiGet('/api/ew/overrides'),
      apiGet('/api/ew/forecast-files').catch(() => []),
    ]);
    const params = home.params || {};
    const form = document.getElementById('ew-params-form');
    const scSel = document.getElementById('p-scenario');
    if (scSel && Array.isArray(home.scenarios)) {
      scSel.innerHTML = home.scenarios.map((s) => `<option value="${esc(s.key)}">${esc(s.label)}</option>`).join('');
    }
    const dl = document.getElementById('ew-forecast-db-list');
    if (dl && Array.isArray(dbFiles)) {
      dl.innerHTML = dbFiles.map((f) => `<option value="${esc(f.path)}">${esc(f.name)} (${f.size_kb} KB)</option>`).join('');
    }
    populateSlotSelects(home.points || []);
    if (form) {
      Object.entries(params).forEach(([k, v]) => {
        const el = form.elements.namedItem(k);
        if (el && v != null) el.value = String(v);
      });
    }
    const dsBadges = document.getElementById('ew-ds-badges');
    const ds = home.latest?.weather_snapshot?.data_sources || {};
    if (dsBadges) {
      dsBadges.innerHTML = ['renewgen', 'load', 'weather'].map((k) => {
        const item = ds[k] || {};
        const ok = Boolean(item.connected);
        const label = k === 'renewgen' ? 'renewgen.db' : (k === 'load' ? 'load.db' : 'weather.db');
        const stTxt = ok ? `${item.rows}点${item.point_id ? ` · ${item.point_id}` : ''}` : (item.exists ? '表为空' : '文件缺失');
        return `<span class="se-pill ${ok ? 'ok' : 'bad'}" title="${esc(item.path || '')} (${esc(item.status || '')})">${label}: ${esc(stTxt)}</span>`;
      }).join('');
    }
    const meta = document.getElementById('ew-cfg-meta');
    if (meta) meta.textContent = `覆写 ${overrides.length} 点 · 更新 ${(params.updated_at || '').slice(0, 19).replace('T', ' ')}`;

    const tb = document.getElementById('ew-ovr-tbody');
    if (tb) {
      const numCell = (slot, field, val) => `<input type="number" step="any" class="tabular" data-ovr-slot="${slot}" data-ovr-field="${field}" value="${val ?? ''}" placeholder="—">`;
      tb.innerHTML = overrides.length ? overrides.map((o) => `
        <tr data-ovr-row="${o.slot_idx}">
          <td class="tabular">${esc(slotOptionLabel(o.slot_idx, home.points || []))}</td>
          <td>${numCell(o.slot_idx, 'irradiance_wm2', o.irradiance_wm2)}</td>
          <td>${numCell(o.slot_idx, 'wind_speed_ms', o.wind_speed_ms)}</td>
          <td>${numCell(o.slot_idx, 'ambient_temp_c', o.ambient_temp_c)}</td>
          <td>${numCell(o.slot_idx, 'wind_kw', o.wind_kw)}</td>
          <td>${numCell(o.slot_idx, 'pv_kw', o.pv_kw)}</td>
          <td>${numCell(o.slot_idx, 'load_kw', o.load_kw)}</td>
          <td class="tabular se-muted">${(o.updated_at || '').slice(0, 19).replace('T', ' ')}</td>
          <td><button type="button" class="se-btn mini danger-ghost" data-del-ovr="${o.slot_idx}">删除</button></td>
        </tr>`).join('') : '<tr><td colspan="9" class="se-empty">暂无手工覆写 · 可在上方选择起止时段批量录入，或直接连接三大预测库</td></tr>';
      // 表格单元格内嵌无缝编辑：失焦或回车直接写回 pas.db
      tb.querySelectorAll('input[data-ovr-slot]').forEach((inp) => {
        inp.addEventListener('change', async () => {
          const slot = Number(inp.dataset.ovrSlot);
          const tr = tb.querySelector(`tr[data-ovr-row="${slot}"]`);
          if (!tr) return;
          const payload = { slot_idx: slot };
          tr.querySelectorAll('input[data-ovr-field]').forEach((el) => {
            payload[el.dataset.ovrField] = el.value;
          });
          try {
            await apiPost('/api/ew/overrides', payload);
            showNotice(`时段 #${slot} 覆写已保存`);
          } catch (err) {
            showNotice(err.message || '保存失败', true);
          }
        });
      });
      tb.querySelectorAll('[data-del-ovr]').forEach((b) => {
        b.addEventListener('click', async () => {
          await apiPost(`/api/ew/overrides/${b.dataset.delOvr}/delete`);
          showNotice('已删除单点覆写');
          loadConfigPage();
        });
      });
    }
  }

  /* ==================== 4. 运行日志与历史页 ==================== */
  async function loadLogsPage() {
    const lvl = document.getElementById('ew-log-level')?.value || 'all';
    const q = document.getElementById('ew-log-q')?.value || '';
    const [logsData, hist] = await Promise.all([
      apiGet(`/api/ew/logs?level=${encodeURIComponent(lvl)}&q=${encodeURIComponent(q)}&limit=120`),
      apiGet('/api/ew/history?limit=60'),
    ]);
    const meta = document.getElementById('ew-logs-meta');
    if (meta) meta.textContent = `日志 ${logsData.meta?.total || 0} 条 · 历史 ${hist.length} 次`;
    const cLogs = document.getElementById('ew-tab-logs-count');
    if (cLogs) cLogs.textContent = String(logsData.meta?.total || 0);
    const cHist = document.getElementById('ew-tab-hist-count');
    if (cHist) cHist.textContent = String(hist.length);

    const ltb = document.getElementById('ew-logs-tbody');
    if (ltb) {
      const rows = logsData.rows || [];
      ltb.innerHTML = rows.length ? rows.map((r) => `
        <tr>
          <td class="tabular">${(r.calc_time || '').slice(0, 19).replace('T', ' ')}</td>
          <td><span class="se-pill ${r.level === 'ERROR' ? 'bad' : (r.level === 'WARN' ? 'warn' : 'ok')}">${esc(r.level)}</span></td>
          <td>${esc(r.stage)}</td>
          <td>${esc(r.source)}</td>
          <td class="tabular">${r.elapsed_ms != null ? Number(r.elapsed_ms).toFixed(1) : '—'}</td>
          <td>${esc(r.message)}</td>
        </tr>`).join('') : '<tr><td colspan="6" class="se-empty">暂无运行日志</td></tr>';
    }
    const htb = document.getElementById('ew-hist-tbody');
    if (htb) {
      const rows = [...hist].reverse();
      htb.innerHTML = rows.length ? rows.map((h) => `
        <tr>
          <td class="tabular">#${h.ew_run_id}</td>
          <td class="tabular">${(h.calc_time || '').slice(0, 19).replace('T', ' ')}</td>
          <td>${esc(h.scenario_label)}</td>
          <td class="tabular" style="color:${survTone(h.green_survival_hours, h.green_survival_capped) === 'ok' ? 'var(--sem-ok)' : 'var(--sem-warn)'}">${h.green_survival_capped ? '≥' : ''}${fmt(h.green_survival_hours, 2)}h</td>
          <td class="tabular">${h.green_survival_no_ren_hours != null ? `${fmt(h.green_survival_no_ren_hours, 2)}h` : '—'}</td>
          <td class="tabular">${h.green_survival_with_h2_hours != null ? `${fmt(h.green_survival_with_h2_hours, 2)}h` : '—'}</td>
          <td class="tabular">${h.storage_min_soc_24h_pct != null ? `${fmt(h.storage_min_soc_24h_pct, 1)}%` : '—'}</td>
          <td class="tabular">${fmt(h.security_score, 1)} (${esc(h.health_grade)})</td>
          <td class="tabular">${h.risk_slots_count}/96</td>
          <td>${esc(h.summary_text || '—')}</td>
        </tr>`).join('') : '<tr><td colspan="10" class="se-empty">暂无历史记录</td></tr>';
    }
  }

  /* ==================== 5. 态势推演页（潮流图中心 + 96点实时演化） ==================== */
  const SVG_NS = 'http://www.w3.org/2000/svg';
  const sim = {
    svgLoaded: false,
    svgT: { scale: 0.45, tx: 0, ty: 0, vbW: 2518, vbH: 2143 },
    topo: null,
    home: null,
    risks: [],
    slot: 0,
    mode: 'power',
    chartMode: 'green',
    selectedDevId: null,
    playing: false,
    timer: null,
    speedMs: 450,
  };

  function cssVar(name, fallback = '#38bdf8') {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }

  function applySimSvgTransform() {
    const c = document.getElementById('ew-svg-canvas');
    if (c) c.style.transform = `translate(${sim.svgT.tx}px, ${sim.svgT.ty}px) scale(${sim.svgT.scale})`;
    const lbl = document.getElementById('ew-zoom-label');
    if (lbl) lbl.textContent = `${Math.round(sim.svgT.scale * 100)}%`;
  }

  function fitSimSvg() {
    const vp = document.getElementById('ew-svg-viewport');
    if (!vp) return;
    const r = vp.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const s = Math.min((r.width - 20) / sim.svgT.vbW, (r.height - 20) / sim.svgT.vbH);
    sim.svgT.scale = Math.max(0.14, Math.min(2.5, s || 0.45));
    sim.svgT.tx = (r.width - sim.svgT.vbW * sim.svgT.scale) / 2;
    sim.svgT.ty = (r.height - sim.svgT.vbH * sim.svgT.scale) / 2;
    applySimSvgTransform();
  }

  function zoomSimSvg(factor, cx, cy) {
    const vp = document.getElementById('ew-svg-viewport');
    if (!vp) return;
    const r = vp.getBoundingClientRect();
    const ox = cx ?? r.width / 2;
    const oy = cy ?? r.height / 2;
    const prev = sim.svgT.scale;
    const next = Math.max(0.14, Math.min(4.0, prev * factor));
    sim.svgT.tx = ox - ((ox - sim.svgT.tx) * next) / prev;
    sim.svgT.ty = oy - ((oy - sim.svgT.ty) * next) / prev;
    sim.svgT.scale = next;
    applySimSvgTransform();
  }

  async function ensureSimSvgLoaded() {
    if (sim.svgLoaded) return;
    const canvas = document.getElementById('ew-svg-canvas');
    if (!canvas) return;
    const resp = await fetch('/api/se/svg');
    if (!resp.ok) {
      canvas.innerHTML = '<div class="se-empty">潮流系统图暂不可用</div>';
      return;
    }
    canvas.innerHTML = await resp.text();
    const svg = canvas.querySelector('svg');
    if (!svg) return;
    const vb = (svg.getAttribute('viewBox') || '0 0 2518 2143').split(/\s+/).map(Number);
    sim.svgT.vbW = vb[2] || 2518;
    sim.svgT.vbH = vb[3] || 2143;
    svg.removeAttribute('width');
    svg.removeAttribute('height');
    svg.style.width = `${sim.svgT.vbW}px`;
    svg.style.height = `${sim.svgT.vbH}px`;
    sim.svgLoaded = true;

    const vp = document.getElementById('ew-svg-viewport');
    if (vp) {
      let drag = false; let moved = false; let sx = 0; let sy = 0; let stx = 0; let sty = 0;
      vp.addEventListener('wheel', (e) => {
        e.preventDefault();
        const r = vp.getBoundingClientRect();
        zoomSimSvg(e.deltaY < 0 ? 1.15 : 0.87, e.clientX - r.left, e.clientY - r.top);
      }, { passive: false });
      vp.addEventListener('pointerdown', (e) => {
        if (e.button !== 0) return;
        drag = true; moved = false; sx = e.clientX; sy = e.clientY; stx = sim.svgT.tx; sty = sim.svgT.ty;
      });
      window.addEventListener('pointermove', (e) => {
        if (!drag) return;
        if (Math.hypot(e.clientX - sx, e.clientY - sy) > 4) moved = true;
        sim.svgT.tx = stx + (e.clientX - sx);
        sim.svgT.ty = sty + (e.clientY - sy);
        applySimSvgTransform();
      });
      window.addEventListener('pointerup', () => { drag = false; });
      vp.addEventListener('click', (e) => {
        if (moved) return;
        const el = e.target.closest('[dev-id], g.mg[dev]');
        if (!el) return;
        const did = el.getAttribute('dev-id') || el.getAttribute('dev');
        if (did && sim.topo?.devices?.[did]) selectSimDevice(did);
      });
    }
    requestAnimationFrame(fitSimSvg);
  }

  function classifySimDevice(dev) {
    const dt = String(dev.device_type || '');
    const nm = String(dev.name || '');
    if (dt === 'ACNode' || dt === 'DCNode' || dt === 'ACRealBs' || dt === 'DCRealBs') return 'bus';
    if (dt === 'ACLoad' || dt === 'DCLoad') return 'load';
    if (nm.includes('储能') || nm.includes('电池') || nm.includes('氢')) return 'storage';
    if (nm.includes('风电') || nm.includes('风机')) return 'wind';
    if (nm.includes('光伏')) return 'pv';
    if (dt === 'DCACConverter' || dt === 'DCDCConverter') return 'converter';
    if (dt === 'ACBranch' || dt === 'DCBranch' || dt === 'ACZeroBranch' || dt === 'ACBreak' || dt === 'DCBreak') return 'branch';
    if (dt === 'ACGenerator' || dt === 'DCGenerator') return 'gen';
    return 'other';
  }

  function evolveDeviceAtSlot(dev, pt, basePt) {
    const kind = classifySimDevice(dev);
    const slots = dev.svg_slots || {};
    const baseLoad = Number(basePt?.load_kw);
    const loadRatio = (Number.isFinite(baseLoad) && baseLoad > 1e-6) ? Math.max(0.0, Number(pt.load_kw || 0) / baseLoad) : 1.0;
    const baseWind = Number(basePt?.wind_kw);
    const windRatio = Number(pt.wind_speed_ms || 0) >= 35
      ? 0
      : ((Number.isFinite(baseWind) && baseWind > 1e-6) ? Math.max(0, Number(pt.wind_kw || 0) / baseWind) : 1.0);
    const basePv = Number(basePt?.pv_kw);
    const pvRatio = (Number.isFinite(basePv) && basePv > 1e-6) ? Math.max(0, Number(pt.pv_kw || 0) / basePv) : 1.0;
    const n1Ld = pt.n1_max_loading_pct != null ? Number(pt.n1_max_loading_pct) : null;
    const n0Ld = pt.n0_max_loading_pct != null ? Number(pt.n0_max_loading_pct) : null;
    const baseN0Ld = basePt?.n0_max_loading_pct != null ? Number(basePt.n0_max_loading_pct) : null;
    const vDrop = (pt.n0_min_v_pu != null && basePt?.n0_min_v_pu != null)
      ? (Number(pt.n0_min_v_pu) - Number(basePt.n0_min_v_pu))
      : 0.0;
    const windCutout = Number(pt.wind_speed_ms || 0) >= 35;
    const depleted = pt.green_alive === 0;

    let alert = false;
    let warn = false;
    const out = {};

    Object.entries(slots).forEach(([mt, slot]) => {
      const baseVal = slot.lf != null ? Number(slot.lf) : NaN;
      const validBase = Number.isFinite(baseVal);
      let val = validBase ? baseVal : null;
      let ldPct = slot.loading_pct != null ? Number(slot.loading_pct) : null;
      const unit = slot.unit || '';

      if (mt === 'voltage') {
        if (validBase && baseVal > 0.1) {
          const vScale = Math.max(0.75, Math.min(1.12, 1.0 + vDrop));
          val = baseVal * vScale;
          if (pt.n1_min_v_pu != null && Number(pt.n1_min_v_pu) < 0.93 && kind === 'bus' && baseVal > 10) {
            warn = true;
            if (pt.n0_min_v_pu != null && Number(pt.n0_min_v_pu) < 0.93) alert = true;
          }
        }
      } else if (mt === 'activePower' || mt === 'current' || mt === 'reactivePower') {
        if (kind === 'wind') {
          if (validBase) val = baseVal * windRatio;
          if (windCutout) alert = true;
        } else if (kind === 'pv') {
          if (validBase) val = baseVal * pvRatio;
        } else if (kind === 'storage') {
          if (validBase && pt.storage_power_kw != null) {
            const stScale = (basePt?.storage_power_kw != null && Math.abs(Number(basePt.storage_power_kw)) > 1e-3)
              ? (Number(pt.storage_power_kw) / Number(basePt.storage_power_kw))
              : 1.0;
            val = baseVal * stScale;
          }
          if (depleted) alert = true;
          else if (pt.storage_soc_pct != null && Number(pt.storage_soc_pct) < 28) warn = true;
        } else if (kind === 'load' || kind === 'gen') {
          if (validBase) val = baseVal * loadRatio;
        } else if (kind === 'converter' || kind === 'branch') {
          const scale = (n0Ld != null && baseN0Ld != null && baseN0Ld > 1e-3) ? Math.max(0.1, n0Ld / baseN0Ld) : 1.0;
          if (validBase) val = baseVal * scale;
          if (ldPct != null) {
            ldPct = Math.min(180, ldPct * scale);
            if (ldPct >= 100) alert = true;
            else if (ldPct >= 80) warn = true;
          }
        }
      }
      out[mt] = { val, ldPct, unit };
    });

    // 若当刻风险明细直接点名该设备，则强制标红告警环
    const slotRisks = sim.risks.filter((r) => Number(r.slot_idx) === Number(pt.slot_idx));
    if (slotRisks.some((r) => (r.device_name || '').includes(dev.name) || (r.contingency_name || '').includes(dev.name))) {
      alert = true;
    }
    return { kind, slots: out, alert, warn };
  }

  function renderSimSvgAtSlot(slotIdx) {
    const svg = document.querySelector('#ew-svg-canvas svg');
    const pts = sim.home?.points || [];
    if (!svg || !sim.topo || !pts.length) return;
    const pt = pts[slotIdx] || pts[0];
    const basePt = pts[0];
    const devices = sim.topo.devices || {};
    const cPower = cssVar('--chart-se', '#38bdf8');
    const cOk = cssVar('--sem-ok', '#34d399');
    const cWarn = cssVar('--sem-warn', '#fbbf24');
    const cBad = cssVar('--sem-danger', '#fb7185');
    const cChg = cssVar('--accent', '#60a5fa');

    svg.querySelectorAll('.se-bad-ring').forEach((n) => n.remove());
    svg.querySelectorAll('.se-bad-device,.se-dev-selected').forEach((n) => n.classList.remove('se-bad-device', 'se-dev-selected'));

    const alertDevIds = [];
    svg.querySelectorAll('g.mg[dev]').forEach((mg) => {
      const did = mg.getAttribute('dev');
      const dev = devices[did];
      if (!dev) return;
      const ev = evolveDeviceAtSlot(dev, pt, basePt);
      if (ev.alert) alertDevIds.push(did);

      mg.querySelectorAll('text').forEach((textEl) => {
        const mv = textEl.querySelector('tspan.mv[mt]');
        if (!mv) return;
        const mt = mv.getAttribute('mt');
        const info = ev.slots[mt];
        if (!info) return;
        const tspans = Array.from(textEl.children).filter((n) => n.tagName.toLowerCase() === 'tspan');
        const unitSpan = tspans.length >= 3 ? tspans[tspans.length - 1] : null;

        if (sim.mode === 'loading' && info.ldPct != null) {
          mv.textContent = fmt(info.ldPct, 1);
          if (unitSpan) unitSpan.textContent = '%';
          mv.setAttribute('fill', info.ldPct >= 100 ? cBad : (info.ldPct >= 80 ? cWarn : cOk));
        } else if (sim.mode === 'voltage' && mt === 'voltage') {
          mv.textContent = info.val != null ? fmt(info.val, 2) : '—';
          if (unitSpan) unitSpan.textContent = info.val != null ? (info.unit || 'V') : '';
          mv.setAttribute('fill', ev.alert ? cBad : (ev.warn ? cWarn : cOk));
        } else {
          mv.textContent = info.val != null ? fmt(info.val, Math.abs(info.val) >= 100 ? 1 : 2) : '—';
          if (unitSpan) unitSpan.textContent = info.val != null ? (info.unit || '') : '';
          let col = cPower;
          if (ev.alert) col = cBad;
          else if (ev.warn) col = cWarn;
          else if (ev.kind === 'storage') col = Number(pt.storage_power_kw || 0) < 0 ? cChg : cOk;
          else if (ev.kind === 'wind' || ev.kind === 'pv') col = cOk;
          mv.setAttribute('fill', col);
        }
      });

      let bg = mg.querySelector('rect.se-mg-bg');
      if (bg) bg.remove();
      try {
        const bb = mg.getBBox();
        if (bb.width > 0 && bb.height > 0) {
          bg = document.createElementNS(SVG_NS, 'rect');
          bg.setAttribute('class', `se-mg-bg${ev.alert ? ' is-bad' : ''}`);
          bg.setAttribute('x', String(bb.x - 5));
          bg.setAttribute('y', String(bb.y - 3));
          bg.setAttribute('width', String(bb.width + 10));
          bg.setAttribute('height', String(bb.height + 6));
          mg.insertBefore(bg, mg.firstChild);
        }
      } catch (_) {}
    });

    Array.from(new Set(alertDevIds)).slice(0, 24).forEach((did) => {
      svg.querySelectorAll(`[dev-id="${CSS.escape(did)}"]`).forEach((el) => {
        if ((el.id || '').startsWith('label_')) return;
        el.classList.add('se-bad-device');
        try {
          const bb = el.getBBox();
          if (bb.width > 0 && bb.height > 0 && el.parentNode) {
            const ring = document.createElementNS(SVG_NS, 'rect');
            ring.setAttribute('class', 'se-bad-ring');
            ring.setAttribute('x', String(bb.x - 10));
            ring.setAttribute('y', String(bb.y - 10));
            ring.setAttribute('width', String(bb.width + 20));
            ring.setAttribute('height', String(bb.height + 20));
            ring.setAttribute('rx', '10');
            if (el.getAttribute('transform')) ring.setAttribute('transform', el.getAttribute('transform'));
            el.parentNode.insertBefore(ring, el);
          }
        } catch (_) {}
      });
    });

    if (sim.selectedDevId) {
      svg.querySelectorAll(`[dev-id="${CSS.escape(sim.selectedDevId)}"]`).forEach((el) => {
        if (!(el.id || '').startsWith('label_')) el.classList.add('se-dev-selected');
      });
    }
  }

  function focusSimDevice(devId) {
    selectSimDevice(devId);
    const svg = document.querySelector('#ew-svg-canvas svg');
    const vp = document.getElementById('ew-svg-viewport');
    if (!svg || !vp) return;
    const el = svg.querySelector(`[dev-id="${CSS.escape(devId)}"]`) || svg.querySelector(`g.mg[dev="${CSS.escape(devId)}"]`);
    if (!el) return;
    try {
      const bb = el.getBBox();
      const r = vp.getBoundingClientRect();
      sim.svgT.scale = Math.max(sim.svgT.scale, 0.85);
      sim.svgT.tx = r.width / 2 - (bb.x + bb.width / 2) * sim.svgT.scale;
      sim.svgT.ty = r.height / 2 - (bb.y + bb.height / 2) * sim.svgT.scale;
      applySimSvgTransform();
    } catch (_) {}
  }

  function selectSimDevice(devId) {
    sim.selectedDevId = devId;
    renderSimSvgAtSlot(sim.slot);
    const dev = sim.topo?.devices?.[devId];
    const pts = sim.home?.points || [];
    const pt = pts[sim.slot];
    const tEl = document.getElementById('ew-sim-dev-title');
    const tpEl = document.getElementById('ew-sim-dev-type');
    const bEl = document.getElementById('ew-sim-dev-body');
    if (!dev || !pt || !bEl) return;
    if (tEl) tEl.textContent = dev.name || devId;
    if (tpEl) tpEl.textContent = dev.device_type || '—';
    const ev = evolveDeviceAtSlot(dev, pt, pts[0]);
    const rows = Object.entries(ev.slots).map(([mt, info]) => `
      <div class="se-insp-row">
        <span>${esc(mt)}</span>
        <strong class="tabular">${fmt(info.val, 2)} ${esc(info.unit)}${info.ldPct != null ? ` (${fmt(info.ldPct, 1)}%)` : ''}</strong>
      </div>`).join('');
    bEl.innerHTML = rows || '<div class="se-empty">点击潮流图上任意设备查看演化态</div>';
  }

  function renderSimSideAndHud(slotIdx) {
    const pts = sim.home?.points || [];
    const pt = pts[slotIdx];
    if (!pt) return;
    const clock = document.getElementById('ew-sim-clock');
    if (clock) clock.textContent = `${pt.time_label} (#${pt.slot_idx}/95)`;
    const slider = document.getElementById('ew-sim-slider');
    if (slider) slider.value = String(slotIdx);

    const hud = document.getElementById('ew-sim-hud');
    if (hud) {
      const aliveCol = pt.green_alive ? 'var(--sem-ok)' : 'var(--sem-danger)';
      hud.innerHTML = `
        <span class="hud-item"><small>时刻</small><strong class="tabular">${esc(pt.time_label)}</strong></span>
        <span class="hud-item"><small>气象</small><strong class="tabular">${fmt(pt.irradiance_wm2, 0)}W/m² · ${fmt(pt.wind_speed_ms, 1)}m/s · ${fmt(pt.ambient_temp_c, 1)}℃</strong></span>
        <span class="hud-item"><small>风+光</small><strong class="tabular" style="color:var(--sem-ok)">${fmt(pt.renewable_kw, 1)} kW</strong></span>
        <span class="hud-item"><small>负荷</small><strong class="tabular" style="color:var(--sem-warn)">${fmt(pt.load_kw, 1)} kW</strong></span>
        <span class="hud-item"><small>储能SOC</small><strong class="tabular" style="color:${aliveCol}">${fmt(pt.storage_soc_pct, 1)}% (${Number(pt.storage_power_kw) >= 0 ? '放' : '充'}${fmt(Math.abs(pt.storage_power_kw || 0), 1)}kW)</strong></span>
        <span class="hud-item"><small>N-1负载/最低V</small><strong class="tabular">${fmt(pt.n1_max_loading_pct, 1)}% / ${fmt(pt.n1_min_v_pu, 3)}pu</strong></span>`;
    }

    const sp = document.getElementById('ew-sim-slot-pill');
    if (sp) {
      sp.className = `se-pill ${pt.risk_level === 'critical' ? 'bad' : (pt.risk_level === 'high' || pt.risk_level === 'medium' ? 'warn' : 'ok')} tabular`;
      sp.textContent = `${pt.time_label} · ${fmt(pt.security_score, 0)}分`;
    }
    const kv = document.getElementById('ew-sim-kv');
    if (kv) {
      kv.innerHTML = `
        <div class="pas-stat-chip"><span>风电 / 光伏</span><strong class="tabular">${fmt(pt.wind_kw, 1)} / ${fmt(pt.pv_kw, 1)} kW</strong></div>
        <div class="pas-stat-chip"><span>负荷 / 净负荷</span><strong class="tabular">${fmt(pt.load_kw, 1)} / ${fmt(pt.net_load_kw, 1)} kW</strong></div>
        <div class="pas-stat-chip"><span>储能 SOC / 充放</span><strong class="tabular">${fmt(pt.storage_soc_pct, 1)}% · ${fmt(pt.storage_power_kw, 1)}kW</strong></div>
        <div class="pas-stat-chip"><span>绿电维生状态</span><strong class="tabular" style="color:${pt.green_alive ? 'var(--sem-ok)' : 'var(--sem-danger)'}">${pt.green_alive ? '绿电自治中' : `缺口 ${fmt(pt.green_deficit_kw, 1)}kW`}</strong></div>`;
    }

    const slotRisks = sim.risks.filter((r) => Number(r.slot_idx) === Number(pt.slot_idx));
    const rc = document.getElementById('ew-sim-risk-cnt');
    if (rc) {
      rc.textContent = String(slotRisks.length);
      rc.className = `se-pill tabular ${slotRisks.length ? 'bad' : 'ok'}`;
    }
    const rl = document.getElementById('ew-sim-risk-list');
    if (rl) {
      rl.innerHTML = slotRisks.length ? slotRisks.slice(0, 12).map((r) => `
        <button type="button" class="se-bad-item" data-ew-risk-dev="${esc(r.device_name || '')}">
          <div class="top"><span>${esc(r.contingency_name || r.category)}</span><span class="tabular">${fmt(r.actual_value, 2)}${esc(r.unit)}</span></div>
          <div class="vals">${esc(r.detail)}</div>
        </button>`).join('') : '<div class="se-empty">当前时刻无越限风险</div>';
      rl.querySelectorAll('[data-ew-risk-dev]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const target = btn.dataset.ewRiskDev || '';
          const match = Object.values(sim.topo?.devices || {}).find((d) => target.includes(d.name) || (d.name && d.name.includes(target)));
          if (match) focusSimDevice(match.dev_id);
        });
      });
    }
    if (sim.selectedDevId) selectSimDevice(sim.selectedDevId);
  }

  function renderSimCurve() {
    const host = document.getElementById('ew-sim-curve');
    const pts = sim.home?.points || [];
    if (!host || !pts.length) return;
    const rect = host.getBoundingClientRect();
    const W = Math.max(420, Math.floor(rect.width || 920));
    const H = Math.max(138, Math.floor(rect.height || 168));
    const pad = { l: 44, r: 42, t: 18, b: 22 };
    const pw = W - pad.l - pad.r;
    const ph = H - pad.t - pad.b;

    let series = [];
    if (sim.chartMode === 'weather') {
      series = [
        { name: '辐照(W/m²)/10', color: 'var(--sem-warn)', data: pts.map((p) => Number(p.irradiance_wm2 || 0) / 10) },
        { name: '风速(m/s)', color: 'var(--accent)', data: pts.map((p) => Number(p.wind_speed_ms || 0)) },
        { name: '气温(℃)', color: '#a78bfa', data: pts.map((p) => Number(p.ambient_temp_c || 0)) },
      ];
    } else if (sim.chartMode === 'loading') {
      series = [
        { name: 'N-1极限负载(%)', color: 'var(--sem-danger)', data: pts.map((p) => Number(p.n1_max_loading_pct || 0)) },
        { name: 'N-0基态负载(%)', color: 'var(--accent)', data: pts.map((p) => Number(p.n0_max_loading_pct || 0)) },
      ];
    } else if (sim.chartMode === 'score') {
      series = [
        { name: '时段评分', color: 'var(--sem-ok)', data: pts.map((p) => Number(p.security_score || 0)) },
        { name: '最低电压(pu)×100', color: 'var(--accent)', data: pts.map((p) => Number(p.n1_min_v_pu || 0) * 100) },
      ];
    } else {
      series = [
        { name: '负荷(kW)', color: 'var(--sem-warn)', data: pts.map((p) => Number(p.load_kw || 0)) },
        { name: '风电+光伏(kW)', color: 'var(--sem-ok)', data: pts.map((p) => Number(p.renewable_kw || 0)) },
        { name: '储能SOC(%)', color: 'var(--accent)', data: pts.map((p) => Number(p.storage_soc_pct || 0)), rightAxis: true },
      ];
    }

    const leftVals = series.filter((s) => !s.rightAxis).flatMap((s) => s.data);
    let minL = Math.min(...leftVals, 0);
    let maxL = Math.max(...leftVals, 10);
    if (maxL - minL < 1) maxL = minL + 10;
    const xAt = (i) => pad.l + (i / Math.max(1, pts.length - 1)) * pw;
    const yL = (v) => pad.t + ph - ((v - minL) / (maxL - minL)) * ph;
    const yR = (v) => pad.t + ph - (Math.max(0, Math.min(100, v)) / 100) * ph;

    // 风险底带
    const stepW = pw / Math.max(1, pts.length);
    const riskBands = pts.map((p, i) => {
      if (p.risk_level === 'critical') return `<rect x="${(xAt(i) - stepW / 2).toFixed(1)}" y="${pad.t}" width="${(stepW + 0.5).toFixed(1)}" height="${ph}" fill="rgba(251,113,133,0.10)"/>`;
      if (p.risk_level === 'high') return `<rect x="${(xAt(i) - stepW / 2).toFixed(1)}" y="${pad.t}" width="${(stepW + 0.5).toFixed(1)}" height="${ph}" fill="rgba(249,115,22,0.08)"/>`;
      return '';
    }).join('');

    const gridY = [0, 0.25, 0.5, 0.75, 1].map((r) => {
      const y = pad.t + ph * (1 - r);
      const val = minL + (maxL - minL) * r;
      return `<line x1="${pad.l}" y1="${y.toFixed(1)}" x2="${W - pad.r}" y2="${y.toFixed(1)}" stroke="var(--border-color)" stroke-dasharray="2 3" opacity="0.55"/>
        <text x="${pad.l - 5}" y="${(y + 3).toFixed(1)}" text-anchor="end" fill="var(--text-muted)" font-size="10">${val.toFixed(0)}</text>`;
    }).join('');

    const xTicks = [0, 12, 24, 36, 48, 60, 72, 84, 95].filter((i) => i < pts.length).map((i) => {
      const x = xAt(i);
      return `<text x="${x.toFixed(1)}" y="${H - 5}" text-anchor="middle" fill="var(--text-muted)" font-size="10">${esc(pts[i].time_label)}</text>`;
    }).join('');

    const paths = series.map((s) => {
      const d = s.data.map((v, i) => `${i === 0 ? 'M' : 'L'}${xAt(i).toFixed(1)},${(s.rightAxis ? yR(v) : yL(v)).toFixed(1)}`).join(' ');
      const cx = xAt(sim.slot);
      const cy = s.rightAxis ? yR(s.data[sim.slot]) : yL(s.data[sim.slot]);
      return `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="${s.rightAxis ? 1.8 : 2}" ${s.rightAxis ? 'stroke-dasharray="4 3"' : ''}/>
        <circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="4" fill="${s.color}" stroke="var(--bg-surface)" stroke-width="1.5"/>`;
    }).join('');

    const curX = xAt(sim.slot);
    const curPt = pts[sim.slot];
    const legend = series.map((s, idx) => `
      <g transform="translate(${pad.l + idx * 124}, 11)">
        <line x1="0" y1="-3" x2="14" y2="-3" stroke="${s.color}" stroke-width="2" ${s.rightAxis ? 'stroke-dasharray="3 2"' : ''}/>
        <text x="18" y="0" fill="var(--text-secondary)" font-size="10.5">${esc(s.name)}</text>
      </g>`).join('');

    host.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" style="display:block;width:100%;height:100%">
      ${riskBands}${gridY}${xTicks}${paths}
      <line x1="${curX.toFixed(1)}" y1="${pad.t}" x2="${curX.toFixed(1)}" y2="${pad.t + ph}" stroke="var(--accent)" stroke-width="1.6"/>
      <rect x="${Math.min(W - 76, Math.max(pad.l, curX - 28)).toFixed(1)}" y="${pad.t}" width="56" height="16" rx="4" fill="var(--accent)"/>
      <text x="${Math.min(W - 48, Math.max(pad.l + 28, curX)).toFixed(1)}" y="${pad.t + 11.5}" text-anchor="middle" fill="#08111f" font-size="10" font-weight="700">${esc(curPt.time_label)}</text>
      ${legend}
    </svg>`;

    const pickFromEvent = (ev) => {
      const box = host.getBoundingClientRect();
      const rx = ev.clientX - box.left;
      const ratio = Math.max(0, Math.min(1, (rx - pad.l) / Math.max(1, pw)));
      const idx = Math.round(ratio * (pts.length - 1));
      if (idx !== sim.slot) setSimSlot(idx);
    };
    let scrubbing = false;
    host.onpointerdown = (ev) => { scrubbing = true; pauseSimPlay(); pickFromEvent(ev); };
    host.onpointermove = (ev) => { if (scrubbing) pickFromEvent(ev); };
    host.onpointerup = () => { scrubbing = false; };
    host.onpointerleave = () => { scrubbing = false; };
  }

  function setSimSlot(idx) {
    const pts = sim.home?.points || [];
    if (!pts.length) return;
    sim.slot = ((idx % pts.length) + pts.length) % pts.length;
    renderSimSvgAtSlot(sim.slot);
    renderSimSideAndHud(sim.slot);
    renderSimCurve();
  }

  function pauseSimPlay() {
    sim.playing = false;
    if (sim.timer) { clearInterval(sim.timer); sim.timer = null; }
    const btn = document.getElementById('btn-sim-play');
    if (btn) btn.textContent = '▶ 推演';
  }

  function toggleSimPlay() {
    if (sim.playing) {
      pauseSimPlay();
      return;
    }
    sim.playing = true;
    const btn = document.getElementById('btn-sim-play');
    if (btn) btn.textContent = '⏸ 暂停';
    sim.timer = setInterval(() => setSimSlot(sim.slot + 1), sim.speedMs);
  }

  async function loadScenarioPage() {
    await ensureSimSvgLoaded();
    const [home, topo, risksRes] = await Promise.all([
      apiGet('/api/ew/home'),
      apiGet('/api/lf/topology-values').catch(() => ({ devices: {} })),
      apiGet('/api/ew/risks?limit=500').catch(() => ({ rows: [] })),
    ]);
    sim.home = home;
    sim.topo = topo;
    sim.risks = risksRes.rows || [];
    const latest = home.latest;
    const lp = document.getElementById('ew-sc-level-pill');
    const mt = document.getElementById('ew-sc-meta');
    if (lp && latest) {
      const hasSc = latest.security_score != null;
      lp.className = `se-pill ${hasSc ? levelTone(latest.risk_level) : 'neutral'}`;
      lp.textContent = hasSc ? `${latest.risk_level} · ${latest.health_grade}级` : (latest.risk_level || '无数据');
    }
    if (mt && latest) {
      const survStr = latest.green_survival_hours != null
        ? `${latest.green_survival_capped ? '≥' : ''}${fmt(latest.green_survival_hours, 2)}h`
        : '—';
      mt.textContent = `#${latest.ew_run_id} · ${latest.scenario_label || '—'} · 绿电维生 ${survStr}`;
    }
    const scSel = document.getElementById('ew-sc-scenario');
    if (scSel && Array.isArray(home.scenarios)) {
      scSel.innerHTML = home.scenarios.map((s) => `<option value="${esc(s.key)}">${esc(s.label)}</option>`).join('');
      scSel.value = (home.params && home.params.forecast_scenario) || 'auto';
    }
    const dsEl = document.getElementById('ew-sim-ds-badges');
    const ds = latest?.weather_snapshot?.data_sources || {};
    if (dsEl) {
      dsEl.innerHTML = ['renewgen', 'load', 'weather'].map((k) => {
        const it = ds[k] || {};
        const ok = Boolean(it.connected);
        const stTxt = ok ? `${it.rows}点` : (it.exists ? '空表' : '缺失');
        return `<span class="se-pill ${ok ? 'ok' : 'bad'}" title="${esc(it.path || '')}">${k}.db:${stTxt}</span>`;
      }).join('');
    }
    const jump = document.getElementById('ew-svg-jump');
    if (jump && topo?.devices) {
      const list = Object.values(topo.devices).sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')));
      jump.innerHTML = '<option value="">定位设备…</option>' + list.map((d) => `<option value="${esc(d.dev_id)}">${esc(d.name)} (${esc(d.device_type)})</option>`).join('');
    }
    const pts = home.points || [];
    if (!pts.length) {
      const hud = document.getElementById('ew-sim-hud');
      if (hud) hud.innerHTML = '<span class="hud-item"><strong>无预测库数据</strong><small>请点击右上「预测与覆写」选择预测库或录入时段数据</small></span>';
      const curveHost = document.getElementById('ew-sim-curve');
      if (curveHost) curveHost.innerHTML = '<div class="se-empty">暂无预测趋势数据（缺少 renewgen.db / load.db / weather.db 或手工覆写）</div>';
      const kv = document.getElementById('ew-sim-kv');
      if (kv) kv.innerHTML = '<div class="se-empty" style="grid-column:span 2">—</div>';
      const rl = document.getElementById('ew-sim-risk-list');
      if (rl) rl.innerHTML = '<div class="se-empty">—</div>';
      return;
    }
    setSimSlot(Math.min(sim.slot, pts.length - 1));
  }

  /* ==================== 6. 绿电维生专属页 ==================== */
  async function loadGreenPage() {
    const home = await apiGet('/api/ew/home');
    _homeData = home;
    const latest = home.latest;
    const pts = home.points || [];
    if (!latest) return;

    const hasSurv = latest.green_survival_hours != null && Number.isFinite(Number(latest.green_survival_hours));
    const h = hasSurv ? Number(latest.green_survival_hours) : null;
    const capped = Number(latest.green_survival_capped) === 1;
    const gTone = hasSurv ? survTone(h, capped) : 'neutral';
    const pill = document.getElementById('ew-gr-pill');
    const meta = document.getElementById('ew-gr-meta');
    if (pill) {
      pill.className = `se-pill ${gTone} tabular`;
      pill.textContent = !hasSurv ? '无数据' : (capped ? `纯绿电 ≥${h.toFixed(1)}h` : `纯绿电 ${h.toFixed(2)}h`);
    }
    if (meta) {
      meta.textContent = `${latest.scenario_label || '—'} · 初始SOC ${latest.storage_init_soc_pct != null ? `${fmt(latest.storage_init_soc_pct, 1)}%` : '—'} · 24h最低 ${latest.storage_min_soc_24h_pct != null ? `${fmt(latest.storage_min_soc_24h_pct, 1)}%` : '—'}`;
    }

    const hero = document.getElementById('ew-gr-hero');
    if (hero) {
      const hasH2 = latest.green_survival_with_h2_hours != null && Number.isFinite(Number(latest.green_survival_with_h2_hours));
      const hasNoRen = latest.green_survival_no_ren_hours != null && Number.isFinite(Number(latest.green_survival_no_ren_hours));
      const hasMinSoc = latest.storage_min_soc_24h_pct != null && Number.isFinite(Number(latest.storage_min_soc_24h_pct));
      const hasDef = latest.deficit_total_kwh != null && Number.isFinite(Number(latest.deficit_total_kwh));
      const tiles = [
        {
          tone: gTone, lbl: '纯电化学绿电维生时长',
          badge: !hasSurv ? '缺少预测库/SOC' : (capped ? `外推 ${fmt(latest.green_survival_extrap_hours, 1)}h` : `${latest.green_exhaust_time || '—'} 触底`),
          val: !hasSurv ? '—' : `${capped ? '≥' : ''}${h.toFixed(capped ? 1 : 2)}<small>h</small>`,
          sub: hasSurv ? '零柴发 · 仅依赖风光与电化学储能' : '请在「态势推演 → 预测与覆写」配置数据源',
          pct: hasSurv ? Math.min(100, (h / 24) * 100) : 0,
        },
        {
          tone: hasNoRen ? 'accent' : 'neutral', lbl: '无风光纯储能保底',
          badge: latest.storage_cold_factor != null ? `低温折减 ${fmt(Number(latest.storage_cold_factor) * 100, 1)}%` : '—',
          val: hasNoRen ? `${fmt(latest.green_survival_no_ren_hours, 2)}<small>h</small>` : '—',
          sub: latest.storage_total_kwh ? `可用 ${fmt(latest.storage_usable_kwh, 1)} / ${fmt(latest.storage_total_kwh, 0)} kWh` : 'devices.db 无电化学储能',
          pct: hasNoRen ? Math.min(100, (Number(latest.green_survival_no_ren_hours) / 12) * 100) : 0,
        },
        {
          tone: hasH2 ? 'ok' : 'neutral', lbl: '含储氢扩展维生',
          badge: hasH2 ? '绿氢协同' : '无氢电容量字段',
          val: hasH2 ? `${fmt(latest.green_survival_with_h2_hours, 1)}<small>h</small>` : '—',
          sub: hasH2 ? '电化学储能 + 储氢燃料电池协同' : 'devices.db HydroStorage 未定义电容量',
          pct: hasH2 ? Math.min(100, (Number(latest.green_survival_with_h2_hours) / 72) * 100) : 0,
        },
        {
          tone: !hasMinSoc ? 'neutral' : (Number(latest.storage_min_soc_24h_pct) <= 16 ? 'bad' : 'ok'), lbl: '24h 最低储能 SOC',
          badge: latest.storage_init_soc_pct != null ? `初 ${fmt(latest.storage_init_soc_pct, 1)}%` : '无SOC',
          val: hasMinSoc ? `${fmt(latest.storage_min_soc_24h_pct, 1)}<small>%</small>` : '—',
          sub: latest.storage_max_discharge_kw ? `最大放电能力 ${fmt(latest.storage_max_discharge_kw, 0)} kW` : '—',
          pct: hasMinSoc ? Number(latest.storage_min_soc_24h_pct) : 0,
        },
        {
          tone: !hasDef ? 'neutral' : (Number(latest.deficit_total_kwh) > 0 ? 'bad' : 'ok'), lbl: '24h 绿电缺口 / 占比',
          badge: latest.green_renewable_share_pct != null ? `占比 ${fmt(latest.green_renewable_share_pct, 1)}%` : '—',
          val: hasDef ? `${fmt(latest.deficit_total_kwh, 1)}<small>kWh</small>` : '—',
          sub: latest.max_deficit_kw != null ? `最大缺口 ${fmt(latest.max_deficit_kw, 1)} kW` : '—',
          pct: latest.green_renewable_share_pct != null ? Math.min(100, Number(latest.green_renewable_share_pct)) : 0,
        },
      ];
      hero.innerHTML = tiles.map((t) => `
        <div class="pas-hero-tile tone-${t.tone}">
          <div class="pas-hero-top"><span class="pas-hero-lbl">${esc(t.lbl)}</span><span class="pas-hero-badge ${t.tone} tabular">${esc(t.badge)}</span></div>
          <div class="pas-hero-val-row"><div class="pas-hero-val ${t.tone === 'bad' ? 'bad' : (t.tone === 'ok' ? 'ok' : '')} tabular">${t.val}</div><div class="pas-hero-sub tabular" title="${esc(t.sub)}">${esc(t.sub)}</div></div>
          <div class="pas-hero-meter"><i style="width:${t.pct > 0 ? Math.max(4, Math.min(100, t.pct)).toFixed(1) : '0'}%"></i></div>
        </div>`).join('');
    }

    const badge = document.getElementById('ew-gr-badge');
    if (badge) { badge.className = `se-pill ${gTone} tabular`; badge.textContent = !hasSurv ? '无数据' : (capped ? '24h+ 可持续' : `${h.toFixed(2)}h`); }
    const gauge = document.getElementById('ew-gr-gauge');
    if (gauge) {
      if (!hasSurv) {
        gauge.innerHTML = '<div class="ew-gauge-fallback tabular"><strong style="color:var(--text-muted)">—</strong><span>缺少预测库或储能实时 SOC</span></div>';
      } else if (window.PAS_KIT?.renderGauge) {
        window.PAS_KIT.renderGauge(gauge, {
          value: Math.min(24, h), max: 24,
          label: capped ? `≥24h（外推 ${fmt(latest.green_survival_extrap_hours, 1)}h）` : `${latest.green_exhaust_time || '—'} 触底`,
          unit: 'h',
          color: gTone === 'ok' ? 'var(--sem-ok)' : (gTone === 'bad' ? 'var(--sem-danger)' : 'var(--sem-warn)'),
        });
      }
    }
    const chips = document.getElementById('ew-gr-chips');
    if (chips) {
      chips.innerHTML = `
        <div class="pas-stat-chip"><span>可用电化学储能</span><strong class="tabular">${fmt(latest.storage_usable_kwh, 1)} kWh</strong></div>
        <div class="pas-stat-chip"><span>绿电负荷占比</span><strong class="tabular">${fmt(latest.green_renewable_share_pct, 1)}%</strong></div>`;
    }
    const curSc = document.getElementById('ew-gr-cur-sc');
    if (curSc) curSc.textContent = latest.scenario_label || '—';

    const scBtns = document.getElementById('ew-gr-sc-btns');
    if (scBtns && Array.isArray(home.scenarios)) {
      const curKey = home.params?.forecast_scenario || 'auto';
      scBtns.innerHTML = home.scenarios.map((s) => `
        <button type="button" class="se-btn mini ${s.key === curKey ? 'primary' : ''}" data-gr-sc="${esc(s.key)}">${esc(s.label)}</button>`).join('');
      scBtns.querySelectorAll('[data-gr-sc]').forEach((b) => {
        b.addEventListener('click', () => triggerRun(b.dataset.grSc));
      });
    }

    const pf = document.getElementById('ew-gr-param-form');
    if (pf && home.params) {
      ['storage_min_soc', 'storage_max_soc', 'storage_eff', 'include_hydrogen'].forEach((k) => {
        const el = pf.elements.namedItem(k);
        if (el && home.params[k] != null) el.value = String(home.params[k]);
      });
    }

    const units = Array.isArray(latest.storage_units) ? latest.storage_units : [];
    const uMeta = document.getElementById('ew-gr-units-meta');
    if (uMeta) uMeta.textContent = `${units.length} 台 · 电化学 ${fmt(latest.storage_total_kwh, 0)} kWh · 低温折减 ${latest.storage_cold_factor != null ? `${fmt(Number(latest.storage_cold_factor) * 100, 1)}%` : '—'}`;
    const uTb = document.getElementById('ew-gr-units-tbody');
    if (uTb) {
      const minSoc = Number(home.params?.storage_min_soc || 0.15);
      const cold = Number(latest.storage_cold_factor || 1.0);
      uTb.innerHTML = units.length ? units.map((u) => {
        const hasSoc = u.soc_pct != null && Number.isFinite(Number(u.soc_pct));
        const soc = hasSoc ? Number(u.soc_pct) : null;
        const hasCap = u.capacity_kwh != null && Number.isFinite(Number(u.capacity_kwh));
        const cap = hasCap ? Number(u.capacity_kwh) : null;
        const usable = (hasCap && hasSoc)
          ? (u.domain === 'H2' ? cap * (soc / 100) : Math.max(0, cap * (soc / 100 - minSoc) * cold))
          : null;
        const col = u.domain === 'H2' ? '#a78bfa' : ((soc ?? 0) < 25 ? 'var(--sem-danger)' : ((soc ?? 0) < 45 ? 'var(--sem-warn)' : 'var(--sem-ok)'));
        const srcBadge = u.soc_source === 'scada'
          ? '<span class="se-pill ok">scdfe_d.db 实时</span>'
          : (u.soc_source === 'model' ? '<span class="se-pill neutral">devices.db 模型</span>' : '<span class="se-pill bad">无实时SOC</span>');
        const socCell = hasSoc
          ? `<div class="pas-bar-row" style="grid-template-columns:minmax(60px,1fr) 44px"><div class="track"><i style="width:${Math.min(100, soc).toFixed(1)}%;background:${col}"></i></div><span class="val tabular">${fmt(soc, 1)}%</span></div>`
          : '<span class="se-muted">—</span>';
        return `<tr>
          <td>${esc(u.name)}${u.pressure_mpa != null ? ` <small class="se-muted">${fmt(u.pressure_mpa, 2)}MPa</small>` : ''}</td>
          <td><span class="se-tag">${esc(u.domain || 'AC')}</span></td>
          <td class="tabular">${hasCap ? fmt(cap, 1) : '—'}</td>
          <td class="tabular">${u.max_discharge_kw != null ? fmt(u.max_discharge_kw, 1) : '—'}</td>
          <td>${socCell}</td>
          <td class="tabular">${usable != null ? fmt(usable, 1) : '—'}</td>
          <td>${srcBadge}</td>
        </tr>`;
      }).join('') : '<tr><td colspan="7" class="se-empty">模型/实时库中未检出储能单元</td></tr>';
    }

    const exTag = document.getElementById('ew-gr-exhaust-tag');
    if (exTag) {
      exTag.className = `se-pill ${gTone} tabular`;
      exTag.textContent = capped ? '未来 24h 全程绿电自治' : `${latest.green_exhaust_time || '—'} 触底耗尽`;
    }
    const curveHost = document.getElementById('ew-gr-panel-curve');
    if (curveHost) {
      const exhaustSlot = (!capped && latest.green_exhaust_slot != null) ? Number(latest.green_exhaust_slot) : null;
      renderMultiLineChart(curveHost, {
        labels: pts.map((p) => p.time_label),
        series: [
          { name: '预测负荷(kW)', color: 'var(--sem-warn)', data: pts.map((p) => Number(p.load_kw || 0)), area: true },
          { name: '风电+光伏(kW)', color: 'var(--sem-ok)', data: pts.map((p) => Number(p.renewable_kw || 0)), area: true },
          { name: '储能SOC(%)', color: 'var(--accent)', data: pts.map((p) => Number(p.storage_soc_pct || 0)), rightAxis: true },
        ],
        unit: 'kW',
        exhaustSlot,
        exhaustLabel: latest.green_exhaust_time ? `${latest.green_exhaust_time} 触底` : '',
      });
    }

    const pTb = document.getElementById('ew-gr-points-tbody');
    if (pTb) {
      pTb.innerHTML = pts.map((p) => `
        <tr class="${p.green_alive ? '' : 'row-bad'}">
          <td class="tabular">${p.slot_idx}</td>
          <td class="tabular">${esc(p.time_label)}</td>
          <td class="tabular">${fmt(p.ambient_temp_c, 1)}</td>
          <td class="tabular">${fmt(p.wind_kw, 1)}</td>
          <td class="tabular">${fmt(p.pv_kw, 1)}</td>
          <td class="tabular" style="color:var(--sem-ok)">${fmt(p.renewable_kw, 1)}</td>
          <td class="tabular">${fmt(p.load_kw, 1)}</td>
          <td class="tabular">${fmt(p.net_load_kw, 1)}</td>
          <td class="tabular">${Number(p.storage_power_kw) >= 0 ? '+' : ''}${fmt(p.storage_power_kw, 1)}</td>
          <td class="tabular" style="color:${p.green_alive ? 'var(--sem-ok)' : 'var(--sem-danger)'}">${fmt(p.storage_soc_pct, 1)}%</td>
          <td class="tabular" style="color:${Number(p.green_deficit_kw) > 0 ? 'var(--sem-danger)' : 'var(--text-secondary)'}">${fmt(p.green_deficit_kw, 1)}</td>
          <td><span class="se-pill ${p.green_alive ? 'ok' : 'bad'}">${p.green_alive ? '自治' : '耗尽'}</span></td>
        </tr>`).join('');
    }
  }

  async function triggerRun(scenario = '') {
    try {
      showNotice('正在执行未来 24h 96 点预警与绿电维生计算…');
      await apiPost('/api/ew/run', scenario ? { scenario, source: 'manual' } : { source: 'manual' });
      showNotice('EW 预警计算完成');
      await reloadPage();
    } catch (err) {
      showNotice(err.message || 'EW 执行失败', true);
    }
  }

  async function reloadPage() {
    try {
      if (view === 'home') await loadHome();
      else if (view === 'scenario') await loadScenarioPage();
      else if (view === 'risks') await loadRisksPage();
      else if (view === 'green') await loadGreenPage();
      else if (view === 'config') await loadConfigPage();
      else if (view === 'logs') await loadLogsPage();
    } catch (err) {
      showNotice(err.message || '加载失败', true);
    }
  }

  function bindEvents() {
    document.getElementById('btn-run-ew')?.addEventListener('click', () => triggerRun());
    if (!common) document.getElementById('btn-refresh')?.addEventListener('click', reloadPage);
    document.getElementById('btn-ew-apply-scenario')?.addEventListener('click', () => {
      const sc = document.getElementById('ew-scenario-select')?.value || 'auto';
      triggerRun(sc);
    });
    /* 态势推演页专属交互绑定 */
    document.getElementById('btn-ew-sc-run')?.addEventListener('click', () => {
      const sc = document.getElementById('ew-sc-scenario')?.value || 'auto';
      pauseSimPlay();
      triggerRun(sc);
    });
    document.getElementById('ew-sc-scenario')?.addEventListener('change', (e) => {
      pauseSimPlay();
      triggerRun(e.target.value || 'auto');
    });
    document.getElementById('btn-sim-play')?.addEventListener('click', toggleSimPlay);
    document.getElementById('btn-sim-prev')?.addEventListener('click', () => { pauseSimPlay(); setSimSlot(sim.slot - 1); });
    document.getElementById('btn-sim-next')?.addEventListener('click', () => { pauseSimPlay(); setSimSlot(sim.slot + 1); });
    document.getElementById('ew-sim-slider')?.addEventListener('input', (e) => { pauseSimPlay(); setSimSlot(Number(e.target.value)); });
    document.getElementById('ew-sim-speed')?.addEventListener('change', (e) => {
      sim.speedMs = Math.max(120, Number(e.target.value) || 450);
      if (sim.playing) { pauseSimPlay(); toggleSimPlay(); }
    });
    document.getElementById('ew-svg-mode')?.addEventListener('change', (e) => {
      sim.mode = e.target.value || 'power';
      renderSimSvgAtSlot(sim.slot);
    });
    document.getElementById('ew-svg-jump')?.addEventListener('change', (e) => {
      if (e.target.value) focusSimDevice(e.target.value);
    });
    document.getElementById('btn-ew-zoom-in')?.addEventListener('click', () => zoomSimSvg(1.2));
    document.getElementById('btn-ew-zoom-out')?.addEventListener('click', () => zoomSimSvg(0.84));
    document.getElementById('btn-ew-zoom-fit')?.addEventListener('click', fitSimSvg);
    document.querySelectorAll('[data-ew-sim-chart]').forEach((btn) => {
      btn.addEventListener('click', () => {
        sim.chartMode = btn.dataset.ewSimChart;
        document.querySelectorAll('[data-ew-sim-chart]').forEach((b) => b.classList.toggle('active', b === btn));
        renderSimCurve();
      });
    });
    document.getElementById('btn-ew-sc-config')?.addEventListener('click', async () => {
      await loadConfigPage();
      document.getElementById('ew-cfg-dialog')?.showModal();
    });
    document.getElementById('btn-ew-cfg-close')?.addEventListener('click', () => {
      document.getElementById('ew-cfg-dialog')?.close();
    });
    /* 绿电维生页专属交互绑定 */
    document.querySelectorAll('[data-ew-gr-tab]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.ewGrTab;
        document.querySelectorAll('[data-ew-gr-tab]').forEach((b) => {
          const active = b === btn;
          b.classList.toggle('active', active);
          b.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        const pc = document.getElementById('ew-gr-panel-curve');
        const pt = document.getElementById('ew-gr-panel-table');
        if (pc) pc.hidden = tab !== 'curve';
        if (pt) pt.hidden = tab !== 'table';
      });
    });
    document.getElementById('btn-ew-gr-apply')?.addEventListener('click', async () => {
      const form = document.getElementById('ew-gr-param-form');
      if (!form) return;
      const payload = { trigger_run: true };
      Array.from(form.elements).forEach((el) => { if (el.name) payload[el.name] = el.value; });
      try {
        await apiPost('/api/ew/params', payload);
        showNotice('储能维生边界参数已更新并重算');
        loadGreenPage();
      } catch (err) {
        showNotice(err.message || '参数更新失败', true);
      }
    });
    document.querySelectorAll('[data-ew-chart]').forEach((btn) => {
      btn.addEventListener('click', () => {
        _chartMode = btn.dataset.ewChart;
        document.querySelectorAll('[data-ew-chart]').forEach((b) => b.classList.toggle('active', b === btn));
        if (_homeData) renderMainCurve(_homeData.points || [], _homeData.latest);
      });
    });
    document.querySelectorAll('[data-ew-view-tab]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.ewViewTab;
        document.querySelectorAll('[data-ew-view-tab]').forEach((b) => b.classList.toggle('active', b === btn));
        const pr = document.getElementById('ew-panel-risks');
        const pp = document.getElementById('ew-panel-points');
        const flt = document.getElementById('ew-risk-filters');
        if (pr) pr.hidden = tab !== 'risks';
        if (pp) pp.hidden = tab !== 'points';
        if (flt) flt.style.display = tab === 'risks' ? '' : 'none';
      });
    });
    document.querySelectorAll('[data-ew-log-tab]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.ewLogTab;
        document.querySelectorAll('[data-ew-log-tab]').forEach((b) => {
          const active = b === btn;
          b.classList.toggle('active', active);
          b.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        const pl = document.getElementById('ew-panel-logs');
        const ph = document.getElementById('ew-panel-history');
        const flt = document.getElementById('ew-log-filters');
        if (pl) pl.hidden = tab !== 'logs';
        if (ph) ph.hidden = tab !== 'history';
        if (flt) flt.style.display = tab === 'logs' ? '' : 'none';
      });
    });
    document.getElementById('btn-export-risks')?.addEventListener('click', () => {
      const cat = document.getElementById('ew-f-cat')?.value || 'all';
      const sev = document.getElementById('ew-f-sev')?.value || 'all';
      const q = document.getElementById('ew-f-q')?.value || '';
      window.open(`/api/ew/risks/export?category=${encodeURIComponent(cat)}&severity=${encodeURIComponent(sev)}&q=${encodeURIComponent(q)}`, '_blank');
    });
    ['ew-f-cat', 'ew-f-sev', 'ew-f-q'].forEach((id) => {
      document.getElementById(id)?.addEventListener('input', loadRisksPage);
      document.getElementById(id)?.addEventListener('change', loadRisksPage);
    });
    ['ew-log-level', 'ew-log-q'].forEach((id) => {
      document.getElementById(id)?.addEventListener('input', loadLogsPage);
      document.getElementById(id)?.addEventListener('change', loadLogsPage);
    });
    document.getElementById('btn-ew-save-run')?.addEventListener('click', async () => {
      const form = document.getElementById('ew-params-form');
      if (!form) return;
      const payload = { trigger_run: true };
      Array.from(form.elements).forEach((el) => {
        if (el.name) payload[el.name] = el.value;
      });
      try {
        await apiPost('/api/ew/params', payload);
        showNotice('EW 参数已保存并完成 96 点重算');
        await loadConfigPage();
        if (view === 'scenario') {
          document.getElementById('ew-cfg-dialog')?.close();
          await loadScenarioPage();
        }
      } catch (err) {
        showNotice(err.message || '保存失败', true);
      }
    });
    document.getElementById('btn-ew-reset-params')?.addEventListener('click', () => {
      const doReset = async () => {
        await apiPost('/api/ew/params/reset');
        showNotice('已恢复默认参数');
        await loadConfigPage();
        if (view === 'scenario') await loadScenarioPage();
      };
      if (common?.openConfirm) {
        common.openConfirm({
          title: '恢复默认参数',
          desc: '确认将 EW 预警阈值、储能 SOC 保护限值及三大预测库路径恢复为出厂默认值？',
          okText: '确认恢复',
          onConfirm: doReset,
        });
      } else {
        doReset();
      }
    });
    document.getElementById('ew-ovr-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const g = (id) => document.getElementById(id)?.value;
      const sf = g('ovr-slot-from');
      const st = g('ovr-slot-to');
      const payload = {
        irradiance_wm2: g('ovr-irr'),
        wind_speed_ms: g('ovr-wind'),
        ambient_temp_c: g('ovr-temp'),
        wind_kw: g('ovr-wkw'),
        pv_kw: g('ovr-pkw'),
        load_kw: g('ovr-lkw'),
      };
      if (sf !== undefined && sf !== '') {
        payload.slot_from = Number(sf);
        payload.slot_to = st !== undefined && st !== '' ? Number(st) : Number(sf);
      } else {
        payload.slot_idx = Number(g('ovr-slot'));
      }
      try {
        const res = await apiPost('/api/ew/overrides', payload);
        const cnt = res?.data?.count || 1;
        showNotice(cnt > 1 ? `已批量写入 ${cnt} 个时段覆写` : '已保存单点预测覆写');
        await loadConfigPage();
        if (view === 'scenario') await triggerRun();
      } catch (err) {
        showNotice(err.message || '保存覆写失败', true);
      }
    });
    document.getElementById('btn-ew-ovr-clear')?.addEventListener('click', () => {
      const doClear = async () => {
        await apiPost('/api/ew/overrides/clear');
        showNotice('已清空手工覆写');
        await loadConfigPage();
        if (view === 'scenario') await triggerRun();
      };
      if (common?.openConfirm) {
        common.openConfirm({
          title: '清空预测覆写',
          desc: '确认清空全部 96 点手工预测覆写？清空后将恢复采用三大预测库或所选演变剧本数据。',
          okText: '确认清空',
          onConfirm: doClear,
        });
      } else {
        doClear();
      }
    });
    window.addEventListener('pas-weather-updated', () => triggerRun());
    window.addEventListener('resize', () => {
      if (view === 'home' && _homeData) renderMainCurve(_homeData.points || [], _homeData.latest);
      if (view === 'scenario' && sim.home) renderSimCurve();
      if (view === 'green' && _homeData) loadGreenPage();
    });
  }

  common?.initShell({ onRefresh: reloadPage });
  bindEvents();
  reloadPage();
})();
