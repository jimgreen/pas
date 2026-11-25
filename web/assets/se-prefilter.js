/* 状态估计预过滤量测管理独立页 */
(() => {
  'use strict';

  const I18N = {
    'zh-CN': {
      'title.prefilter': '预过滤量测管理',
      'kpi.total': '预过滤量测',
      'kpi.rule_hit': '规则命中',
      'kpi.kernel': '内核预过滤',
      'kpi.rules': '预过滤规则',
      'tab.results': '预过滤明细',
      'tab.rules': '预过滤规则',
      'tab.analysis': '趋势与分布',
      'origin.rule': '规则命中',
      'origin.kernel': '内核预过滤',
      'origin.policy': '策略屏蔽',
      'rule.range': '上下限越界',
      'rule.force': '强制预过滤',
      'scope.type': '按设备类 (*)',
      'scope.device': '按单设备',
      'btn.add_rule': '+ 新增规则',
      'dlg.rule_title': '预过滤规则',
      'ph.search': '筛选设备/量测',
      'ana.trend_title': '预过滤数量趋势',
      'ana.by_reason': '按原因分布',
      'ana.by_devtype': '按设备类型分布',
      'col.origin': '来源',
      'col.scope': '作用域',
      'col.device_type': '设备类型',
      'col.device_name': '设备',
      'col.metric': '指标',
      'col.value': '实测值',
      'col.range': '允许范围',
      'col.rule_type': '规则',
      'col.min': '下限 Min',
      'col.max': '上限 Max',
      'col.status': '状态',
      'col.reason': '原因',
      'col.note': '备注',
      'col.ops': '操作',
      'act.locate': '定位',
      'act.to_pseudo': '转伪量测',
      'act.enable': '启用',
      'act.disable': '停用',
      'msg.saved': '已保存',
      'msg.deleted': '已删除',
      'msg.to_pseudo': '已生成伪量测定义',
      'confirm.del_title': '删除预过滤规则',
      'confirm.del_desc': '确认删除该预过滤规则？',
    },
    'en-US': {
      'title.prefilter': 'Prefiltered Measurements',
      'kpi.total': 'Prefiltered',
      'kpi.rule_hit': 'Rule Hits',
      'kpi.kernel': 'Kernel Filter',
      'kpi.rules': 'Filter Rules',
      'tab.results': 'Prefiltered List',
      'tab.rules': 'Filter Rules',
      'tab.analysis': 'Trend & Breakdown',
      'origin.rule': 'Rule Hit',
      'origin.kernel': 'Kernel',
      'origin.policy': 'Policy',
      'rule.range': 'Range Limit',
      'rule.force': 'Force Filter',
      'scope.type': 'By Type (*)',
      'scope.device': 'By Device',
      'btn.add_rule': '+ Add Rule',
      'dlg.rule_title': 'Prefilter Rule',
      'ph.search': 'Filter device / metric',
      'ana.trend_title': 'Prefiltered Count Trend',
      'ana.by_reason': 'By Reason',
      'ana.by_devtype': 'By Device Type',
      'col.origin': 'Origin',
      'col.scope': 'Scope',
      'col.device_type': 'Device Type',
      'col.device_name': 'Device',
      'col.metric': 'Metric',
      'col.value': 'Value',
      'col.range': 'Range',
      'col.rule_type': 'Rule',
      'col.min': 'Min',
      'col.max': 'Max',
      'col.status': 'Status',
      'col.reason': 'Reason',
      'col.note': 'Note',
      'col.ops': 'Actions',
      'act.locate': 'Locate',
      'act.to_pseudo': 'To Pseudo',
      'act.enable': 'On',
      'act.disable': 'Off',
      'msg.saved': 'Saved',
      'msg.deleted': 'Deleted',
      'msg.to_pseudo': 'Converted to pseudo measurement',
      'confirm.del_title': 'Delete Prefilter Rule',
      'confirm.del_desc': 'Delete this prefilter rule?',
    },
    'ru-RU': {
      'title.prefilter': 'Предфильтр измерений',
      'kpi.total': 'Отфильтровано',
      'kpi.rule_hit': 'По правилам',
      'kpi.kernel': 'Ядро SE',
      'kpi.rules': 'Правила',
      'tab.results': 'Отфильтрованные',
      'tab.rules': 'Правила фильтра',
      'tab.analysis': 'Тренд и причины',
      'origin.rule': 'Правило',
      'origin.kernel': 'Ядро',
      'origin.policy': 'Блокировка',
      'rule.range': 'Диапазон',
      'rule.force': 'Принудительно',
      'scope.type': 'По типу (*)',
      'scope.device': 'Устройство',
      'btn.add_rule': '+ Правило',
      'dlg.rule_title': 'Правило предфильтра',
      'ph.search': 'Поиск устройства',
      'ana.trend_title': 'Тренд предфильтрации',
      'ana.by_reason': 'По причинам',
      'ana.by_devtype': 'По типам',
      'col.origin': 'Источник',
      'col.scope': 'Область',
      'col.device_type': 'Тип',
      'col.device_name': 'Устройство',
      'col.metric': 'Параметр',
      'col.value': 'Значение',
      'col.range': 'Диапазон',
      'col.rule_type': 'Правило',
      'col.min': 'Мин',
      'col.max': 'Макс',
      'col.status': 'Статус',
      'col.reason': 'Причина',
      'col.note': 'Прим.',
      'col.ops': 'Действия',
      'act.locate': 'Схема',
      'act.to_pseudo': 'В псевдо',
      'act.enable': 'Вкл',
      'act.disable': 'Выкл',
      'msg.saved': 'Сохранено',
      'msg.deleted': 'Удалено',
      'msg.to_pseudo': 'Создано псевдоизмерение',
      'confirm.del_title': 'Удалить правило',
      'confirm.del_desc': 'Удалить правило предфильтра?',
    },
  };

  const state = {
    catalog: null,
    origin: 'all',
    results: { rows: [], total: 0, limit: 50, offset: 0 },
    rules: [],
    analysis: { trend: [], by_reason: [], by_device_type: [] },
  };

  const common = window.createSECommon(I18N, () => {
    populateFilterSelects();
    renderResults();
    renderRules();
    renderAnalysis();
  });
  const { t, esc, fmtNum, fmtTime, devTypeLabel, api, notify, openConfirm } = common;

  function populateFilterSelects() {
    if (!state.catalog) return;
    const types = Object.keys(state.catalog.meas_metrics || {});
    ['pf-res-type', 'pf-rule-type-filter'].forEach((id) => {
      const sel = document.getElementById(id);
      if (!sel) return;
      const cur = sel.value || 'all';
      sel.innerHTML = `<option value="all">${esc(t('common.all'))}</option>`
        + types.map((dt) => `<option value="${esc(dt)}">${esc(devTypeLabel(dt))} (${esc(dt)})</option>`).join('');
      sel.value = types.includes(cur) ? cur : 'all';
    });
  }

  function syncRuleDialogVisibility() {
    const isDevice = document.getElementById('fr-scope').value === 'device';
    const isRange = document.getElementById('fr-rule-type').value === 'range';
    document.getElementById('fr-dev-wrap').hidden = !isDevice;
    document.getElementById('fr-min-wrap').hidden = !isRange;
    document.getElementById('fr-max-wrap').hidden = !isRange;
  }

  function populateRuleDialogSelects(row = null) {
    const typeSel = document.getElementById('fr-dev-type');
    const devSel = document.getElementById('fr-dev-name');
    const metSel = document.getElementById('fr-metric');
    const metricsMap = state.catalog.meas_metrics || {};
    const devicesMap = state.catalog.devices || {};
    const types = Object.keys(metricsMap).filter((k) => (devicesMap[k] || []).length > 0);
    const listTypes = types.length ? types : Object.keys(metricsMap);

    typeSel.innerHTML = listTypes.map((dt) => `<option value="${esc(dt)}">${esc(devTypeLabel(dt))} (${esc(dt)})</option>`).join('');
    typeSel.value = row && listTypes.includes(row.device_type) ? row.device_type : listTypes[0];

    const refreshSub = (dt, keepDev, keepMet) => {
      const devs = devicesMap[dt] || [];
      devSel.innerHTML = devs.map((d) => `<option value="${esc(d.name)}" data-idx="${d.idx}">${esc(d.name)} (#${d.idx})</option>`).join('');
      if (keepDev && devs.some((d) => d.name === keepDev)) devSel.value = keepDev;

      const mets = Object.entries(metricsMap[dt] || {});
      metSel.innerHTML = mets.map(([m, code]) => `<option value="${esc(m)}">${esc(m)} · ${esc(code)}</option>`).join('');
      if (keepMet && metricsMap[dt] && metricsMap[dt][keepMet]) metSel.value = keepMet;
    };

    refreshSub(typeSel.value, row?.device_name, row?.metric);
    typeSel.onchange = () => refreshSub(typeSel.value, null, null);
  }

  function openRuleDialog(row = null) {
    const dlg = document.getElementById('rule-dialog');
    const form = document.getElementById('rule-form');
    form.reset();
    form.elements.id.value = row ? row.id : '';
    document.getElementById('fr-scope').value = row?.scope || 'device_type';
    populateRuleDialogSelects(row);
    document.getElementById('fr-rule-type').value = row?.rule_type || 'range';
    document.getElementById('fr-enabled').value = row ? String(row.enabled ?? 1) : '1';
    document.getElementById('fr-min').value = row?.min_value ?? '';
    document.getElementById('fr-max').value = row?.max_value ?? '';
    document.getElementById('fr-note').value = row?.note || '';
    syncRuleDialogVisibility();
    dlg.showModal();
  }

  function originPill(origin) {
    const map = {
      rule: ['warn', t('origin.rule')],
      policy: ['bad', t('origin.policy')],
      kernel: ['neutral', t('origin.kernel')],
    };
    const [cls, label] = map[origin] || ['neutral', origin || '—'];
    return `<span class="se-pill ${cls}">${esc(label)}</span>`;
  }

  function fmtRange(minV, maxV, unit) {
    if (minV == null && maxV == null) return '—';
    const lo = minV == null ? '-∞' : fmtNum(minV, 2);
    const hi = maxV == null ? '+∞' : fmtNum(maxV, 2);
    return `[${lo}, ${hi}] ${unit || ''}`.trim();
  }

  function renderResults() {
    const wrap = document.getElementById('pf-res-table');
    const pager = document.getElementById('pf-res-pager');
    const meta = document.getElementById('pf-res-meta');
    const { rows, total, limit, offset } = state.results;
    meta.textContent = `${rows.length} / ${total}`;
    if (!rows.length) {
      wrap.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
      pager.innerHTML = '';
      return;
    }
    wrap.innerHTML = `
      <table class="se-table">
        <thead>
          <tr>
            <th>#</th>
            <th>${esc(t('col.origin'))}</th>
            <th>${esc(t('col.device_type'))}</th>
            <th>${esc(t('col.device_name'))}</th>
            <th>${esc(t('col.metric'))}</th>
            <th>${esc(t('col.value'))}</th>
            <th>${esc(t('col.range'))}</th>
            <th>${esc(t('col.reason'))}</th>
            <th>${esc(t('col.ops'))}</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((r) => `
            <tr>
              <td class="tabular">${r.meas_id}</td>
              <td>${originPill(r.origin)}</td>
              <td>${esc(devTypeLabel(r.device_type))}</td>
              <td><strong>${esc(r.device_name)}</strong></td>
              <td class="tabular">${esc(r.metric || r.meas_type)}</td>
              <td class="tabular">${fmtNum(r.meas_value, 3)} ${esc(r.unit || '')}</td>
              <td class="tabular">${esc(fmtRange(r.min_value, r.max_value, r.unit))}</td>
              <td>${esc(r.reason || '—')}</td>
              <td>
                <div class="se-row-actions">
                  <a class="se-btn mini se-link-btn" href="/se-flow.html?device_type=${encodeURIComponent(r.device_type)}&device_name=${encodeURIComponent(r.device_name)}">${esc(t('act.locate'))}</a>
                  <button type="button" class="se-btn mini" data-act="to-pseudo" data-idx="${r.id}">${esc(t('act.to_pseudo'))}</button>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;

    const pages = Math.max(1, Math.ceil(total / limit));
    const page = Math.floor(offset / limit) + 1;
    pager.innerHTML = `
      <button type="button" class="se-btn mini" id="pf-prev" ${page <= 1 ? 'disabled' : ''}>${esc(t('common.prev'))}</button>
      <span class="tabular">${page} / ${pages}</span>
      <button type="button" class="se-btn mini" id="pf-next" ${page >= pages ? 'disabled' : ''}>${esc(t('common.next'))}</button>`;
    const pPrev = document.getElementById('pf-prev');
    const pNext = document.getElementById('pf-next');
    if (pPrev) pPrev.onclick = () => { state.results.offset = Math.max(0, offset - limit); loadResults(); };
    if (pNext) pNext.onclick = () => { state.results.offset = offset + limit; loadResults(); };
  }

  function renderRules() {
    const wrap = document.getElementById('pf-rule-table');
    if (!state.rules.length) {
      wrap.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
      return;
    }
    wrap.innerHTML = `
      <table class="se-table">
        <thead>
          <tr>
            <th>#</th>
            <th>${esc(t('col.scope'))}</th>
            <th>${esc(t('col.device_type'))}</th>
            <th>${esc(t('col.device_name'))}</th>
            <th>${esc(t('col.metric'))}</th>
            <th>${esc(t('col.rule_type'))}</th>
            <th>${esc(t('col.range'))}</th>
            <th>${esc(t('col.status'))}</th>
            <th>${esc(t('col.note'))}</th>
            <th>${esc(t('col.ops'))}</th>
          </tr>
        </thead>
        <tbody>
          ${state.rules.map((r) => `
            <tr>
              <td class="tabular">${r.id}</td>
              <td><span class="se-tag">${esc(r.scope === 'device' ? t('scope.device') : t('scope.type'))}</span></td>
              <td>${esc(devTypeLabel(r.device_type))}</td>
              <td><strong>${esc(r.device_name)}</strong></td>
              <td class="tabular">${esc(r.metric)}</td>
              <td><span class="se-pill ${r.rule_type === 'force_filter' ? 'warn' : 'info'}">${esc(r.rule_type === 'force_filter' ? t('rule.force') : t('rule.range'))}</span></td>
              <td class="tabular">${esc(fmtRange(r.min_value, r.max_value, r.unit))}</td>
              <td><span class="se-pill ${r.enabled ? 'ok' : 'neutral'}">${esc(r.enabled ? t('common.enabled') : t('common.disabled'))}</span></td>
              <td>${esc(r.note || '—')}</td>
              <td>
                <div class="se-row-actions">
                  <button type="button" class="se-btn mini" data-act="toggle-rule" data-id="${r.id}">${esc(r.enabled ? t('act.disable') : t('act.enable'))}</button>
                  <button type="button" class="se-btn mini" data-act="edit-rule" data-id="${r.id}">${esc(t('action.edit'))}</button>
                  <button type="button" class="se-btn mini danger-ghost" data-act="del-rule" data-id="${r.id}">${esc(t('action.delete'))}</button>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  }

  function renderAnalysis() {
    const chartHost = document.getElementById('pf-trend-chart');
    const trend = state.analysis.trend || [];
    if (!trend.length) {
      chartHost.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
    } else {
      const w = Math.max(360, chartHost.clientWidth || 640);
      const h = Math.max(180, chartHost.clientHeight || 200);
      const pad = { top: 16, right: 32, bottom: 26, left: 42 };
      const plotW = w - pad.left - pad.right;
      const plotH = h - pad.top - pad.bottom;
      const vals = trend.map((d) => Number(d.prefiltered_count || 0));
      const maxY = Math.max(1, ...vals);
      const pts = trend.map((d, idx) => {
        const x = pad.left + (trend.length === 1 ? plotW / 2 : (idx / (trend.length - 1)) * plotW);
        const y = pad.top + plotH - (Number(d.prefiltered_count || 0) / maxY) * plotH;
        return { x, y, d };
      });
      const poly = pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
      const ticks = [0, Math.ceil(maxY / 2), maxY];
      chartHost.innerHTML = `
        <svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}">
          ${ticks.map((v) => {
            const y = pad.top + plotH - (v / maxY) * plotH;
            return `<line x1="${pad.left}" y1="${y}" x2="${w - pad.right}" y2="${y}" stroke="var(--grid-line)" stroke-dasharray="3 3"/>
                    <text x="${pad.left - 6}" y="${y + 4}" text-anchor="end" fill="var(--text-secondary)" font-size="11">${v}</text>`;
          }).join('')}
          <polyline fill="none" stroke="var(--warning)" stroke-width="2" points="${poly}"/>
          ${pts.map((p) => `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="3" fill="var(--warning)"><title>#${p.d.run_id} · ${fmtTime(p.d.calc_time)} · ${p.d.prefiltered_count}</title></circle>`).join('')}
          <text x="${pad.left}" y="${h - 6}" text-anchor="start" fill="var(--text-secondary)" font-size="11">${esc(fmtTime(trend[0].calc_time).slice(5, 16))}</text>
          <text x="${w - pad.right}" y="${h - 6}" text-anchor="end" fill="var(--text-secondary)" font-size="11">${esc(fmtTime(trend[trend.length - 1].calc_time).slice(5, 16))}</text>
        </svg>`;
    }

    const drawBars = (elId, items, labelFn) => {
      const host = document.getElementById(elId);
      if (!items.length) {
        host.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
        return;
      }
      const maxC = Math.max(1, ...items.map((x) => x.count));
      host.innerHTML = items.map((x) => `
        <div class="se-stage-item" style="grid-template-columns: 150px minmax(0,1fr) 48px;">
          <span class="se-tag" title="${esc(labelFn(x))}" style="overflow:hidden;text-overflow:ellipsis">${esc(labelFn(x))}</span>
          <div class="se-stage-track"><div class="se-stage-fill" style="width:${((x.count / maxC) * 100).toFixed(1)}%"></div></div>
          <span class="tabular" style="text-align:right">${x.count}</span>
        </div>`).join('');
    };
    drawBars('pf-reason-bars', state.analysis.by_reason || [], (x) => x.reason);
    drawBars('pf-devtype-bars', state.analysis.by_device_type || [], (x) => devTypeLabel(x.device_type));
  }

  async function loadOverview() {
    const ov = await api('/api/se/prefilter/overview');
    document.getElementById('kpi-pf-total').textContent = ov.total;
    document.getElementById('kpi-pf-rule').textContent = ov.by_rule;
    document.getElementById('kpi-pf-kernel').textContent = ov.by_kernel;
    document.getElementById('kpi-rules-enabled').textContent = ov.rule_enabled;
    document.getElementById('kpi-rules-total').textContent = `/ ${ov.rule_total}`;
    const meta = document.getElementById('pf-run-meta');
    meta.textContent = ov.latest_run ? `Run #${ov.latest_run.run_id} · ${fmtTime(ov.latest_run.calc_time)}` : '—';
  }

  async function loadResults() {
    const dt = document.getElementById('pf-res-type').value || '';
    const q = document.getElementById('pf-res-search').value || '';
    state.results = await api(
      `/api/se/prefilter/results?origin=${encodeURIComponent(state.origin)}&device_type=${encodeURIComponent(dt)}&q=${encodeURIComponent(q)}&limit=${state.results.limit}&offset=${state.results.offset}`,
    );
    renderResults();
  }

  async function loadRules() {
    const dt = document.getElementById('pf-rule-type-filter').value || '';
    const rt = document.getElementById('pf-rule-kind-filter').value || '';
    const q = document.getElementById('pf-rule-search').value || '';
    state.rules = await api(`/api/se/prefilter/rules?device_type=${encodeURIComponent(dt)}&rule_type=${encodeURIComponent(rt)}&q=${encodeURIComponent(q)}`);
    renderRules();
  }

  async function loadAnalysis() {
    const lim = document.getElementById('pf-trend-limit').value || '60';
    state.analysis = await api(`/api/se/prefilter/analysis?limit=${lim}`);
    renderAnalysis();
  }

  async function refreshAll() {
    try {
      if (!state.catalog) {
        state.catalog = await api('/api/se/model-catalog');
        populateFilterSelects();
      }
      await Promise.all([loadOverview(), loadResults(), loadRules(), loadAnalysis()]);
    } catch (err) {
      notify(err.message, true);
    }
  }

  function bindEvents() {
    document.querySelectorAll('#pf-tabs .se-tab').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#pf-tabs .se-tab').forEach((b) => b.classList.toggle('active', b === btn));
        document.querySelectorAll('.se-workspace .se-panel').forEach((p) => p.classList.toggle('active', p.dataset.panel === btn.dataset.view));
        if (btn.dataset.view === 'analysis') renderAnalysis();
      });
    });

    document.querySelectorAll('#pf-origin-seg .seg').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#pf-origin-seg .seg').forEach((b) => b.classList.toggle('active', b === btn));
        state.origin = btn.dataset.origin;
        state.results.offset = 0;
        loadResults();
      });
    });

    document.getElementById('pf-res-type').addEventListener('change', () => { state.results.offset = 0; loadResults(); });
    document.getElementById('pf-res-search').addEventListener('input', () => { state.results.offset = 0; loadResults(); });
    document.getElementById('pf-rule-type-filter').addEventListener('change', loadRules);
    document.getElementById('pf-rule-kind-filter').addEventListener('change', loadRules);
    document.getElementById('pf-rule-search').addEventListener('input', loadRules);
    document.getElementById('pf-trend-limit').addEventListener('change', loadAnalysis);

    document.getElementById('fr-scope').addEventListener('change', syncRuleDialogVisibility);
    document.getElementById('fr-rule-type').addEventListener('change', syncRuleDialogVisibility);
    document.getElementById('btn-add-rule').addEventListener('click', () => openRuleDialog(null));
    document.getElementById('btn-rule-cancel').addEventListener('click', () => document.getElementById('rule-dialog').close());

    document.getElementById('rule-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const scope = document.getElementById('fr-scope').value;
      const devSel = document.getElementById('fr-dev-name');
      const opt = devSel.selectedOptions[0];
      const id = e.target.elements.id.value;
      const minRaw = document.getElementById('fr-min').value.trim();
      const maxRaw = document.getElementById('fr-max').value.trim();
      const payload = {
        scope,
        device_type: document.getElementById('fr-dev-type').value,
        device_idx: scope === 'device' && opt ? Number(opt.dataset.idx) : null,
        device_name: scope === 'device' ? devSel.value : '*',
        metric: document.getElementById('fr-metric').value,
        rule_type: document.getElementById('fr-rule-type').value,
        min_value: minRaw === '' ? null : Number(minRaw),
        max_value: maxRaw === '' ? null : Number(maxRaw),
        enabled: Number(document.getElementById('fr-enabled').value),
        note: document.getElementById('fr-note').value,
      };
      try {
        if (id) {
          await api(`/api/se/prefilter/rules/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
        } else {
          await api('/api/se/prefilter/rules', { method: 'POST', body: JSON.stringify(payload) });
        }
        document.getElementById('rule-dialog').close();
        notify(t('msg.saved'));
        await Promise.all([loadOverview(), loadRules()]);
      } catch (err) {
        notify(err.message, true);
      }
    });

    document.getElementById('pf-res-table').addEventListener('click', async (e) => {
      const btn = e.target.closest('button[data-act="to-pseudo"]');
      if (!btn) return;
      const rid = Number(btn.dataset.idx);
      const row = state.results.rows.find((r) => r.id === rid);
      if (!row || !row.metric) return;
      try {
        await api('/api/se/pseudo/meas', {
          method: 'POST',
          body: JSON.stringify({
            device_type: row.device_type,
            device_idx: row.device_idx,
            device_name: row.device_name,
            metric: row.metric,
            meas_value: row.meas_value ?? 0,
            meas_weight: 1e-4,
            meas_useflag: 1,
            source_mode: 'manual',
            note: `prefilter:${row.reason || ''}`,
          }),
        });
        notify(t('msg.to_pseudo'));
      } catch (err) {
        notify(err.message, true);
      }
    });

    document.getElementById('pf-rule-table').addEventListener('click', async (e) => {
      const btn = e.target.closest('button[data-act]');
      if (!btn) return;
      const id = Number(btn.dataset.id);
      const row = state.rules.find((r) => r.id === id);
      if (!row) return;
      if (btn.dataset.act === 'edit-rule') {
        openRuleDialog(row);
      } else if (btn.dataset.act === 'toggle-rule') {
        try {
          await api(`/api/se/prefilter/rules/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ ...row, enabled: row.enabled ? 0 : 1 }),
          });
          notify(t('msg.saved'));
          await Promise.all([loadOverview(), loadRules()]);
        } catch (err) {
          notify(err.message, true);
        }
      } else if (btn.dataset.act === 'del-rule') {
        openConfirm({
          title: t('confirm.del_title'),
          desc: `${row.device_type}.${row.device_name}.${row.metric} — ${t('confirm.del_desc')}`,
          okText: t('action.delete'),
          onConfirm: async () => {
            try {
              await api(`/api/se/prefilter/rules/${id}`, { method: 'DELETE' });
              notify(t('msg.deleted'));
              await Promise.all([loadOverview(), loadRules()]);
            } catch (err) {
              notify(err.message, true);
            }
          },
        });
      }
    });
  }

  common.initShell({ onRefresh: refreshAll, afterRunSE: refreshAll });
  bindEvents();
  refreshAll();
})();
