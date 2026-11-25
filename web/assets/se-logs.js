/* 状态估计运行日志查询、导出与定期自动删除策略独立页 */
(() => {
  'use strict';

  const I18N = {
    'zh-CN': {
      'title.logs': '状态估计运行日志',
      'kpi.total': '日志总条数',
      'kpi.err24': '24h 错误 / 告警',
      'kpi.err24_sub': 'ERROR / WARN',
      'kpi.retention': '保留与自动清理',
      'kpi.cleanup': '上次清理结果',
      'unit.days': '天',
      'unit.rows': '条',
      'tab.stream': '日志明细与检索',
      'tab.runs': '运行与调度',
      'tab.policy': '定期删除与存储策略',
      'runs.title': 'SE 运行记录',
      'runs.open_detail': '明细与 dbdef →',
      'runs.view_log': '看日志',
      'col.pass_rate': '合格率',
      'col.bad_count': '坏数据',
      'col.status': '状态',
      'col.elapsed_s': '用时 (s)',
      'sched.title': 'SE 周期调度',
      'sched.period': '周期 (s)',
      'sched.enabled': '启用周期自动执行',
      'sched.save': '保存调度',
      'sched.daemon_start': '启动周期',
      'sched.daemon_stop': '停止周期',
      'sched.saved': '调度已保存',
      'sched.started': '周期已启动',
      'sched.stopped': '周期已停止',
      'filter.level_all': '全部级别',
      'filter.stage_all': '全部阶段',
      'filter.source_all': '全部来源',
      'win.all': '全部时间',
      'win.1h': '近 1 小时',
      'win.24h': '近 24 小时',
      'win.7d': '近 7 天',
      'win.30d': '近 30 天',
      'ph.run_id': 'Run ID',
      'ph.search': '搜索日志内容',
      'col.time': '时间',
      'col.run_id': 'Run',
      'col.level': '级别',
      'col.stage': '阶段',
      'col.source': '来源',
      'col.elapsed': '耗时 (ms)',
      'col.message': '日志摘要',
      'pol.title': '定期删除与存储策略 (se_log_policy)',
      'pol.enabled': '自动定期清理',
      'pol.min_level': '最低入库级别',
      'pol.retention': '常规日志保留天数',
      'pol.keep_err': 'ERROR 日志保留天数',
      'pol.max_rows': '最大保留条数',
      'pol.interval': '清理执行周期',
      'pol.save': '保存策略',
      'pol.preview': '预估待清理',
      'pol.purge_now': '立即按策略清理',
      'dist.title': '阶段分布统计',
      'msg.pol_saved': '日志策略已保存',
      'msg.purged': '日志清理完成，共删除 ',
      'msg.preview_tpl': '预计清理: ',
      'confirm.purge_title': '清理历史日志',
      'confirm.purge_desc': '确认清理到期/超限日志？',
      'confirm.purge_ok': '确认清理',
      'recent24_tpl': '近 24h 新增: ',
      'maxrows_tpl': '上限 ',
    },
    'en-US': {
      'title.logs': 'SE Run Logs',
      'kpi.total': 'Total Logs',
      'kpi.err24': '24h Error / Warn',
      'kpi.err24_sub': 'ERROR / WARN',
      'kpi.retention': 'Retention Policy',
      'kpi.cleanup': 'Last Cleanup',
      'unit.days': 'd',
      'unit.rows': 'rows',
      'tab.stream': 'Log Stream',
      'tab.runs': 'Runs & Schedule',
      'tab.policy': 'Retention & Auto-Purge',
      'runs.title': 'SE Run History',
      'runs.open_detail': 'Details & dbdef →',
      'runs.view_log': 'Logs',
      'col.pass_rate': 'Pass Rate',
      'col.bad_count': 'Bad',
      'col.status': 'Status',
      'col.elapsed_s': 'Elapsed (s)',
      'sched.title': 'SE Schedule',
      'sched.period': 'Period (s)',
      'sched.enabled': 'Enable periodic run',
      'sched.save': 'Save',
      'sched.daemon_start': 'Start',
      'sched.daemon_stop': 'Stop',
      'sched.saved': 'Schedule saved',
      'sched.started': 'Daemon started',
      'sched.stopped': 'Daemon stopped',
      'filter.level_all': 'All Levels',
      'filter.stage_all': 'All Stages',
      'filter.source_all': 'All Sources',
      'win.all': 'All Time',
      'win.1h': 'Last 1h',
      'win.24h': 'Last 24h',
      'win.7d': 'Last 7d',
      'win.30d': 'Last 30d',
      'ph.run_id': 'Run ID',
      'ph.search': 'Search messages',
      'col.time': 'Time',
      'col.run_id': 'Run',
      'col.level': 'Level',
      'col.stage': 'Stage',
      'col.source': 'Source',
      'col.elapsed': 'Elapsed (ms)',
      'col.message': 'Message',
      'pol.title': 'Retention & Auto-Purge Policy',
      'pol.enabled': 'Auto Cleanup',
      'pol.min_level': 'Min Level',
      'pol.retention': 'Retention Days',
      'pol.keep_err': 'Error Retention Days',
      'pol.max_rows': 'Max Rows',
      'pol.interval': 'Cleanup Interval',
      'pol.save': 'Save Policy',
      'pol.preview': 'Preview Purge',
      'pol.purge_now': 'Purge Now',
      'dist.title': 'Stage Distribution',
      'msg.pol_saved': 'Log policy saved',
      'msg.purged': 'Cleanup complete, deleted ',
      'msg.preview_tpl': 'Pending purge: ',
      'confirm.purge_title': 'Confirm Log Cleanup',
      'confirm.purge_desc': 'Expired or overflow SE run logs will be permanently deleted.',
      'confirm.purge_ok': 'Purge Now',
      'recent24_tpl': 'Last 24h: ',
      'maxrows_tpl': 'Max ',
    },
    'ru-RU': {
      'title.logs': 'Журнал работы SE',
      'kpi.total': 'Всего записей',
      'kpi.err24': '24ч Ошибки / Пред.',
      'kpi.err24_sub': 'ERROR / WARN',
      'kpi.retention': 'Хранение',
      'kpi.cleanup': 'Посл. очистка',
      'unit.days': 'дн',
      'unit.rows': 'зап.',
      'tab.stream': 'Лента журнала',
      'tab.runs': 'Запуски и цикл',
      'tab.policy': 'Автоочистка',
      'runs.title': 'Запуски SE',
      'runs.open_detail': 'Детали и dbdef →',
      'runs.view_log': 'Лог',
      'col.pass_rate': 'Годные',
      'col.bad_count': 'Плохие',
      'col.status': 'Статус',
      'col.elapsed_s': 'Время (с)',
      'sched.title': 'Расписание SE',
      'sched.period': 'Период (с)',
      'sched.enabled': 'Автозапуск',
      'sched.save': 'Сохранить',
      'sched.daemon_start': 'Старт',
      'sched.daemon_stop': 'Стоп',
      'sched.saved': 'Сохранено',
      'sched.started': 'Запущено',
      'sched.stopped': 'Остановлено',
      'filter.level_all': 'Все уровни',
      'filter.stage_all': 'Все этапы',
      'filter.source_all': 'Все источники',
      'win.all': 'Всё время',
      'win.1h': '1 час',
      'win.24h': '24 часа',
      'win.7d': '7 дней',
      'win.30d': '30 дней',
      'ph.run_id': 'Run ID',
      'ph.search': 'Поиск по журналу',
      'col.time': 'Время',
      'col.run_id': 'Run',
      'col.level': 'Уровень',
      'col.stage': 'Этап',
      'col.source': 'Источник',
      'col.elapsed': 'Время (мс)',
      'col.message': 'Сообщение',
      'pol.title': 'Политика хранения и очистки',
      'pol.enabled': 'Автоочистка',
      'pol.min_level': 'Мин. уровень',
      'pol.retention': 'Срок хранения (дн)',
      'pol.keep_err': 'Хранение ERROR (дн)',
      'pol.max_rows': 'Макс. записей',
      'pol.interval': 'Интервал очистки',
      'pol.save': 'Сохранить',
      'pol.preview': 'Оценить',
      'pol.purge_now': 'Очистить сейчас',
      'dist.title': 'Распределение по этапам',
      'msg.pol_saved': 'Политика сохранена',
      'msg.purged': 'Очистка завершена, удалено: ',
      'msg.preview_tpl': 'К удалению: ',
      'confirm.purge_title': 'Подтвердить очистку',
      'confirm.purge_desc': 'Устаревшие записи журнала SE будут безвозвратно удалены.',
      'confirm.purge_ok': 'Очистить',
      'recent24_tpl': 'За 24ч: ',
      'maxrows_tpl': 'Лимит ',
    },
  };

  const state = {
    logs: { rows: [], total: 0, limit: 50, offset: 0 },
    expandedId: null,
    summary: null,
  };

  function syncUnitOptions() {
    const unitD = t('unit.days');
    ['lp-retention', 'lp-keep-err'].forEach((id) => {
      const sel = document.getElementById(id);
      if (!sel) return;
      Array.from(sel.options).forEach((opt) => {
        if (/^\d+$/.test(opt.value)) opt.textContent = `${opt.value} ${unitD}`;
      });
    });
  }

  const common = window.createSECommon(I18N, () => {
    syncUnitOptions();
    renderLogs();
    if (state.summary) renderSummary(state.summary);
  });
  const { t, esc, fmtNum, fmtTime, api, notify, openConfirm } = common;

  function computeDateFrom() {
    const win = document.getElementById('log-window-filter').value;
    if (win === 'all') return '';
    const hours = { '1h': 1, '24h': 24, '7d': 24 * 7, '30d': 24 * 30 }[win] || 0;
    return hours ? new Date(Date.now() - hours * 3600 * 1000).toISOString() : '';
  }

  function buildFilterQuery(includePaging = true) {
    const p = new URLSearchParams();
    const level = document.getElementById('log-level-filter').value;
    const stage = document.getElementById('log-stage-filter').value;
    const source = document.getElementById('log-source-filter').value;
    const runId = document.getElementById('log-runid-input').value.trim();
    const q = document.getElementById('log-search-input').value.trim();
    const dateFrom = computeDateFrom();
    if (level) p.set('level', level);
    if (stage && stage !== 'all') p.set('stage', stage);
    if (source && source !== 'all') p.set('source', source);
    if (runId) p.set('run_id', runId);
    if (dateFrom) p.set('date_from', dateFrom);
    if (q) p.set('q', q);
    if (includePaging) {
      p.set('limit', String(state.logs.limit));
      p.set('offset', String(state.logs.offset));
    }
    return p.toString();
  }

  function renderLogs() {
    const wrap = document.getElementById('log-table-wrap');
    const pager = document.getElementById('log-pager');
    const meta = document.getElementById('log-count-meta');
    const { rows, total, limit, offset } = state.logs;
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
            <th>${esc(t('col.time'))}</th>
            <th>${esc(t('col.run_id'))}</th>
            <th>${esc(t('col.level'))}</th>
            <th>${esc(t('col.stage'))}</th>
            <th>${esc(t('col.source'))}</th>
            <th>${esc(t('col.elapsed'))}</th>
            <th>${esc(t('col.message'))}</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((r) => `
            <tr data-log-id="${r.log_id}" style="cursor:pointer">
              <td class="tabular">${r.log_id}</td>
              <td class="tabular">${esc(fmtTime(r.calc_time))}</td>
              <td class="tabular">${r.run_id != null ? `#${r.run_id}` : '—'}</td>
              <td><span class="se-level ${esc(r.level)}">${esc(r.level)}</span></td>
              <td><span class="se-tag">${esc(r.stage)}</span></td>
              <td>${esc(r.source)}</td>
              <td class="tabular">${r.elapsed_ms != null ? fmtNum(r.elapsed_ms, 1) : '—'}</td>
              <td class="se-cell-msg" title="${esc(r.message)}">${esc(r.message)}</td>
            </tr>
            ${state.expandedId === r.log_id ? `
              <tr class="se-detail-row">
                <td colspan="8"><pre class="se-json-box">${esc(JSON.stringify(r.detail || {}, null, 2))}</pre></td>
              </tr>` : ''}
          `).join('')}
        </tbody>
      </table>`;

    const pages = Math.max(1, Math.ceil(total / limit));
    const page = Math.floor(offset / limit) + 1;
    pager.innerHTML = `
      <button type="button" class="se-btn mini" id="log-prev" ${page <= 1 ? 'disabled' : ''}>${esc(t('common.prev'))}</button>
      <span class="tabular">${page} / ${pages}</span>
      <button type="button" class="se-btn mini" id="log-next" ${page >= pages ? 'disabled' : ''}>${esc(t('common.next'))}</button>`;
    const pPrev = document.getElementById('log-prev');
    const pNext = document.getElementById('log-next');
    if (pPrev) pPrev.onclick = () => { state.logs.offset = Math.max(0, offset - limit); loadLogs(); };
    if (pNext) pNext.onclick = () => { state.logs.offset = offset + limit; loadLogs(); };
  }

  function renderSummary(s) {
    state.summary = s;
    document.getElementById('kpi-log-total').textContent = s.total;
    document.getElementById('kpi-log-24h').textContent = `${t('recent24_tpl')}${s.recent_24h}`;
    document.getElementById('kpi-err-24h').textContent = s.errors_24h;
    document.getElementById('kpi-warn-24h').textContent = `/ ${s.warns_24h}`;
    document.getElementById('kpi-card-err').classList.toggle('alarm', s.errors_24h > 0);

    const pol = s.policy || {};
    document.getElementById('kpi-ret-days').textContent = pol.retention_days ?? 30;
    document.getElementById('kpi-ret-sub').textContent = `${pol.enabled ? t('common.enabled') : t('common.disabled')} · ${t('maxrows_tpl')}${pol.max_rows ?? 50000}`;
    document.getElementById('kpi-last-del').textContent = pol.last_deleted_count ?? 0;
    document.getElementById('kpi-last-time').textContent = pol.last_cleanup_at ? fmtTime(pol.last_cleanup_at) : '--';
    document.getElementById('logs-range-meta').textContent = s.newest_at ? `${fmtTime(s.oldest_at)} → ${fmtTime(s.newest_at)}` : '--';

    // 填充策略表单（若当前值不在预设列表则动态插入选项）
    const setSelect = (id, val) => {
      const sel = document.getElementById(id);
      if (!sel) return;
      const strVal = String(val);
      if (!Array.from(sel.options).some((o) => o.value === strVal)) {
        const opt = document.createElement('option');
        opt.value = strVal;
        opt.textContent = strVal;
        sel.appendChild(opt);
      }
      sel.value = strVal;
    };
    setSelect('lp-enabled', pol.enabled ?? 1);
    setSelect('lp-min-level', pol.min_level || 'INFO');
    setSelect('lp-retention', pol.retention_days ?? 30);
    setSelect('lp-keep-err', pol.keep_error_days ?? 90);
    setSelect('lp-max-rows', pol.max_rows ?? 50000);
    setSelect('lp-interval', pol.cleanup_interval_hours ?? 6);

    const pend = s.pending_purge || { total_to_delete: 0 };
    document.getElementById('pol-pending-meta').textContent = `${t('msg.preview_tpl')}${pend.total_to_delete}`;

    const bars = document.getElementById('log-stage-bars');
    const stages = s.by_stage || [];
    if (!stages.length) {
      bars.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
    } else {
      const maxC = Math.max(1, ...stages.map((x) => x.count));
      bars.innerHTML = stages.map((x) => `
        <div class="se-stage-item">
          <span class="se-tag">${esc(x.stage)}</span>
          <div class="se-stage-track"><div class="se-stage-fill" style="width:${((x.count / maxC) * 100).toFixed(1)}%"></div></div>
          <span class="tabular" style="text-align:right">${x.count}${x.avg_ms != null ? ` · ${fmtNum(x.avg_ms, 0)}ms` : ''}</span>
        </div>`).join('');
    }
  }

  async function loadSummary() {
    const s = await api('/api/se/logs/summary');
    renderSummary(s);
  }

  async function loadLogs() {
    const qs = buildFilterQuery(true);
    state.logs = await api(`/api/se/logs?${qs}`);
    renderLogs();
  }

  async function loadRunsAndSchedule() {
    const [ov, cfg] = await Promise.all([api('/api/se/overview'), api('/api/config')]);
    const seCfg = (cfg && cfg.tasks && cfg.tasks.se) || { period_seconds: 60, enabled: true };
    const form = document.getElementById('se-schedule-form');
    if (form) {
      form.elements.period_seconds.value = seCfg.period_seconds;
      form.elements.enabled.checked = Boolean(seCfg.enabled);
    }
    const rows = (ov && ov.recent_runs) || [];
    const wrap = document.getElementById('se-runs-table-wrap');
    if (!wrap) return;
    if (!rows.length) {
      wrap.innerHTML = `<div class="se-empty">${esc(t('common.empty'))}</div>`;
      return;
    }
    wrap.innerHTML = `
      <table class="se-table">
        <thead>
          <tr>
            <th>${esc(t('col.run_id'))}</th>
            <th>${esc(t('col.status'))}</th>
            <th>${esc(t('col.time'))}</th>
            <th>${esc(t('col.pass_rate'))}</th>
            <th>${esc(t('col.bad_count'))}</th>
            <th>${esc(t('col.elapsed_s'))}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((r) => `
            <tr>
              <td class="tabular"><button type="button" class="se-btn mini" data-filter-run="${r.run_id}">#${r.run_id}</button></td>
              <td><span class="se-pill ${r.status === 'succeeded' ? 'ok' : r.status === 'failed' ? 'bad' : 'warn'}">${esc(t(`status.${r.status}`))}</span></td>
              <td class="tabular">${esc(fmtTime(r.started_at))}</td>
              <td class="tabular">${r.pass_rate != null ? (Number(r.pass_rate) * 100).toFixed(2) + '%' : '—'}</td>
              <td class="tabular">${r.bad_data_count ?? '—'}</td>
              <td class="tabular">${r.elapsed_seconds != null ? Number(r.elapsed_seconds).toFixed(3) : '—'}</td>
              <td><button type="button" class="se-btn mini" data-filter-run="${r.run_id}">${esc(t('runs.view_log'))}</button></td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  }

  async function refreshAll() {
    try {
      await Promise.all([loadSummary(), loadLogs(), loadRunsAndSchedule()]);
    } catch (err) {
      notify(err.message, true);
    }
  }

  function bindEvents() {
    document.querySelectorAll('#logs-tabs .se-tab').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#logs-tabs .se-tab').forEach((b) => b.classList.toggle('active', b === btn));
        document.querySelectorAll('.se-workspace .se-panel').forEach((p) => p.classList.toggle('active', p.dataset.panel === btn.dataset.view));
      });
    });

    ['log-level-filter', 'log-stage-filter', 'log-source-filter', 'log-window-filter'].forEach((id) => {
      document.getElementById(id).addEventListener('change', () => { state.logs.offset = 0; loadLogs(); });
    });
    const debouncedLoadLogs = common.debounce(() => { state.logs.offset = 0; loadLogs(); }, 200);
    ['log-runid-input', 'log-search-input'].forEach((id) => {
      document.getElementById(id).addEventListener('input', debouncedLoadLogs);
    });

    document.getElementById('log-table-wrap').addEventListener('click', (e) => {
      const tr = e.target.closest('tr[data-log-id]');
      if (!tr) return;
      const lid = Number(tr.dataset.logId);
      state.expandedId = state.expandedId === lid ? null : lid;
      renderLogs();
    });

    document.getElementById('btn-export-logs').addEventListener('click', () => {
      const qs = buildFilterQuery(false);
      window.location.href = `/api/se/logs/export?${qs}`;
    });

    const runsWrap = document.getElementById('se-runs-table-wrap');
    if (runsWrap) {
      runsWrap.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-filter-run]');
        if (!btn) return;
        document.getElementById('log-runid-input').value = btn.dataset.filterRun;
        state.logs.offset = 0;
        document.querySelector('#logs-tabs .se-tab[data-view="stream"]')?.click();
        loadLogs();
      });
    }

    const schedForm = document.getElementById('se-schedule-form');
    if (schedForm) {
      schedForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          await api('/api/schedules/se', {
            method: 'POST',
            body: JSON.stringify({
              period_seconds: Number(schedForm.elements.period_seconds.value),
              enabled: Boolean(schedForm.elements.enabled.checked),
            }),
          });
          notify(t('sched.saved'));
        } catch (err) {
          notify(err.message, true);
        }
      });
    }
    const btnStart = document.getElementById('btn-daemon-start');
    if (btnStart) {
      btnStart.addEventListener('click', async () => {
        try { await api('/api/actions/daemon/start', { method: 'POST', body: '{}' }); notify(t('sched.started')); } catch (err) { notify(err.message, true); }
      });
    }
    const btnStop = document.getElementById('btn-daemon-stop');
    if (btnStop) {
      btnStop.addEventListener('click', async () => {
        try { await api('/api/actions/daemon/stop', { method: 'POST', body: '{}' }); notify(t('sched.stopped')); } catch (err) { notify(err.message, true); }
      });
    }

    document.getElementById('log-policy-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        enabled: Number(document.getElementById('lp-enabled').value),
        min_level: document.getElementById('lp-min-level').value,
        retention_days: Number(document.getElementById('lp-retention').value),
        keep_error_days: Number(document.getElementById('lp-keep-err').value),
        max_rows: Number(document.getElementById('lp-max-rows').value),
        cleanup_interval_hours: Number(document.getElementById('lp-interval').value),
      };
      try {
        await api('/api/se/logs/policy', { method: 'POST', body: JSON.stringify(payload) });
        notify(t('msg.pol_saved'));
        await refreshAll();
      } catch (err) {
        notify(err.message, true);
      }
    });

    document.getElementById('btn-preview-purge').addEventListener('click', async () => {
      try {
        const res = await api('/api/se/logs/purge', {
          method: 'POST',
          body: JSON.stringify({
            dry_run: true,
            retention_days: Number(document.getElementById('lp-retention').value),
            keep_error_days: Number(document.getElementById('lp-keep-err').value),
            max_rows: Number(document.getElementById('lp-max-rows').value),
          }),
        });
        document.getElementById('pol-pending-meta').textContent = `${t('msg.preview_tpl')}${res.total_to_delete}`;
        notify(`${t('msg.preview_tpl')}${res.total_to_delete}`);
      } catch (err) {
        notify(err.message, true);
      }
    });

    document.getElementById('btn-run-purge').addEventListener('click', async () => {
      try {
        const retention_days = Number(document.getElementById('lp-retention').value);
        const keep_error_days = Number(document.getElementById('lp-keep-err').value);
        const max_rows = Number(document.getElementById('lp-max-rows').value);
        const preview = await api('/api/se/logs/purge', {
          method: 'POST',
          body: JSON.stringify({ dry_run: true, retention_days, keep_error_days, max_rows }),
        });
        openConfirm({
          title: t('confirm.purge_title'),
          desc: `${t('confirm.purge_desc')} (${t('msg.preview_tpl')}${preview.total_to_delete})`,
          okText: t('confirm.purge_ok'),
          onConfirm: async () => {
            try {
              const res = await api('/api/se/logs/purge', {
                method: 'POST',
                body: JSON.stringify({ dry_run: false, retention_days, keep_error_days, max_rows }),
              });
              notify(`${t('msg.purged')}${res.deleted}`);
              await refreshAll();
            } catch (err) {
              notify(err.message, true);
            }
          },
        });
      } catch (err) {
        notify(err.message, true);
      }
    });
  }

  // 支持从主画面或其它页通过 ?run_id=xxx 跳转下钻
  const urlRunId = new URLSearchParams(window.location.search).get('run_id');
  if (urlRunId) {
    document.getElementById('log-runid-input').value = urlRunId;
  }

  common.initShell({ onRefresh: refreshAll, afterRunSE: refreshAll });
  syncUnitOptions();
  bindEvents();
  refreshAll();
})();
