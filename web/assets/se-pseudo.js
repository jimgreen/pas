/* 状态估计伪量测与伪状态管理独立页逻辑 */
(() => {
  'use strict';

  const I18N = {
    'zh-CN': {
      'title.pseudo': '伪量测',
      'kpi.defined': '伪量测定义',
      'kpi.defined_sub': '启用 / 总定义',
      'kpi.stat': '伪状态定义',
      'kpi.stat_sub': '开关与运行态覆盖',
      'kpi.res_user': '人工注入结果',
      'kpi.res_user_sub': '本次 SE 已生效',
      'kpi.res_auto': '内核自动补充',
      'kpi.res_auto_sub': '可观测性自动补齐',
      'tab.defines': '伪量测定义',
      'tab.results': '本次伪量测结果',
      'tab.stats': '伪状态定义',
      'filter.enabled_only': '仅看已启用',
      'btn.add_meas': '+ 新增伪量测',
      'btn.add_stat': '+ 新增伪状态',
      'ph.search': '筛选设备/指标',
      'origin.user': '人工定义',
      'origin.auto': '内核补充',
      'dlg.meas_title': '伪量测定义',
      'dlg.stat_title': '伪状态定义',
      'col.device_type': '设备类型',
      'col.device_name': '目标设备',
      'col.metric': '量测指标',
      'col.source_mode': '来源模式',
      'col.value': '设定值',
      'col.se_value': 'SE 估计值',
      'col.residual': '残差 Δ',
      'col.weight': '权重',
      'col.weight_custom': '自定义权重',
      'col.status': '状态',
      'col.stat_val': '强制状态',
      'col.origin': '来源',
      'col.note': '备注 / 原因',
      'col.updated': '更新时间',
      'col.ops': '操作',
      'mode.manual': '人工给定',
      'mode.zero': '零注入约束',
      'mode.bad_replace': '坏量测替代',
      'weight.custom': '自定义…',
      'stat.on': '1 · 合位 / 运行',
      'stat.off': '0 · 分位 / 停运',
      'msg.saved': '配置已保存',
      'msg.deleted': '已删除',
      'confirm.del_meas_title': '删除伪量测',
      'confirm.del_meas_desc': '确认删除该伪量测？',
      'confirm.del_stat_title': '删除伪状态',
      'confirm.del_stat_desc': '确认删除该伪状态？',
      'action.enable': '启用',
      'action.disable': '停用',
      'act.locate': '定位潮流图',
      'act.promote_manual': '固化为人工',
    },
    'en-US': {
      'title.pseudo': 'Pseudo Measurements',
      'kpi.defined': 'Pseudo Definitions',
      'kpi.defined_sub': 'Enabled / Total',
      'kpi.stat': 'Pseudo Status',
      'kpi.stat_sub': 'Breaker & Run Overrides',
      'kpi.res_user': 'User Injected',
      'kpi.res_user_sub': 'Active in Latest SE',
      'kpi.res_auto': 'Kernel Auto-Filled',
      'kpi.res_auto_sub': 'Observability Fill',
      'tab.defines': 'Pseudo Meas Config',
      'tab.results': 'Latest Pseudo Results',
      'tab.stats': 'Pseudo Status Config',
      'filter.enabled_only': 'Enabled Only',
      'btn.add_meas': '+ Add Pseudo Meas',
      'btn.add_stat': '+ Add Pseudo Status',
      'ph.search': 'Filter device / metric',
      'origin.user': 'User Defined',
      'origin.auto': 'Kernel Auto',
      'dlg.meas_title': 'Pseudo Measurement',
      'dlg.stat_title': 'Pseudo Status',
      'col.device_type': 'Device Type',
      'col.device_name': 'Device',
      'col.metric': 'Metric',
      'col.source_mode': 'Mode',
      'col.value': 'Value',
      'col.se_value': 'SE Value',
      'col.residual': 'Residual Δ',
      'col.weight': 'Weight',
      'col.weight_custom': 'Custom Weight',
      'col.status': 'Status',
      'col.stat_val': 'Forced State',
      'col.origin': 'Origin',
      'col.note': 'Note / Reason',
      'col.updated': 'Updated',
      'col.ops': 'Actions',
      'mode.manual': 'Manual',
      'mode.zero': 'Zero Injection',
      'mode.bad_replace': 'Bad Replace',
      'weight.custom': 'Custom…',
      'stat.on': '1 · Closed / Running',
      'stat.off': '0 · Open / Outage',
      'msg.saved': 'Saved successfully',
      'msg.deleted': 'Deleted',
      'confirm.del_meas_title': 'Delete Pseudo Measurement',
      'confirm.del_meas_desc': 'This pseudo measurement will no longer be injected into future SE runs.',
      'confirm.del_stat_title': 'Delete Pseudo Status',
      'confirm.del_stat_desc': 'Live SCADA status will be used on the next SE run.',
      'action.enable': 'Enable',
      'action.disable': 'Disable',
      'act.locate': 'Locate SVG',
      'act.promote_manual': 'Pin as Manual',
    },
    'ru-RU': {
      'title.pseudo': 'Псевдоизмерения',
      'kpi.defined': 'Псевдоизмерения',
      'kpi.defined_sub': 'Вкл / Всего',
      'kpi.stat': 'Псевдостатусы',
      'kpi.stat_sub': 'Выкл. и сост. работы',
      'kpi.res_user': 'Введено вручную',
      'kpi.res_user_sub': 'В последнем SE',
      'kpi.res_auto': 'Авто-дополнение',
      'kpi.res_auto_sub': 'Наблюдаемость',
      'tab.defines': 'Настройка изм.',
      'tab.results': 'Результаты SE',
      'tab.stats': 'Псевдостатусы',
      'filter.enabled_only': 'Только вкл.',
      'btn.add_meas': '+ Добавить изм.',
      'btn.add_stat': '+ Добавить статус',
      'ph.search': 'Поиск устройства',
      'origin.user': 'Вручную',
      'origin.auto': 'Авто ядра',
      'dlg.meas_title': 'Псевдоизмерение',
      'dlg.stat_title': 'Псевдостатус',
      'col.device_type': 'Тип',
      'col.device_name': 'Устройство',
      'col.metric': 'Параметр',
      'col.source_mode': 'Режим',
      'col.value': 'Значение',
      'col.se_value': 'Оценка SE',
      'col.residual': 'Невязка Δ',
      'col.weight': 'Вес',
      'col.weight_custom': 'Свой вес',
      'col.status': 'Статус',
      'col.stat_val': 'Состояние',
      'col.origin': 'Источник',
      'col.note': 'Примечание',
      'col.updated': 'Обновлено',
      'col.ops': 'Действия',
      'mode.manual': 'Вручную',
      'mode.zero': 'Нул. инъекция',
      'mode.bad_replace': 'Замена сбоя',
      'weight.custom': 'Другой…',
      'stat.on': '1 · Вкл / Работа',
      'stat.off': '0 · Откл / Ремонт',
      'msg.saved': 'Сохранено',
      'msg.deleted': 'Удалено',
      'confirm.del_meas_title': 'Удалить псевдоизмерение',
      'confirm.del_meas_desc': 'Это псевдоизмерение больше не будет участвовать в расчёте SE.',
      'confirm.del_stat_title': 'Удалить псевдостатус',
      'confirm.del_stat_desc': 'Вернётся использование телесигналов SCADA.',
      'action.enable': 'Вкл',
      'action.disable': 'Выкл',
      'act.locate': 'На схеме',
      'act.promote_manual': 'Закрепить',
    },
  };

  const state = {
    catalog: null,
    defines: [],
    stats: [],
    results: { rows: [], total: 0, limit: 50, offset: 0 },
    resOrigin: 'all',
  };

  const common = window.createSECommon(I18N, () => {
    populateFilterSelects();
    renderDefines();
    renderResults();
    renderStats();
  });
  const { t, esc, fmtNum, fmtTime, devTypeLabel, api, notify, openConfirm } = common;

  function populateFilterSelects() {
    if (!state.catalog) return;
    const measTypes = Object.keys(state.catalog.meas_metrics || {});
    const statTypes = Object.keys(state.catalog.stat_types || {});

    const fill = (id, list) => {
      const sel = document.getElementById(id);
      if (!sel) return;
      const cur = sel.value || 'all';
      sel.innerHTML = `<option value="all">${esc(t('common.all'))}</option>`
        + list.map((dt) => `<option value="${esc(dt)}">${esc(devTypeLabel(dt))} (${esc(dt)})</option>`).join('');
      sel.value = list.includes(cur) ? cur : 'all';
    };
    fill('def-type-filter', measTypes);
    fill('res-type-filter', measTypes);
    fill('stat-type-filter', statTypes);
  }

  function populateMeasDialogSelects(selectedType, selectedDev, selectedMetric) {
    const typeSel = document.getElementById('fm-dev-type');
    const devSel = document.getElementById('fm-dev-name');
    const metSel = document.getElementById('fm-metric');
    const metricsMap = state.catalog.meas_metrics || {};
    const devicesMap = state.catalog.devices || {};
    const types = Object.keys(metricsMap).filter((k) => (devicesMap[k] || []).length > 0);
    const listTypes = types.length ? types : Object.keys(metricsMap);

    typeSel.innerHTML = listTypes.map((dt) => `<option value="${esc(dt)}">${esc(devTypeLabel(dt))} (${esc(dt)})</option>`).join('');
    typeSel.value = listTypes.includes(selectedType) ? selectedType : listTypes[0];

    const refreshSub = (dt, keepDev, keepMet) => {
      const devs = devicesMap[dt] || [];
      devSel.innerHTML = devs.map((d) => `<option value="${esc(d.name)}" data-idx="${d.idx}">${esc(d.name)} (#${d.idx})</option>`).join('');
      if (keepDev && devs.some((d) => d.name === keepDev)) devSel.value = keepDev;

      const mets = Object.entries(metricsMap[dt] || {});
      metSel.innerHTML = mets.map(([m, code]) => `<option value="${esc(m)}">${esc(m)} · ${esc(code)}</option>`).join('');
      if (keepMet && metricsMap[dt] && metricsMap[dt][keepMet]) metSel.value = keepMet;
    };

    refreshSub(typeSel.value, selectedDev, selectedMetric);
    typeSel.onchange = () => refreshSub(typeSel.value, null, null);
  }

  function populateStatDialogSelects(selectedType, selectedDev) {
    const typeSel = document.getElementById('fs-dev-type');
    const devSel = document.getElementById('fs-dev-name');
    const statMap = state.catalog.stat_types || {};
    const devicesMap = state.catalog.devices || {};
    const types = Object.keys(statMap).filter((k) => (devicesMap[k] || []).length > 0);
    const listTypes = types.length ? types : Object.keys(statMap);

    typeSel.innerHTML = listTypes.map((dt) => `<option value="${esc(dt)}">${esc(devTypeLabel(dt))} (${esc(dt)})</option>`).join('');
    typeSel.value = listTypes.includes(selectedType) ? selectedType : listTypes[0];

    const refreshDev = (dt, keepDev) => {
      const devs = devicesMap[dt] || [];
      devSel.innerHTML = devs.map((d) => `<option value="${esc(d.name)}" data-idx="${d.idx}">${esc(d.name)} (#${d.idx})</option>`).join('');
      if (keepDev && devs.some((d) => d.name === keepDev)) devSel.value = keepDev;
    };
    refreshDev(typeSel.value, selectedDev);
    typeSel.onchange = () => refreshDev(typeSel.value, null);
  }

  function openMeasDialog(row = null) {
    const dlg = document.getElementById('meas-dialog');
    const form = document.getElementById('meas-form');
    form.reset();
    form.elements.id.value = row ? row.id : '';
    populateMeasDialogSelects(row?.device_type, row?.dev_name, row?.metric);
    document.getElementById('fm-mode').value = row?.source_mode || 'manual';
    document.getElementById('fm-value').value = row ? row.meas_value : 0;
    document.getElementById('fm-useflag').value = row ? String(row.meas_useflag ?? 1) : '1';
    document.getElementById('fm-note').value = row?.note || '';

    const wPreset = document.getElementById('fm-weight-preset');
    const wWrap = document.getElementById('fm-weight-custom-wrap');
    const wInput = document.getElementById('fm-weight');
    const wVal = row?.meas_weight ?? 1e-4;
    const matchOpt = Array.from(wPreset.options).find((o) => o.value !== 'custom' && Math.abs(Number(o.value) - Number(wVal)) < 1e-12);
    if (matchOpt) {
      wPreset.value = matchOpt.value;
      wWrap.hidden = true;
      wInput.value = matchOpt.value;
    } else {
      wPreset.value = 'custom';
      wWrap.hidden = false;
      wInput.value = wVal;
    }
    dlg.showModal();
  }

  function openStatDialog(row = null) {
    const dlg = document.getElementById('stat-dialog');
    const form = document.getElementById('stat-form');
    form.reset();
    form.elements.id.value = row ? row.id : '';
    populateStatDialogSelects(row?.device_type, row?.dev_name);
    document.getElementById('fs-value').value = row ? String(Number(row.stat_value) ? 1 : 0) : '1';
    document.getElementById('fs-useflag').value = row ? String(row.stat_useflag ?? 1) : '1';
    document.getElementById('fs-note').value = row?.note || '';
    dlg.showModal();
  }

  function renderDefines() {
    const wrap = document.getElementById('def-table-wrap');
    if (!state.defines.length) {
      wrap.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
      return;
    }
    const modeMap = { manual: t('mode.manual'), zero_injection: t('mode.zero'), bad_replace: t('mode.bad_replace') };
    wrap.innerHTML = `
      <table class="se-table">
        <thead>
          <tr>
            <th>#</th>
            <th>${esc(t('col.device_type'))}</th>
            <th>${esc(t('col.device_name'))}</th>
            <th>${esc(t('col.metric'))}</th>
            <th>${esc(t('col.value'))}</th>
            <th>${esc(t('col.weight'))}</th>
            <th>${esc(t('col.source_mode'))}</th>
            <th>${esc(t('col.status'))}</th>
            <th>${esc(t('col.note'))}</th>
            <th>${esc(t('col.ops'))}</th>
          </tr>
        </thead>
        <tbody>
          ${state.defines.map((r) => `
            <tr>
              <td class="tabular">${r.id}</td>
              <td>${esc(devTypeLabel(r.device_type))}</td>
              <td><strong>${esc(r.dev_name)}</strong></td>
              <td class="tabular">${esc(r.metric)} <span class="se-muted">${esc(r.se_type || '')}</span></td>
              <td class="tabular">${fmtNum(r.meas_value, 3)} ${esc(r.unit || '')}</td>
              <td class="tabular">${Number(r.meas_weight || 0).toExponential(1)}</td>
              <td><span class="se-tag">${esc(modeMap[r.source_mode] || r.source_mode || '')}</span></td>
              <td><span class="se-pill ${r.meas_useflag ? 'ok' : 'neutral'}">${esc(r.meas_useflag ? t('common.enabled') : t('common.disabled'))}</span></td>
              <td>${esc(r.note || '--')}</td>
              <td>
                <div class="se-row-actions">
                  <button type="button" class="se-btn mini" data-act="toggle-meas" data-id="${r.id}">${esc(r.meas_useflag ? t('action.disable') : t('action.enable'))}</button>
                  <button type="button" class="se-btn mini" data-act="edit-meas" data-id="${r.id}">${esc(t('action.edit'))}</button>
                  <button type="button" class="se-btn mini danger-ghost" data-act="del-meas" data-id="${r.id}">${esc(t('action.delete'))}</button>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  }

  function renderResults() {
    const wrap = document.getElementById('res-table-wrap');
    const pager = document.getElementById('res-pager');
    const meta = document.getElementById('res-count-meta');
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
            <th>${esc(t('col.se_value'))}</th>
            <th>${esc(t('col.residual'))}</th>
            <th>${esc(t('col.weight'))}</th>
            <th>${esc(t('col.note'))}</th>
            <th>${esc(t('col.ops'))}</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((r, idx) => `
            <tr>
              <td class="tabular">${r.meas_id}</td>
              <td><span class="se-pill ${r.origin === 'user_defined' ? 'info' : 'neutral'}">${esc(r.origin === 'user_defined' ? t('origin.user') : t('origin.auto'))}</span></td>
              <td>${esc(devTypeLabel(r.device_type))}</td>
              <td><strong>${esc(r.device_name)}</strong></td>
              <td class="tabular">${esc(r.metric || r.meas_type)}</td>
              <td class="tabular">${fmtNum(r.pseudo_value, 3)} ${esc(r.unit || '')}</td>
              <td class="tabular">${fmtNum(r.se_value, 3)} ${esc(r.unit || '')}</td>
              <td class="tabular">${fmtNum(r.residual, 4)}</td>
              <td class="tabular">${r.weight != null ? Number(r.weight).toExponential(1) : '--'}</td>
              <td>${esc(r.reason || '--')}</td>
              <td>
                <div class="se-row-actions">
                  <a class="se-btn mini se-link-btn" href="/se-flow.html?device_type=${encodeURIComponent(r.device_type)}&device_name=${encodeURIComponent(r.device_name)}">${esc(t('act.locate'))}</a>
                  ${r.origin !== 'user_defined' && r.metric ? `<button type="button" class="se-btn mini" data-res-promote="${idx}">${esc(t('act.promote_manual'))}</button>` : ''}
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
    const pages = Math.max(1, Math.ceil(total / limit));
    const page = Math.floor(offset / limit) + 1;
    pager.innerHTML = `
      <button type="button" class="se-btn mini" id="res-prev" ${page <= 1 ? 'disabled' : ''}>${esc(t('common.prev'))}</button>
      <span class="tabular">${page} / ${pages}</span>
      <button type="button" class="se-btn mini" id="res-next" ${page >= pages ? 'disabled' : ''}>${esc(t('common.next'))}</button>`;
    const pPrev = document.getElementById('res-prev');
    const pNext = document.getElementById('res-next');
    if (pPrev) pPrev.onclick = () => { state.results.offset = Math.max(0, offset - limit); loadResults(); };
    if (pNext) pNext.onclick = () => { state.results.offset = offset + limit; loadResults(); };
  }

  function renderStats() {
    const wrap = document.getElementById('stat-table-wrap');
    if (!state.stats.length) {
      wrap.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
      return;
    }
    wrap.innerHTML = `
      <table class="se-table">
        <thead>
          <tr>
            <th>#</th>
            <th>${esc(t('col.device_type'))}</th>
            <th>${esc(t('col.device_name'))}</th>
            <th>${esc(t('col.metric'))}</th>
            <th>${esc(t('col.stat_val'))}</th>
            <th>${esc(t('col.status'))}</th>
            <th>${esc(t('col.note'))}</th>
            <th>${esc(t('col.updated'))}</th>
            <th>${esc(t('col.ops'))}</th>
          </tr>
        </thead>
        <tbody>
          ${state.stats.map((r) => `
            <tr>
              <td class="tabular">${r.id}</td>
              <td>${esc(devTypeLabel(r.device_type))}</td>
              <td><strong>${esc(r.dev_name)}</strong></td>
              <td class="tabular">${esc(r.metric || 'status')}</td>
              <td><span class="se-pill ${Number(r.stat_value) ? 'ok' : 'warn'}">${esc(Number(r.stat_value) ? t('stat.on') : t('stat.off'))}</span></td>
              <td><span class="se-pill ${r.stat_useflag ? 'ok' : 'neutral'}">${esc(r.stat_useflag ? t('common.enabled') : t('common.disabled'))}</span></td>
              <td>${esc(r.note || '--')}</td>
              <td class="tabular">${esc(fmtTime(r.updated_at))}</td>
              <td>
                <div class="se-row-actions">
                  <button type="button" class="se-btn mini" data-act="edit-stat" data-id="${r.id}">${esc(t('action.edit'))}</button>
                  <button type="button" class="se-btn mini danger-ghost" data-act="del-stat" data-id="${r.id}">${esc(t('action.delete'))}</button>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  }

  async function loadOverview() {
    const ov = await api('/api/se/pseudo/overview');
    document.getElementById('kpi-def-enabled').textContent = ov.defined_enabled;
    document.getElementById('kpi-def-total').textContent = `/ ${ov.defined_total}`;
    document.getElementById('kpi-stat-enabled').textContent = ov.stat_enabled;
    document.getElementById('kpi-stat-total').textContent = `/ ${ov.stat_total}`;
    document.getElementById('kpi-res-user').textContent = ov.result_user;
    document.getElementById('kpi-res-auto').textContent = ov.result_auto;
    const meta = document.getElementById('pseudo-run-meta');
    meta.textContent = ov.latest_run ? `Run #${ov.latest_run.run_id} · ${fmtTime(ov.latest_run.calc_time)}` : '--';
  }

  async function loadDefines() {
    const dt = document.getElementById('def-type-filter').value || '';
    const q = document.getElementById('def-search').value || '';
    const en = document.getElementById('def-enabled-only').checked ? '1' : '0';
    state.defines = await api(`/api/se/pseudo/meas?device_type=${encodeURIComponent(dt)}&enabled_only=${en}&q=${encodeURIComponent(q)}`);
    renderDefines();
  }

  async function loadResults() {
    const dt = document.getElementById('res-type-filter').value || '';
    const q = document.getElementById('res-search').value || '';
    state.results = await api(
      `/api/se/pseudo/results?origin=${encodeURIComponent(state.resOrigin)}&device_type=${encodeURIComponent(dt)}&q=${encodeURIComponent(q)}&limit=${state.results.limit}&offset=${state.results.offset}`,
    );
    renderResults();
  }

  async function loadStats() {
    const dt = document.getElementById('stat-type-filter').value || '';
    state.stats = await api(`/api/se/pseudo/stat?device_type=${encodeURIComponent(dt)}`);
    renderStats();
  }

  async function refreshAll() {
    try {
      if (!state.catalog) {
        state.catalog = await api('/api/se/model-catalog');
        populateFilterSelects();
      }
      await Promise.all([loadOverview(), loadDefines(), loadResults(), loadStats()]);
    } catch (err) {
      notify(err.message, true);
    }
  }

  function bindEvents() {
    document.querySelectorAll('#pseudo-tabs .se-tab').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#pseudo-tabs .se-tab').forEach((b) => b.classList.toggle('active', b === btn));
        document.querySelectorAll('.se-workspace .se-panel').forEach((p) => p.classList.toggle('active', p.dataset.panel === btn.dataset.view));
      });
    });

    document.getElementById('def-type-filter').addEventListener('change', loadDefines);
    document.getElementById('def-search').addEventListener('input', loadDefines);
    document.getElementById('def-enabled-only').addEventListener('change', loadDefines);
    document.getElementById('res-type-filter').addEventListener('change', () => { state.results.offset = 0; loadResults(); });
    document.getElementById('res-search').addEventListener('input', () => { state.results.offset = 0; loadResults(); });
    document.getElementById('stat-type-filter').addEventListener('change', loadStats);

    document.querySelectorAll('#res-origin-seg .seg').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#res-origin-seg .seg').forEach((b) => b.classList.toggle('active', b === btn));
        state.resOrigin = btn.dataset.origin;
        state.results.offset = 0;
        loadResults();
      });
    });

    document.getElementById('btn-add-meas').addEventListener('click', () => openMeasDialog(null));
    document.getElementById('btn-add-stat').addEventListener('click', () => openStatDialog(null));
    document.getElementById('btn-meas-cancel').addEventListener('click', () => document.getElementById('meas-dialog').close());
    document.getElementById('btn-stat-cancel').addEventListener('click', () => document.getElementById('stat-dialog').close());

    document.getElementById('fm-weight-preset').addEventListener('change', (e) => {
      const custom = e.target.value === 'custom';
      document.getElementById('fm-weight-custom-wrap').hidden = !custom;
      if (!custom) document.getElementById('fm-weight').value = e.target.value;
    });

    document.getElementById('meas-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const devSel = document.getElementById('fm-dev-name');
      const opt = devSel.selectedOptions[0];
      const presetVal = document.getElementById('fm-weight-preset').value;
      const weight = presetVal === 'custom' ? Number(document.getElementById('fm-weight').value) : Number(presetVal);
      const id = e.target.elements.id.value;
      const payload = {
        device_type: document.getElementById('fm-dev-type').value,
        device_idx: opt ? Number(opt.dataset.idx) : null,
        device_name: devSel.value,
        metric: document.getElementById('fm-metric').value,
        source_mode: document.getElementById('fm-mode').value,
        meas_value: Number(document.getElementById('fm-value').value),
        meas_weight: weight,
        meas_useflag: Number(document.getElementById('fm-useflag').value),
        note: document.getElementById('fm-note').value,
      };
      try {
        if (id) {
          await api(`/api/se/pseudo/meas/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
        } else {
          await api('/api/se/pseudo/meas', { method: 'POST', body: JSON.stringify(payload) });
        }
        document.getElementById('meas-dialog').close();
        notify(t('msg.saved'));
        await Promise.all([loadOverview(), loadDefines()]);
      } catch (err) {
        notify(err.message, true);
      }
    });

    document.getElementById('stat-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const devSel = document.getElementById('fs-dev-name');
      const opt = devSel.selectedOptions[0];
      const id = e.target.elements.id.value;
      const payload = {
        device_type: document.getElementById('fs-dev-type').value,
        device_idx: opt ? Number(opt.dataset.idx) : null,
        device_name: devSel.value,
        stat_value: Number(document.getElementById('fs-value').value),
        stat_useflag: Number(document.getElementById('fs-useflag').value),
        note: document.getElementById('fs-note').value,
      };
      try {
        if (id) {
          await api(`/api/se/pseudo/stat/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
        } else {
          await api('/api/se/pseudo/stat', { method: 'POST', body: JSON.stringify(payload) });
        }
        document.getElementById('stat-dialog').close();
        notify(t('msg.saved'));
        await Promise.all([loadOverview(), loadStats()]);
      } catch (err) {
        notify(err.message, true);
      }
    });

    document.getElementById('def-table-wrap').addEventListener('click', async (e) => {
      const btn = e.target.closest('button[data-act]');
      if (!btn) return;
      const id = Number(btn.dataset.id);
      const row = state.defines.find((r) => r.id === id);
      if (!row) return;
      if (btn.dataset.act === 'edit-meas') {
        openMeasDialog(row);
      } else if (btn.dataset.act === 'toggle-meas') {
        try {
          await api(`/api/se/pseudo/meas/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
              device_type: row.device_type,
              device_idx: row.device_idx,
              device_name: row.dev_name,
              metric: row.metric,
              source_mode: row.source_mode || 'manual',
              meas_value: row.meas_value,
              meas_weight: row.meas_weight,
              meas_useflag: row.meas_useflag ? 0 : 1,
              note: row.note || '',
            }),
          });
          notify(t('msg.saved'));
          await Promise.all([loadOverview(), loadDefines()]);
        } catch (err) {
          notify(err.message, true);
        }
      } else if (btn.dataset.act === 'del-meas') {
        openConfirm({
          title: t('confirm.del_meas_title'),
          desc: `${row.dev_name}.${row.metric} — ${t('confirm.del_meas_desc')}`,
          okText: t('action.delete'),
          onConfirm: async () => {
            try {
              await api(`/api/se/pseudo/meas/${id}`, { method: 'DELETE' });
              notify(t('msg.deleted'));
              await Promise.all([loadOverview(), loadDefines()]);
            } catch (err) {
              notify(err.message, true);
            }
          },
        });
      }
    });

    // 本次伪量测结果：内核补充点一键固化为人工伪量测
    document.getElementById('res-table-wrap').addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-res-promote]');
      if (!btn) return;
      const row = (state.results.rows || [])[Number(btn.dataset.resPromote)];
      if (!row) return;
      const val = row.se_value != null ? Number(row.se_value) : (row.pseudo_value != null ? Number(row.pseudo_value) : 0);
      openMeasDialog({
        id: '',
        device_type: row.device_type,
        dev_name: row.device_name,
        metric: row.metric,
        source_mode: 'manual',
        meas_value: Number.isFinite(val) ? Number(val.toFixed(4)) : 0,
        meas_weight: row.weight || 1e-4,
        meas_useflag: 1,
        note: 'pinned from kernel_auto',
      });
    });

    document.getElementById('stat-table-wrap').addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-act]');
      if (!btn) return;
      const id = Number(btn.dataset.id);
      const row = state.stats.find((r) => r.id === id);
      if (!row) return;
      if (btn.dataset.act === 'edit-stat') {
        openStatDialog(row);
      } else if (btn.dataset.act === 'del-stat') {
        openConfirm({
          title: t('confirm.del_stat_title'),
          desc: `${row.dev_name}.${row.metric} — ${t('confirm.del_stat_desc')}`,
          okText: t('action.delete'),
          onConfirm: async () => {
            try {
              await api(`/api/se/pseudo/stat/${id}`, { method: 'DELETE' });
              notify(t('msg.deleted'));
              await Promise.all([loadOverview(), loadStats()]);
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
  refreshAll().then(() => {
    const qp = new URLSearchParams(window.location.search);
    const pType = qp.get('prefill_type');
    const pName = qp.get('prefill_name');
    const pMetric = qp.get('prefill_metric');
    if (pType && pName && pMetric) {
      openMeasDialog({
        id: '',
        device_type: pType,
        dev_name: pName,
        metric: pMetric,
        source_mode: 'manual',
        meas_value: 0,
        meas_weight: 1e-4,
        meas_useflag: 1,
        note: '',
      });
    }
  });
})();
