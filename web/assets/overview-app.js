/* PAS 运行总览：SE → LF → CA 全平台联动态势台（三语 + 8 主题 + 一键串联 + 级联开关） */
(() => {
  'use strict';

  const THEMES = [
    'minimalist-light', 'precision-dark', 'bento-grid', 'glassmorphism',
    'editorial', 'sci-fi-cyan', 'sci-fi-purple', 'sci-fi-matrix',
  ];

  const I18N = {
    'zh-CN': {
      'brand.subtitle': '在线分析平台', 'nav.overview': '总览', 'nav.analysis': '分析功能', 'nav.ops': '运行管理',
      'nav.se': '状态估计 SE', 'nav.lf': '潮流分析 LF', 'nav.ca': '静态安全 CA',
      'nav.runs': '运行历史', 'nav.measurements': '设备量测', 'nav.limits': '安全限值', 'nav.workspace': '工作目录', 'nav.settings': '系统设置',
      'service.checking': '服务检查中', 'service.daemon': '周期调度运行中', 'service.online': 'Web 在线 · 周期停止', 'service.offline': '服务暂不可用',
      'theme.light': '极简明亮', 'theme.dark': '精密暗黑', 'theme.bento': '便当盒网格', 'theme.glass': '毛玻璃拟态',
      'theme.editorial': '编辑杂志', 'theme.cyan': '科幻 · 电光青', 'theme.purple': '科幻 · 赛博紫', 'theme.matrix': '科幻 · 矩阵绿',
      'title.overview': 'SE → LF → CA 全平台联动态势',
      'action.run_chain': '串联执行 SE→LF→CA', 'action.refresh': '刷新', 'action.exec': '执行',
      'action.enter': '进入 SE →', 'action.enter_lf': '进入 LF →', 'action.enter_ca': '进入 CA →', 'action.more': '全部 →',
      'ov.alerts': '跨模块重点告警', 'ov.recent_runs': '三模块联合运行动态',
      'col.module': '模块', 'col.severity': '等级', 'col.target': '对象', 'col.detail': '详情',
      'col.source': '来源', 'col.summary': '摘要', 'col.elapsed': '耗时',
      'sync.all': '全链路已同步', 'sync.partial': '待级联同步', 'sync.none': '未就绪',
      'msg.running_chain': '正在按顺序串联执行 SE → LF → CA…',
      'msg.chain_ok': 'SE → LF → CA 全链路串联执行完成',
      'msg.cascade_saved': '级联自动触发策略已更新',
    },
    'en-US': {
      'brand.subtitle': 'Online Analysis', 'nav.overview': 'Overview', 'nav.analysis': 'Analysis', 'nav.ops': 'Operations',
      'nav.se': 'State Estimation SE', 'nav.lf': 'Load Flow LF', 'nav.ca': 'Security CA',
      'nav.runs': 'Runs', 'nav.measurements': 'Measurements', 'nav.limits': 'Limits', 'nav.workspace': 'Workspace', 'nav.settings': 'Settings',
      'service.checking': 'Checking', 'service.daemon': 'Daemon Running', 'service.online': 'Web Online · Idle', 'service.offline': 'Offline',
      'theme.light': 'Minimal Light', 'theme.dark': 'Precision Dark', 'theme.bento': 'Bento Grid', 'theme.glass': 'Glassmorphism',
      'theme.editorial': 'Editorial', 'theme.cyan': 'Sci-Fi Cyan', 'theme.purple': 'Sci-Fi Purple', 'theme.matrix': 'Sci-Fi Matrix',
      'title.overview': 'SE → LF → CA Pipeline Overview',
      'action.run_chain': 'Run SE→LF→CA Chain', 'action.refresh': 'Refresh', 'action.exec': 'Run',
      'action.enter': 'Open SE →', 'action.enter_lf': 'Open LF →', 'action.enter_ca': 'Open CA →', 'action.more': 'All →',
      'ov.alerts': 'Cross-Module Alerts', 'ov.recent_runs': 'Unified Run Feed',
      'col.module': 'Mod', 'col.severity': 'Level', 'col.target': 'Target', 'col.detail': 'Detail',
      'col.source': 'Source', 'col.summary': 'Summary', 'col.elapsed': 'Time',
      'sync.all': 'Chain Synced', 'sync.partial': 'Out of Sync', 'sync.none': 'Not Ready',
      'msg.running_chain': 'Running SE → LF → CA sequentially…',
      'msg.chain_ok': 'SE → LF → CA chain completed',
      'msg.cascade_saved': 'Cascade policy saved',
    },
    'ru-RU': {
      'brand.subtitle': 'Онлайн-анализ', 'nav.overview': 'Обзор', 'nav.analysis': 'Анализ', 'nav.ops': 'Управление',
      'nav.se': 'Оценка сост. SE', 'nav.lf': 'Потоки LF', 'nav.ca': 'Надежность CA',
      'nav.runs': 'Запуски', 'nav.measurements': 'Измерения', 'nav.limits': 'Пределы', 'nav.workspace': 'Каталог', 'nav.settings': 'Настройки',
      'service.checking': 'Проверка', 'service.daemon': 'Планировщик активен', 'service.online': 'Веб онлайн', 'service.offline': 'Нет связи',
      'theme.light': 'Светлая', 'theme.dark': 'Темная', 'theme.bento': 'Бенто', 'theme.glass': 'Стекло',
      'theme.editorial': 'Журнал', 'theme.cyan': 'Неон циан', 'theme.purple': 'Кибер фиол.', 'theme.matrix': 'Матрица',
      'title.overview': 'Конвейер SE → LF → CA',
      'action.run_chain': 'Запуск SE→LF→CA', 'action.refresh': 'Обновить', 'action.exec': 'Пуск',
      'action.enter': 'SE →', 'action.enter_lf': 'LF →', 'action.enter_ca': 'CA →', 'action.more': 'Все →',
      'ov.alerts': 'Сводка тревог', 'ov.recent_runs': 'Лента расчетов',
      'col.module': 'Мод', 'col.severity': 'Уровень', 'col.target': 'Объект', 'col.detail': 'Детали',
      'col.source': 'Источник', 'col.summary': 'Итог', 'col.elapsed': 'Время',
      'sync.all': 'Синхронизировано', 'sync.partial': 'Требует синхр.', 'sync.none': 'Нет данных',
      'msg.running_chain': 'Последовательный запуск SE → LF → CA…',
      'msg.chain_ok': 'Цепочка SE → LF → CA завершена',
      'msg.cascade_saved': 'Каскадный режим обновлен',
    },
  };

  const st = {
    lang: localStorage.getItem('pas_se_lang') || 'zh-CN',
    theme: localStorage.getItem('pas_se_theme') || 'minimalist-light',
  };

  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  const num = (v, d = 2) => (v == null || Number.isNaN(Number(v)) ? '—' : Number(v).toFixed(d));
  const t = (k) => (I18N[st.lang] || I18N['zh-CN'])[k] ?? I18N['zh-CN'][k] ?? k;

  async function api(url, body = null) {
    const opts = body != null ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {};
    const resp = await fetch(url, opts);
    const data = await resp.json();
    if (!resp.ok || data.ok === false) throw new Error(data.error || `HTTP ${resp.status}`);
    return data.data;
  }

  let timer = null;
  function notify(msg, isErr = false) {
    const el = $('#notice');
    if (!el) return;
    el.textContent = msg;
    el.className = `notice ${isErr ? 'error' : 'ok'}`;
    el.hidden = false;
    clearTimeout(timer);
    timer = setTimeout(() => { el.hidden = true; }, isErr ? 6000 : 3500);
  }

  function applyTheme(theme) {
    st.theme = THEMES.includes(theme) ? theme : 'minimalist-light';
    document.documentElement.dataset.theme = st.theme;
    localStorage.setItem('pas_se_theme', st.theme);
    if ($('#theme-select')) $('#theme-select').value = st.theme;
  }

  function applyLang(lang) {
    st.lang = I18N[lang] ? lang : 'zh-CN';
    document.documentElement.lang = st.lang;
    localStorage.setItem('pas_se_lang', st.lang);
    if ($('#lang-select')) $('#lang-select').value = st.lang;
    $$('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
  }

  function kvRows(pairs) {
    return pairs.map(([k, v]) => `<div class="se-kv-row"><span>${esc(k)}</span><strong class="tabular">${esc(v)}</strong></div>`).join('');
  }

  function sevCls(sev) {
    if (sev === 'critical' || sev === 'high' || sev === '严重' || sev === '高') return 'bad';
    if (sev === 'medium' || sev === '中') return 'warn';
    if (sev === 'low' || sev === '低') return 'neutral';
    return 'ok';
  }

  async function loadOverview() {
    const d = await api('/api/pipeline/status');
    const ws = d.workspace || {};
    const lk = d.linkage || {};
    const sched = d.scheduler || {};

    if ($('#service-dot')) $('#service-dot').className = `status-dot ${sched.daemon_running ? 'ok' : ''}`;
    if ($('#service-state')) $('#service-state').textContent = sched.daemon_running ? t('service.daemon') : t('service.online');
    if ($('#ov-scenario-meta')) $('#ov-scenario-meta').textContent = `${ws.runtime || 'realtime'} / ${ws.scenario || '—'}`;

    const syncPill = $('#ov-sync-pill');
    if (syncPill) {
      if (lk.all_synced) {
        syncPill.textContent = `${t('sync.all')} (SE #${lk.se_run_id} → LF #${lk.lf_run_id} → CA #${lk.ca_run_id})`;
        syncPill.className = 'se-pill ok tabular';
      } else if (lk.se_run_id || lk.lf_run_id || lk.ca_run_id) {
        syncPill.textContent = t('sync.partial');
        syncPill.className = 'se-pill warn';
      } else {
        syncPill.textContent = t('sync.none');
        syncPill.className = 'se-pill neutral';
      }
    }

    $('#chk-se-lf').checked = Boolean(d.cascade_policy?.se_to_lf);
    $('#chk-lf-ca').checked = Boolean(d.cascade_policy?.lf_to_ca);
    $('#arrow-se-lf').className = `pas-chain-arrow ${lk.se_lf_synced ? 'synced' : 'stale'}`;
    $('#arrow-lf-ca').className = `pas-chain-arrow ${lk.lf_ca_synced ? 'synced' : 'stale'}`;

    // 1. SE Card
    const se = d.se?.latest;
    $('#ov-se-pill').textContent = se ? (se.converged ? `收敛 · #${se.run_id}` : `未收敛 · #${se.run_id}`) : '—';
    $('#ov-se-pill').className = `se-pill tabular ${se ? (se.converged ? 'ok' : 'bad') : 'neutral'}`;
    $('#ov-se-kv').innerHTML = kvRows([
      ['量测合格率', se ? `${num((se.pass_rate || 0) * 100, 2)}%` : '—'],
      ['有效量测 / 坏数据', se ? `${se.meas_count ?? 0} / ${se.bad_data_count ?? 0}` : '—'],
      ['总残差 / 迭代', se ? `${num(se.total_residual, 3)} / ${se.iterations ?? 0}` : '—'],
      ['计算用时', se ? `${num(se.elapsed_seconds, 2)} s` : '—'],
    ]);

    // 2. LF Card
    const lf = d.lf?.latest;
    $('#ov-lf-pill').textContent = lf ? (lf.converged ? `收敛 · #${lf.run_id}` : `未收敛 · #${lf.run_id}`) : '—';
    $('#ov-lf-pill').className = `se-pill tabular ${lf ? (lf.converged ? 'ok' : 'bad') : 'neutral'}`;
    $('#ov-lf-kv').innerHTML = kvRows([
      ['基态溯源 SE', lf?.source_se_run_id ? `SE #${lf.source_se_run_id} ${lk.se_lf_synced ? '✓' : '⚠'}` : '模型默认'],
      ['发电 / 负荷', lf ? `${num(lf.total_gen_p, 1)} / ${num(lf.total_load_p, 1)} ${lf.p_unit || 'kW'}` : '—'],
      ['全网网损率', lf ? `${num(lf.loss_rate, 3)}% (${num(lf.total_loss_p, 2)} ${lf.p_unit || 'kW'})` : '—'],
      ['最大负载 / 越限', lf ? `${num(lf.max_loading_pct, 1)}% / ${(lf.v_violation_count || 0) + (lf.overload_count || 0)}` : '—'],
    ]);

    // 3. CA Card
    const ca = d.ca?.latest;
    $('#ov-ca-pill').textContent = ca ? `${ca.risk_level} · ${num(ca.security_score, 1)}` : '—';
    $('#ov-ca-pill').className = `se-pill tabular ${ca ? sevCls(ca.risk_level) : 'neutral'}`;
    $('#ov-ca-kv').innerHTML = kvRows([
      ['基态溯源 LF', ca?.source_lf_run_id ? `LF #${ca.source_lf_run_id} ${lk.lf_ca_synced ? '✓' : '⚠'}` : '现场基态'],
      ['N-0 基态风险', ca ? String(ca.n0_risk_count) : '—'],
      ['N-1 扫描 / 风险', ca ? `${ca.n1_total_count} / ${ca.n1_risk_count}` : '—'],
      ['最严重预想故障', ca?.worst_contingency || '—'],
    ]);

    // Chain banner
    const ch = d.chain;
    const banner = $('#ov-chain-banner');
    if (banner && ch?.last_chain?.steps?.length) {
      const stepsTxt = ch.last_chain.steps.map((s) => `${s.task.toUpperCase()} #${s.run_id ?? '—'} (${s.ok ? '✓' : '✗'} ${s.elapsed_seconds}s)`).join(' → ');
      banner.innerHTML = `<strong>最近串联执行：</strong> ${esc(stepsTxt)}`;
      banner.hidden = false;
    }

    // Alerts
    const alerts = d.alerts || [];
    $('#ov-alert-count').textContent = String(alerts.length);
    $('#ov-alert-count').className = `se-pill tabular ${alerts.length ? 'warn' : 'ok'}`;
    $('#ov-alerts-tbody').innerHTML = alerts.length ? alerts.map((a) => `<tr>
      <td><span class="se-tag">${esc(a.module)}</span></td>
      <td><span class="se-pill ${sevCls(a.severity)}">${esc(a.severity)}</span></td>
      <td><a class="se-link" href="${esc(a.href)}">${esc(a.target)}</a></td>
      <td>${esc(a.detail)}</td>
    </tr>`).join('') : `<tr><td colspan="4" class="se-empty">—</td></tr>`;

    // Unified Runs
    const runs = d.recent_runs || [];
    $('#ov-runs-tbody').innerHTML = runs.length ? runs.map((r) => `<tr>
      <td><span class="se-tag">${esc(r.module)}</span></td>
      <td class="tabular"><a class="se-link" href="${esc(r.href)}">#${r.run_id}</a></td>
      <td>${esc(r.source || '—')}</td>
      <td>${esc(r.summary || '—')}</td>
      <td class="tabular">${r.elapsed_seconds != null ? `${num(r.elapsed_seconds, 2)} s` : '—'}</td>
    </tr>`).join('') : `<tr><td colspan="5" class="se-empty">—</td></tr>`;
  }

  function bind() {
    $('#theme-select')?.addEventListener('change', (e) => applyTheme(e.target.value));
    $('#lang-select')?.addEventListener('change', (e) => { applyLang(e.target.value); loadOverview().catch(() => {}); });
    $('#btn-refresh')?.addEventListener('click', () => loadOverview().catch((e) => notify(e.message, true)));

    $('#chk-se-lf')?.addEventListener('change', async (e) => {
      try {
        await api('/api/pipeline/cascade', { se_to_lf: e.target.checked });
        notify(t('msg.cascade_saved'));
      } catch (err) { notify(err.message, true); e.target.checked = !e.target.checked; }
    });
    $('#chk-lf-ca')?.addEventListener('change', async (e) => {
      try {
        await api('/api/pipeline/cascade', { lf_to_ca: e.target.checked });
        notify(t('msg.cascade_saved'));
      } catch (err) { notify(err.message, true); e.target.checked = !e.target.checked; }
    });

    $('#btn-run-chain')?.addEventListener('click', async () => {
      const btn = $('#btn-run-chain');
      btn.disabled = true;
      notify(t('msg.running_chain'));
      try {
        await api('/api/actions/run-chain', { tasks: ['se', 'lf', 'ca'], async: false });
        notify(t('msg.chain_ok'));
        await loadOverview();
      } catch (err) {
        notify(err.message, true);
        await loadOverview().catch(() => {});
      } finally {
        btn.disabled = false;
      }
    });

    $$('[data-trigger]').forEach((b) => b.addEventListener('click', async () => {
      const task = b.dataset.trigger;
      b.disabled = true;
      try {
        await api('/api/actions/trigger', { task });
        notify(`${task.toUpperCase()} 执行完成`);
        await loadOverview();
      } catch (err) {
        notify(err.message, true);
      } finally {
        b.disabled = false;
      }
    }));
  }

  applyTheme(st.theme);
  applyLang(st.lang);
  bind();
  loadOverview().catch((err) => notify(err.message, true));
  setInterval(() => { if (!document.hidden) loadOverview().catch(() => {}); }, 10000);
})();
