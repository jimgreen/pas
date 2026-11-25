/* 状态估计坏量测管理、屏蔽策略、可疑遥信与历史热点独立页 */
(() => {
  'use strict';

  const I18N = {
    'zh-CN': {
      'title.bad': '坏量测管理',
      'kpi.bad_cur': '当前坏量测',
      'kpi.policies': '屏蔽与替代策略',
      'kpi.policies_sub': '已生效 / 总策略',
      'kpi.suspect': '可疑遥信',
      'kpi.suspect_sub': '拓扑与潮流矛盾点',
      'kpi.abnormal': '未参与 / 缺测',
      'link.prefilter': '预过滤管理 →',
      'kpi.abnormal_sub': '预过滤 / 缺测与坏质量',
      'tab.current': '当前坏量测与处置',
      'tab.policies': '屏蔽与替代策略',
      'tab.abnormal': '异常量测与可疑遥信',
      'tab.history': '坏量测历史与热点',
      'ack.unacked': '未确认',
      'ack.acked': '已确认',
      'ack.suppressed': '已屏蔽',
      'ack.replaced': '已转伪量测',
      'pol.suppress': '屏蔽不参与',
      'pol.replace': '转伪量测替代',
      'btn.add_policy': '+ 新增屏蔽策略',
      'cat.susstat': '可疑遥信',
      'cat.filter': '预过滤',
      'cat.notuse': '未参与',
      'cat.nomeas': '缺测 / 坏质量',
      'hist.trend_title': '坏量测数量历史趋势',
      'hist.hotspot_title': '高频坏量测排行',
      'dlg.policy_title': '坏量测屏蔽/替代策略',
      'ph.search': '筛选设备/量测',
      'col.device_type': '设备类型',
      'col.device_name': '设备名称',
      'col.metric': '指标',
      'col.meas': '实测 Meas',
      'col.se': '估计 SE',
      'col.residual': '残差 Δ',
      'col.norm': '标准化残差',
      'col.ack_status': '处置状态',
      'col.action': '策略方式',
      'col.status': '启用状态',
      'col.reason': '原因',
      'col.ops': '操作',
      'col.scada_stat': 'SCADA 遥信',
      'col.inferred_stat': 'SE 推断',
      'col.evidence': '矛盾证据',
      'col.hits': '累计检出次数',
      'col.max_norm': '最大标准化残差',
      'col.last_seen': '最近出现',
      'act.ack': '确认',
      'act.unack': '撤销确认',
      'act.suppress': '屏蔽',
      'act.to_pseudo': '转伪量测',
      'act.locate': '定位潮流图',
      'msg.saved': '操作成功',
      'msg.converted': '已屏蔽原坏量测并生成伪量测定义',
      'msg.deleted': '策略已删除',
      'unacked_tpl': '未确认告警: ',
      'confirm.del_title': '删除策略',
      'confirm.del_desc': '确认删除该屏蔽策略？',
    },
    'en-US': {
      'title.bad': 'Bad Data Management',
      'kpi.bad_cur': 'Current Bad Data',
      'kpi.policies': 'Policies',
      'kpi.policies_sub': 'Active / Total',
      'kpi.suspect': 'Suspect Status',
      'kpi.suspect_sub': 'Topology Conflicts',
      'kpi.abnormal': 'Excluded / Missing',
      'link.prefilter': 'Prefilter →',
      'kpi.abnormal_sub': 'Prefiltered / Missing',
      'tab.current': 'Current Bad Data',
      'tab.policies': 'Suppress Policies',
      'tab.abnormal': 'Abnormal & Suspect',
      'tab.history': 'History & Hotspots',
      'ack.unacked': 'Unacked',
      'ack.acked': 'Acked',
      'ack.suppressed': 'Suppressed',
      'ack.replaced': 'Replaced',
      'pol.suppress': 'Suppress',
      'pol.replace': 'Replace w/ Pseudo',
      'btn.add_policy': '+ Add Policy',
      'cat.susstat': 'Suspect Status',
      'cat.filter': 'Prefiltered',
      'cat.notuse': 'Excluded',
      'cat.nomeas': 'Missing / Bad Qual',
      'hist.trend_title': 'Bad Data Count Trend',
      'hist.hotspot_title': 'Top Bad Data Hotspots',
      'dlg.policy_title': 'Bad Measurement Policy',
      'ph.search': 'Filter device / metric',
      'col.device_type': 'Device Type',
      'col.device_name': 'Device',
      'col.metric': 'Metric',
      'col.meas': 'Meas',
      'col.se': 'SE',
      'col.residual': 'Residual Δ',
      'col.norm': 'Norm. Res',
      'col.ack_status': 'State',
      'col.action': 'Action',
      'col.status': 'Enabled',
      'col.reason': 'Reason',
      'col.ops': 'Actions',
      'col.scada_stat': 'SCADA Status',
      'col.inferred_stat': 'SE Inferred',
      'col.evidence': 'Evidence',
      'col.hits': 'Hits',
      'col.max_norm': 'Max Norm Res',
      'col.last_seen': 'Last Seen',
      'act.ack': 'Ack',
      'act.unack': 'Unack',
      'act.suppress': 'Suppress',
      'act.to_pseudo': 'To Pseudo',
      'act.locate': 'Locate SVG',
      'msg.saved': 'Saved',
      'msg.converted': 'Suppressed and converted to pseudo measurement',
      'msg.deleted': 'Policy deleted',
      'unacked_tpl': 'Unacked: ',
      'confirm.del_title': 'Delete Bad Data Policy',
      'confirm.del_desc': 'This measurement will re-enter SE solving on the next run.',
    },
    'ru-RU': {
      'title.bad': 'Плохие данные',
      'kpi.bad_cur': 'Текущие сбои',
      'kpi.policies': 'Политики',
      'kpi.policies_sub': 'Активно / Всего',
      'kpi.suspect': 'Подозр. ТС',
      'kpi.suspect_sub': 'Конфликты топологии',
      'kpi.abnormal': 'Не учт. / Пропуски',
      'link.prefilter': 'Предфильтр →',
      'kpi.abnormal_sub': 'Фильтр / Нет данных',
      'tab.current': 'Текущие сбои',
      'tab.policies': 'Блокировка',
      'tab.abnormal': 'Аномалии и ТС',
      'tab.history': 'История и очаги',
      'ack.unacked': 'Не подтв.',
      'ack.acked': 'Подтвержд.',
      'ack.suppressed': 'Заблокир.',
      'ack.replaced': 'Псевдоизм.',
      'pol.suppress': 'Исключить',
      'pol.replace': 'Заменить псевдо',
      'btn.add_policy': '+ Новая политика',
      'cat.susstat': 'Подозр. ТС',
      'cat.filter': 'Отфильтровано',
      'cat.notuse': 'Не участвуют',
      'cat.nomeas': 'Пропуск / Качество',
      'hist.trend_title': 'Тренд числа плохих данных',
      'hist.hotspot_title': 'Частые плохие точки',
      'dlg.policy_title': 'Политика блокировки',
      'ph.search': 'Поиск устройства',
      'col.device_type': 'Тип',
      'col.device_name': 'Устройство',
      'col.metric': 'Параметр',
      'col.meas': 'Изм.',
      'col.se': 'Оценка SE',
      'col.residual': 'Невязка Δ',
      'col.norm': 'Норм. нев.',
      'col.ack_status': 'Статус',
      'col.action': 'Действие',
      'col.status': 'Состояние',
      'col.reason': 'Причина',
      'col.ops': 'Операции',
      'col.scada_stat': 'ТС SCADA',
      'col.inferred_stat': 'Вывод SE',
      'col.evidence': 'Признак',
      'col.hits': 'Кол-во',
      'col.max_norm': 'Макс. нор. нев.',
      'col.last_seen': 'Последний раз',
      'act.ack': 'Квит.',
      'act.unack': 'Снять',
      'act.suppress': 'Блок.',
      'act.to_pseudo': 'В псевдо',
      'act.locate': 'На схему',
      'msg.saved': 'Выполнено',
      'msg.converted': 'Заблокировано и переведено в псевдоизмерение',
      'msg.deleted': 'Политика удалена',
      'unacked_tpl': 'Не квитир.: ',
      'confirm.del_title': 'Удалить политику',
      'confirm.del_desc': 'Измерение снова будет участвовать в следующем расчёте SE.',
    },
  };

  const state = {
    catalog: null,
    current: [],
    policies: [],
    abnormal: { category: 'susstat', rows: [], total: 0, limit: 50, offset: 0 },
    history: { history: { hotspots: [] }, trend: [] },
  };

  const common = window.createSECommon(I18N, () => {
    populateSelects();
    renderCurrent();
    renderPolicies();
    renderAbnormal();
    renderHistory();
  });
  const { t, esc, fmtNum, fmtTime, devTypeLabel, api, notify, openConfirm } = common;

  function populateSelects() {
    if (!state.catalog) return;
    const types = Object.keys(state.catalog.meas_metrics || {});
    ['cur-type-filter', 'pol-type-filter', 'abn-type-filter'].forEach((id) => {
      const sel = document.getElementById(id);
      if (!sel) return;
      const cur = sel.value || 'all';
      sel.innerHTML = `<option value="all">${esc(t('common.all'))}</option>`
        + types.map((dt) => `<option value="${esc(dt)}">${esc(devTypeLabel(dt))} (${esc(dt)})</option>`).join('');
      sel.value = types.includes(cur) ? cur : 'all';
    });
  }

  function populatePolicyDialog(row = null) {
    const typeSel = document.getElementById('fp-dev-type');
    const devSel = document.getElementById('fp-dev-name');
    const metSel = document.getElementById('fp-metric');
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

  function openPolicyDialog(row = null) {
    const dlg = document.getElementById('policy-dialog');
    const form = document.getElementById('policy-form');
    form.reset();
    form.elements.id.value = row ? row.id : '';
    populatePolicyDialog(row);
    document.getElementById('fp-action').value = row?.action || 'suppress';
    document.getElementById('fp-enabled').value = row ? String(row.enabled ?? 1) : '1';
    document.getElementById('fp-reason').value = row?.reason || '';
    dlg.showModal();
  }

  function ackBadge(status) {
    const map = {
      unacked: ['bad', t('ack.unacked')],
      acked: ['ok', t('ack.acked')],
      suppressed: ['warn', t('ack.suppressed')],
      replaced_pseudo: ['info', t('ack.replaced')],
    };
    const [cls, label] = map[status] || ['neutral', status || '--'];
    return `<span class="se-pill ${cls}">${esc(label)}</span>`;
  }

  function renderCurrent() {
    const wrap = document.getElementById('cur-table-wrap');
    if (!state.current.length) {
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
            <th>${esc(t('col.meas'))}</th>
            <th>${esc(t('col.se'))}</th>
            <th>${esc(t('col.residual'))}</th>
            <th>${esc(t('col.norm'))}</th>
            <th>${esc(t('col.ack_status'))}</th>
            <th>${esc(t('col.ops'))}</th>
          </tr>
        </thead>
        <tbody>
          ${state.current.map((r) => `
            <tr>
              <td class="tabular">${r.id}</td>
              <td>${esc(devTypeLabel(r.device_type))}</td>
              <td><strong>${esc(r.device_name)}</strong></td>
              <td class="tabular">${esc(r.metric || r.meas_type)}</td>
              <td class="tabular">${fmtNum(r.meas_value, 3)} ${esc(r.unit || '')}</td>
              <td class="tabular">${fmtNum(r.se_value, 3)} ${esc(r.unit || '')}</td>
              <td class="tabular">${fmtNum(r.residual, 3)}</td>
              <td class="tabular">${fmtNum(r.normalized_residual, 2)}</td>
              <td>${ackBadge(r.ack_status || 'unacked')}</td>
              <td>
                <div class="se-row-actions">
                  <button type="button" class="se-btn mini" data-act="${r.ack_status === 'acked' ? 'unack' : 'ack'}" data-id="${r.id}">${esc(r.ack_status === 'acked' ? t('act.unack') : t('act.ack'))}</button>
                  <button type="button" class="se-btn mini" data-act="suppress" data-id="${r.id}">${esc(t('act.suppress'))}</button>
                  <button type="button" class="se-btn mini" data-act="to-pseudo" data-id="${r.id}">${esc(t('act.to_pseudo'))}</button>
                  <a class="se-btn mini se-link-btn" href="/se-flow.html?device_type=${encodeURIComponent(r.device_type)}&device_name=${encodeURIComponent(r.device_name)}">${esc(t('act.locate'))}</a>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  }

  function renderPolicies() {
    const wrap = document.getElementById('pol-table-wrap');
    if (!state.policies.length) {
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
            <th>${esc(t('col.action'))}</th>
            <th>${esc(t('col.status'))}</th>
            <th>${esc(t('col.reason'))}</th>
            <th>${esc(t('col.ops'))}</th>
          </tr>
        </thead>
        <tbody>
          ${state.policies.map((r) => `
            <tr>
              <td class="tabular">${r.id}</td>
              <td>${esc(devTypeLabel(r.device_type))}</td>
              <td><strong>${esc(r.device_name)}</strong></td>
              <td class="tabular">${esc(r.metric)}</td>
              <td><span class="se-pill ${r.action === 'replace_pseudo' ? 'info' : 'warn'}">${esc(r.action === 'replace_pseudo' ? t('pol.replace') : t('pol.suppress'))}</span></td>
              <td><span class="se-pill ${r.enabled ? 'ok' : 'neutral'}">${esc(r.enabled ? t('common.enabled') : t('common.disabled'))}</span></td>
              <td>${esc(r.reason || '--')}</td>
              <td>
                <div class="se-row-actions">
                  <button type="button" class="se-btn mini" data-act="edit-pol" data-id="${r.id}">${esc(t('action.edit'))}</button>
                  <button type="button" class="se-btn mini danger-ghost" data-act="del-pol" data-id="${r.id}">${esc(t('action.delete'))}</button>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  }

  function renderAbnormal() {
    const wrap = document.getElementById('abn-table-wrap');
    const pager = document.getElementById('abn-pager');
    const meta = document.getElementById('abn-count-meta');
    const { category, rows, total, limit, offset } = state.abnormal;
    meta.textContent = `${rows.length} / ${total}`;
    if (!rows.length) {
      wrap.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
      pager.innerHTML = '';
      return;
    }
    if (category === 'susstat') {
      wrap.innerHTML = `
        <table class="se-table">
          <thead>
            <tr>
              <th>#</th>
              <th>${esc(t('col.device_type'))}</th>
              <th>${esc(t('col.device_name'))}</th>
              <th>${esc(t('col.metric'))}</th>
              <th>${esc(t('col.scada_stat'))}</th>
              <th>${esc(t('col.inferred_stat'))}</th>
              <th>${esc(t('col.evidence'))}</th>
              <th>${esc(t('col.reason'))}</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map((r) => `
              <tr>
                <td class="tabular">${r.id}</td>
                <td>${esc(devTypeLabel(r.device_type))}</td>
                <td><strong>${esc(r.device_name)}</strong></td>
                <td class="tabular">${esc(r.metric)}</td>
                <td class="tabular">${r.scada_status ?? '--'}</td>
                <td class="tabular">${r.se_inferred_status ?? '--'}</td>
                <td class="tabular">${esc(r.evidence || '--')}</td>
                <td>${esc(r.reason || '--')}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>`;
    } else if (category === 'nomeas') {
      wrap.innerHTML = `
        <table class="se-table">
          <thead>
            <tr>
              <th>#</th>
              <th>${esc(t('col.device_name'))}</th>
              <th>${esc(t('col.metric'))}</th>
              <th>${esc(t('col.meas'))}</th>
              <th>${esc(t('col.reason'))}</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map((r) => `
              <tr>
                <td class="tabular">${r.id}</td>
                <td><strong>${esc(r.dev_name)}</strong></td>
                <td class="tabular">${esc(r.meas_name)}</td>
                <td class="tabular">${fmtNum(r.meas_value, 3)}</td>
                <td>${esc(r.filter_reason || '--')}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>`;
    } else {
      wrap.innerHTML = `
        <table class="se-table">
          <thead>
            <tr>
              <th>#</th>
              <th>${esc(t('col.device_type'))}</th>
              <th>${esc(t('col.device_name'))}</th>
              <th>${esc(t('col.metric'))}</th>
              <th>${esc(t('col.meas'))}</th>
              <th>${esc(t('col.se'))}</th>
              <th>${esc(t('col.reason'))}</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map((r) => `
              <tr>
                <td class="tabular">${r.meas_id}</td>
                <td>${esc(devTypeLabel(r.device_type))}</td>
                <td><strong>${esc(r.device_name)}</strong></td>
                <td class="tabular">${esc(r.metric || r.meas_type)}</td>
                <td class="tabular">${fmtNum(r.meas_value, 3)} ${esc(r.unit || '')}</td>
                <td class="tabular">${fmtNum(r.se_value, 3)} ${esc(r.unit || '')}</td>
                <td>${esc(r.reason || r.source || '--')}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>`;
    }
    const pages = Math.max(1, Math.ceil(total / limit));
    const page = Math.floor(offset / limit) + 1;
    pager.innerHTML = `
      <button type="button" class="se-btn mini" id="abn-prev" ${page <= 1 ? 'disabled' : ''}>${esc(t('common.prev'))}</button>
      <span class="tabular">${page} / ${pages}</span>
      <button type="button" class="se-btn mini" id="abn-next" ${page >= pages ? 'disabled' : ''}>${esc(t('common.next'))}</button>`;
    const pPrev = document.getElementById('abn-prev');
    const pNext = document.getElementById('abn-next');
    if (pPrev) pPrev.onclick = () => { state.abnormal.offset = Math.max(0, offset - limit); loadAbnormal(); };
    if (pNext) pNext.onclick = () => { state.abnormal.offset = offset + limit; loadAbnormal(); };
  }

  function renderHistory() {
    const chartHost = document.getElementById('bad-trend-chart');
    const trend = state.history.trend || [];
    if (!trend.length) {
      chartHost.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
    } else {
      const w = Math.max(360, chartHost.clientWidth || 560);
      const h = Math.max(200, chartHost.clientHeight || 220);
      const pad = { top: 18, right: 32, bottom: 28, left: 42 };
      const plotW = w - pad.left - pad.right;
      const plotH = h - pad.top - pad.bottom;
      const vals = trend.map((d) => Number(d.bad_data_count || 0));
      const maxY = Math.max(1, ...vals);
      const pts = trend.map((d, idx) => {
        const x = pad.left + (trend.length === 1 ? plotW / 2 : (idx / (trend.length - 1)) * plotW);
        const y = pad.top + plotH - (Number(d.bad_data_count || 0) / maxY) * plotH;
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
          <polyline fill="none" stroke="var(--danger)" stroke-width="2" points="${poly}"/>
          ${pts.map((p) => `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="3" fill="var(--danger)"><title>#${p.d.run_id} · ${fmtTime(p.d.calc_time)} · ${p.d.bad_data_count}</title></circle>`).join('')}
          <text x="${pad.left}" y="${h - 6}" text-anchor="start" fill="var(--text-secondary)" font-size="11">${esc(fmtTime(trend[0].calc_time).slice(5, 16))}</text>
          <text x="${w - pad.right}" y="${h - 6}" text-anchor="end" fill="var(--text-secondary)" font-size="11">${esc(fmtTime(trend[trend.length - 1].calc_time).slice(5, 16))}</text>
        </svg>`;
    }

    const hsWrap = document.getElementById('bad-hotspot-wrap');
    const hotspots = (state.history.history && state.history.history.hotspots) || [];
    if (!hotspots.length) {
      hsWrap.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
      return;
    }
    hsWrap.innerHTML = `
      <table class="se-table">
        <thead>
          <tr>
            <th>${esc(t('col.device_type'))}</th>
            <th>${esc(t('col.device_name'))}</th>
            <th>${esc(t('col.metric'))}</th>
            <th>${esc(t('col.hits'))}</th>
            <th>${esc(t('col.max_norm'))}</th>
            <th>${esc(t('col.last_seen'))}</th>
          </tr>
        </thead>
        <tbody>
          ${hotspots.map((h) => `
            <tr>
              <td>${esc(devTypeLabel(h.device_type))}</td>
              <td><strong>${esc(h.device_name)}</strong></td>
              <td class="tabular">${esc(h.meas_type || h.measurement_type || h.metric || '—')}</td>
              <td class="tabular"><strong>${h.bad_hits ?? h.bad_count ?? h.count ?? 0}</strong></td>
              <td class="tabular">${fmtNum(h.max_norm_residual, 2)}</td>
              <td class="tabular">${esc(fmtTime(h.last_seen_at || h.last_seen || h.last_calc_time))}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  }

  async function loadOverview() {
    const ov = await api('/api/se/bad/overview');
    document.getElementById('kpi-bad-total').textContent = ov.bad_total;
    document.getElementById('kpi-bad-unacked').textContent = `${t('unacked_tpl')}${ov.unacked_count}`;
    document.getElementById('kpi-card-cur').classList.toggle('alarm', ov.unacked_count > 0);
    document.getElementById('kpi-pol-enabled').textContent = ov.policy_enabled;
    document.getElementById('kpi-pol-total').textContent = `/ ${ov.policy_total}`;
    document.getElementById('kpi-suspect').textContent = ov.suspect_count;
    document.getElementById('kpi-notuse').textContent = ov.notuse_count;
    document.getElementById('kpi-nomeas').textContent = `/ ${ov.nomeas_count}`;
    const meta = document.getElementById('bad-run-meta');
    meta.textContent = ov.latest_run ? `Run #${ov.latest_run.run_id} · ${fmtTime(ov.latest_run.calc_time)}` : '--';
  }

  async function loadCurrent() {
    const dt = document.getElementById('cur-type-filter').value || '';
    const ack = document.getElementById('cur-ack-filter').value || 'all';
    const q = document.getElementById('cur-search').value || '';
    state.current = await api(`/api/se/bad/current?device_type=${encodeURIComponent(dt)}&ack_status=${encodeURIComponent(ack)}&q=${encodeURIComponent(q)}`);
    renderCurrent();
  }

  async function loadPolicies() {
    const dt = document.getElementById('pol-type-filter').value || '';
    const act = document.getElementById('pol-action-filter').value || '';
    const q = document.getElementById('pol-search').value || '';
    state.policies = await api(`/api/se/bad/policies?device_type=${encodeURIComponent(dt)}&action=${encodeURIComponent(act)}&q=${encodeURIComponent(q)}`);
    renderPolicies();
  }

  async function loadAbnormal() {
    const dt = document.getElementById('abn-type-filter').value || '';
    const q = document.getElementById('abn-search').value || '';
    state.abnormal = await api(
      `/api/se/bad/abnormal?category=${encodeURIComponent(state.abnormal.category)}&device_type=${encodeURIComponent(dt)}&q=${encodeURIComponent(q)}&limit=${state.abnormal.limit}&offset=${state.abnormal.offset}`,
    );
    renderAbnormal();
  }

  async function loadHistory() {
    const lim = document.getElementById('hist-limit').value || '60';
    state.history = await api(`/api/se/bad/history?limit=${lim}`);
    renderHistory();
  }

  async function refreshAll() {
    try {
      if (!state.catalog) {
        state.catalog = await api('/api/se/model-catalog');
        populateSelects();
      }
      await Promise.all([loadOverview(), loadCurrent(), loadPolicies(), loadAbnormal(), loadHistory()]);
    } catch (err) {
      notify(err.message, true);
    }
  }

  function bindEvents() {
    document.querySelectorAll('#bad-tabs .se-tab').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#bad-tabs .se-tab').forEach((b) => b.classList.toggle('active', b === btn));
        document.querySelectorAll('.se-workspace .se-panel').forEach((p) => p.classList.toggle('active', p.dataset.panel === btn.dataset.view));
        if (btn.dataset.view === 'history') renderHistory();
      });
    });

    document.getElementById('cur-type-filter').addEventListener('change', loadCurrent);
    document.getElementById('cur-ack-filter').addEventListener('change', loadCurrent);
    document.getElementById('cur-search').addEventListener('input', common.debounce(loadCurrent, 200));
    document.getElementById('pol-type-filter').addEventListener('change', loadPolicies);
    document.getElementById('pol-action-filter').addEventListener('change', loadPolicies);
    document.getElementById('pol-search').addEventListener('input', common.debounce(loadPolicies, 200));
    document.getElementById('abn-type-filter').addEventListener('change', () => { state.abnormal.offset = 0; loadAbnormal(); });
    document.getElementById('abn-search').addEventListener('input', common.debounce(() => { state.abnormal.offset = 0; loadAbnormal(); }, 200));
    document.getElementById('hist-limit').addEventListener('change', loadHistory);

    document.querySelectorAll('#abn-cat-seg .seg').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#abn-cat-seg .seg').forEach((b) => b.classList.toggle('active', b === btn));
        state.abnormal.category = btn.dataset.cat;
        state.abnormal.offset = 0;
        loadAbnormal();
      });
    });

    document.getElementById('btn-add-policy').addEventListener('click', () => openPolicyDialog(null));
    document.getElementById('btn-pol-cancel').addEventListener('click', () => document.getElementById('policy-dialog').close());

    document.getElementById('policy-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const devSel = document.getElementById('fp-dev-name');
      const opt = devSel.selectedOptions[0];
      const id = e.target.elements.id.value;
      const payload = {
        device_type: document.getElementById('fp-dev-type').value,
        device_idx: opt ? Number(opt.dataset.idx) : null,
        device_name: devSel.value,
        metric: document.getElementById('fp-metric').value,
        action: document.getElementById('fp-action').value,
        enabled: Number(document.getElementById('fp-enabled').value),
        reason: document.getElementById('fp-reason').value,
      };
      try {
        if (id) {
          await api(`/api/se/bad/policies/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
        } else {
          await api('/api/se/bad/policies', { method: 'POST', body: JSON.stringify(payload) });
        }
        document.getElementById('policy-dialog').close();
        notify(t('msg.saved'));
        await Promise.all([loadOverview(), loadCurrent(), loadPolicies()]);
      } catch (err) {
        notify(err.message, true);
      }
    });

    document.getElementById('cur-table-wrap').addEventListener('click', async (e) => {
      const btn = e.target.closest('button[data-act]');
      if (!btn) return;
      const id = Number(btn.dataset.id);
      const row = state.current.find((r) => r.id === id);
      if (!row) return;
      try {
        if (btn.dataset.act === 'ack' || btn.dataset.act === 'unack') {
          await api('/api/se/bad/ack', {
            method: 'POST',
            body: JSON.stringify({ id, ack_status: btn.dataset.act === 'ack' ? 'acked' : 'unacked' }),
          });
          notify(t('msg.saved'));
        } else if (btn.dataset.act === 'suppress') {
          await api('/api/se/bad/policies', {
            method: 'POST',
            body: JSON.stringify({
              device_type: row.device_type,
              device_idx: row.device_idx,
              device_name: row.device_name,
              metric: row.metric,
              action: 'suppress',
              enabled: 1,
              reason: `bad_data_run_${row.run_id}`,
            }),
          });
          notify(t('msg.saved'));
        } else if (btn.dataset.act === 'to-pseudo') {
          await api('/api/se/bad/convert-pseudo', {
            method: 'POST',
            body: JSON.stringify({ bad_id: id }),
          });
          notify(t('msg.converted'));
        }
        await Promise.all([loadOverview(), loadCurrent(), loadPolicies()]);
      } catch (err) {
        notify(err.message, true);
      }
    });

    document.getElementById('pol-table-wrap').addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-act]');
      if (!btn) return;
      const id = Number(btn.dataset.id);
      const row = state.policies.find((r) => r.id === id);
      if (!row) return;
      if (btn.dataset.act === 'edit-pol') {
        openPolicyDialog(row);
      } else if (btn.dataset.act === 'del-pol') {
        openConfirm({
          title: t('confirm.del_title'),
          desc: `${row.device_name}.${row.metric} — ${t('confirm.del_desc')}`,
          okText: t('action.delete'),
          onConfirm: async () => {
            try {
              await api(`/api/se/bad/policies/${id}`, { method: 'DELETE' });
              notify(t('msg.deleted'));
              await Promise.all([loadOverview(), loadCurrent(), loadPolicies()]);
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
      document.querySelector('#bad-tabs .se-tab[data-view="policies"]')?.click();
      openPolicyDialog({ device_type: pType, device_name: pName, metric: pMetric, action: 'suppress', enabled: 1, reason: '' });
    }
  });
})();
