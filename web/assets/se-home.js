/* 新版三栏 EMS 状态估计主画面逻辑（真实数据驱动 + 今日/昨日合格率双曲线） */
(() => {
  'use strict';

  const I18N = {
    'zh-CN': {
      'title.home': '状态估计主画面',
      'sec.meas_ctrl': '量测分析与控制',
      'sec.calc_ctrl': '计算控制',
      'sec.result': '计算结果',
      'sec.metrics': '指标统计',
      'sub.obs': '可观测性分析',
      'sub.prefilter': '预处理信息',
      'sub.control': '量测控制',
      'sub.params': '参数管理',
      'm.bus_count': '母线总数（交/直）',
      'm.meas_count': '量测总数',
      'm.valid_meas': '有效量测数',
      'm.state_count': '状态变量数',
      'm.rank': '雅可比矩阵秩',
      'm.deficiency': '不可观测点数',
      'm.redundancy': '量测冗余度',
      'm.pf_total': '预过滤总数',
      'm.pf_rate': '预过滤占比',
      'm.pf_rule': '越限规则命中',
      'm.pf_kernel': '内核预过滤',
      'm.pf_rules': '预过滤规则（启/总）',
      'm.nomeas': '缺测 / 坏质量',
      'm.suspect': '可疑遥信数',
      'm.pseudo_stat': '伪遥信（启/总）',
      'm.pseudo_meas': '伪遥测（配/生）',
      'm.policy': '遥测屏蔽（启/总）',
      'm.bad_total': '坏量测（未确/总）',
      'm.branches': '交直流支路数',
      'm.converters': '换流器数',
      'm.devices': '建模设备总数',
      'btn.start_calc': '启动计算',
      'btn.pause_calc': '暂停周期',
      'btn.resume_calc': '启动周期',
      'btn.open_flow': '打开潮流图',
      'lbl.snap_time': '状态估计断面时间',
      'lbl.model_scene': '当前模型 / 场景',
      'p.periodic': '周期运行',
      'p.cycle': '执行周期',
      'p.trigger': '触发方式',
      'p.flat': '平启动',
      'p.tol': '收敛精度判据',
      'p.diffstep': '数值差分步长',
      'p.maxiter': '最大迭代次数',
      'p.badeps': '坏数据门槛',
      'p.badmax': '坏数据上限',
      'p.badstep': '坏数据单步上限',
      'p.pweight': '伪量测权重',
      'p.pmax': '定向伪量测上限',
      'p.vfloor': '电压下限保护',
      'p.pftol': '初值潮流容差',
      'p.pfiter': '初值潮流迭代',
      'r.cur_pass': '当前合格率',
      'r.today_avg': '今日平均',
      'r.yest_avg': '对比日平均',
      'r.conv_rate': '当日收敛率',
      'res.start': '计算开始时间',
      'res.end': '计算结束时间',
      'res.elapsed': '计算耗时',
      'res.iters': '迭代次数',
      'res.obj': '目标函数 J(x)',
      'res.residual': '总残差 / 最大',
      'res.bad': '大误差点数',
      'st.host': '运行主机',
      'st.runs': '当天运行次数',
      'st.conv_cnt': '收敛次数',
      'st.conv_rate': '收敛率',
      'st.pass_rate': '量测合格率',
      'st.good_valid': '合格 / 有效量测',
      'st.coverage': '量测覆盖率',
      'foot.run_info': '运行信息',
      'link.more': '更多…',
      'link.pseudo': '伪量测…',
      'link.bad': '坏量测…',
      'yes': '是',
      'no': '否',
      'conv.ok': '全网收敛',
      'conv.fail': '未收敛',
      'lg.today': '今日合格率',
      'lg.yest': '对比日合格率',
      'msg.daemon_on': '周期调度已启动',
      'msg.daemon_off': '周期调度已暂停',
    },
    'en-US': {
      'title.home': 'State Estimation Home',
      'sec.meas_ctrl': 'Measurement & Control',
      'sec.calc_ctrl': 'Calculation Control',
      'sec.result': 'Calculation Result',
      'sec.metrics': 'Daily Metrics',
      'sub.obs': 'Observability',
      'sub.prefilter': 'Prefilter Summary',
      'sub.control': 'Measurement Control',
      'sub.params': 'Parameters',
      'm.bus_count': 'Buses (AC/DC)',
      'm.meas_count': 'Total Meas',
      'm.valid_meas': 'Valid Meas',
      'm.state_count': 'State Vars',
      'm.rank': 'Jacobian Rank',
      'm.deficiency': 'Unobservable',
      'm.redundancy': 'Redundancy',
      'm.pf_total': 'Prefiltered',
      'm.pf_rate': 'Prefilter Rate',
      'm.pf_rule': 'Rule Hits',
      'm.pf_kernel': 'Kernel Filter',
      'm.pf_rules': 'Rules (On/All)',
      'm.nomeas': 'Missing / Bad Qual',
      'm.suspect': 'Suspect Status',
      'm.pseudo_stat': 'Pseudo Stat (On/All)',
      'm.pseudo_meas': 'Pseudo Meas (Cfg/Eff)',
      'm.policy': 'Policy (On/All)',
      'm.bad_total': 'Bad (Unack/All)',
      'm.branches': 'AC/DC Branches',
      'm.converters': 'Converters',
      'm.devices': 'Model Devices',
      'btn.start_calc': 'Run SE Now',
      'btn.pause_calc': 'Pause Cycle',
      'btn.resume_calc': 'Start Cycle',
      'btn.open_flow': 'Power Flow Map',
      'lbl.snap_time': 'SE Snapshot Time',
      'lbl.model_scene': 'Model / Scenario',
      'p.periodic': 'Periodic',
      'p.cycle': 'Cycle Period',
      'p.trigger': 'Trigger Mode',
      'p.flat': 'Flat Start',
      'p.tol': 'Tolerance',
      'p.diffstep': 'Diff Step',
      'p.maxiter': 'Max Iterations',
      'p.badeps': 'Bad Threshold',
      'p.badmax': 'Bad Max Count',
      'p.badstep': 'Bad Step Limit',
      'p.pweight': 'Pseudo Weight',
      'p.pmax': 'Targeted Pseudo Max',
      'p.vfloor': 'Voltage Floor',
      'p.pftol': 'Init PF Tol',
      'p.pfiter': 'Init PF Max Iter',
      'r.cur_pass': 'Current Pass',
      'r.today_avg': 'Today Avg',
      'r.yest_avg': 'Compare Avg',
      'r.conv_rate': 'Conv Rate',
      'res.start': 'Start Time',
      'res.end': 'End Time',
      'res.elapsed': 'Elapsed',
      'res.iters': 'Iterations',
      'res.obj': 'Objective J(x)',
      'res.residual': 'Total / Max Res',
      'res.bad': 'Bad Points',
      'st.host': 'Host',
      'st.runs': 'Today Runs',
      'st.conv_cnt': 'Converged',
      'st.conv_rate': 'Conv Rate',
      'st.pass_rate': 'Pass Rate',
      'st.good_valid': 'Good / Valid',
      'st.coverage': 'Coverage',
      'foot.run_info': 'Run Info',
      'link.more': 'More…',
      'link.pseudo': 'Pseudo…',
      'link.bad': 'Bad…',
      'yes': 'Yes',
      'no': 'No',
      'conv.ok': 'Converged',
      'conv.fail': 'Diverged',
      'lg.today': 'Today Pass Rate',
      'lg.yest': 'Compare Pass Rate',
      'msg.daemon_on': 'Periodic scheduler started',
      'msg.daemon_off': 'Periodic scheduler paused',
    },
    'ru-RU': {
      'title.home': 'Главный экран SE',
      'sec.meas_ctrl': 'Анализ измерений',
      'sec.calc_ctrl': 'Управление расчётом',
      'sec.result': 'Результаты',
      'sec.metrics': 'Статистика',
      'sub.obs': 'Наблюдаемость',
      'sub.prefilter': 'Предфильтр',
      'sub.control': 'Контроль изм.',
      'sub.params': 'Параметры',
      'm.bus_count': 'Узлы (AC/DC)',
      'm.meas_count': 'Измерений',
      'm.valid_meas': 'Валидных ТИ',
      'm.state_count': 'Перем. сост.',
      'm.rank': 'Ранг матрицы',
      'm.deficiency': 'Ненаблюдаемых',
      'm.redundancy': 'Избыточность',
      'm.pf_total': 'Отфильтровано',
      'm.pf_rate': 'Доля фильтра',
      'm.pf_rule': 'По правилам',
      'm.pf_kernel': 'Ядро SE',
      'm.pf_rules': 'Правила (вкл/все)',
      'm.nomeas': 'Пропуски',
      'm.suspect': 'Подозр. ТС',
      'm.pseudo_stat': 'Псевдо-ТС',
      'm.pseudo_meas': 'Псевдо-ТИ',
      'm.policy': 'Блок. (вкл/все)',
      'm.bad_total': 'Плохие ТИ',
      'm.branches': 'Ветви AC/DC',
      'm.converters': 'Преобразоват.',
      'm.devices': 'Оборудование',
      'btn.start_calc': 'Запустить SE',
      'btn.pause_calc': 'Пауза цикла',
      'btn.resume_calc': 'Старт цикла',
      'btn.open_flow': 'Схема потоков',
      'lbl.snap_time': 'Время среза SE',
      'lbl.model_scene': 'Модель / Сценарий',
      'p.periodic': 'Цикл',
      'p.cycle': 'Период',
      'p.trigger': 'Триггер',
      'p.flat': 'Плоский старт',
      'p.tol': 'Точность',
      'p.diffstep': 'Шаг дифф.',
      'p.maxiter': 'Макс. итераций',
      'p.badeps': 'Порог сбоя',
      'p.badmax': 'Макс. плохих',
      'p.badstep': 'Лимит за шаг',
      'p.pweight': 'Вес псевдо-ТИ',
      'p.pmax': 'Макс. псевдо-ТИ',
      'p.vfloor': 'Мин. напр.',
      'p.pftol': 'Точность УР',
      'p.pfiter': 'Итерац. УР',
      'r.cur_pass': 'Текущ. годн.',
      'r.today_avg': 'Сред. сегодня',
      'r.yest_avg': 'Сред. вчера',
      'r.conv_rate': 'Сходимость',
      'res.start': 'Начало',
      'res.end': 'Окончание',
      'res.elapsed': 'Время',
      'res.iters': 'Итерации',
      'res.obj': 'Цель J(x)',
      'res.residual': 'Сумм. / Макс.',
      'res.bad': 'Плохих точек',
      'st.host': 'Узел',
      'st.runs': 'Запусков',
      'st.conv_cnt': 'Сошлось',
      'st.conv_rate': 'Сходимость',
      'st.pass_rate': 'Доля годных',
      'st.good_valid': 'Годных / Всего',
      'st.coverage': 'Охват',
      'foot.run_info': 'Статус',
      'link.more': 'Далее…',
      'link.pseudo': 'Псевдо…',
      'link.bad': 'Сбои…',
      'yes': 'Да',
      'no': 'Нет',
      'conv.ok': 'Сходится',
      'conv.fail': 'Не сходится',
      'lg.today': 'Сегодня',
      'lg.yest': 'Предыдущий',
      'msg.daemon_on': 'Цикл запущен',
      'msg.daemon_off': 'Цикл остановлен',
    },
  };

  let homeData = null;

  const common = window.createSECommon(I18N, () => {
    if (homeData) renderHome(homeData);
  });
  const { t, esc, fmtNum, fmtTime, api, notify } = common;

  function setVal(id, text, cls = '') {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    el.className = `v tabular${cls ? ' ' + cls : ''}`;
  }

  function renderPassChart(seriesObj) {
    const host = document.getElementById('home-pass-chart');
    const legend = document.getElementById('home-pass-legend');
    const today = seriesObj?.today || [];
    const yest = seriesObj?.yesterday || [];

    legend.innerHTML = `
      <span><i style="background:var(--sem-danger)"></i>${esc(t('lg.today'))} (${esc(seriesObj?.today_date || '')})</span>
      <span><i style="background:var(--text-secondary)"></i>${esc(t('lg.yest'))} (${esc(seriesObj?.compare_date || '')})</span>`;

    if (!today.length && !yest.length) {
      host.innerHTML = `<div class="se-empty">—</div>`;
      return;
    }

    const w = Math.max(420, host.clientWidth || 620);
    const h = Math.max(175, host.clientHeight || 220);
    const pad = { top: 14, right: 24, bottom: 24, left: 46 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    const allVals = [...today, ...yest].map((p) => Number(p.pass_rate));
    let minY = Math.min(...allVals);
    let maxY = Math.max(...allVals);
    if (maxY - minY < 1.0) {
      minY = Math.max(0, Math.floor((minY - 1.5) * 10) / 10);
      maxY = Math.min(100, Math.ceil((maxY + 0.5) * 10) / 10);
      if (maxY <= minY) { minY = 95; maxY = 100; }
    } else {
      minY = Math.max(0, Math.floor(minY - 0.5));
      maxY = Math.min(100, Math.ceil(maxY + 0.5));
    }

    const xOf = (minOfDay) => pad.left + (Math.max(0, Math.min(1440, minOfDay)) / 1440) * plotW;
    const yOf = (val) => pad.top + plotH - ((val - minY) / (maxY - minY || 1)) * plotH;

    const yTicks = [0, 0.25, 0.5, 0.75, 1].map((r) => minY + (maxY - minY) * r);
    const xHours = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24];

    const polyStr = (arr) => arr.map((p) => `${xOf(p.minute).toFixed(1)},${yOf(p.pass_rate).toFixed(1)}`).join(' ');

    host.innerHTML = `
      <svg viewBox="0 0 ${w} ${h}" width="100%" height="100%" preserveAspectRatio="none">
        <rect x="${pad.left}" y="${pad.top}" width="${plotW}" height="${plotH}" fill="var(--bg-subtle)" opacity="0.45"/>
        ${yTicks.map((v) => {
          const y = yOf(v);
          return `<line x1="${pad.left}" y1="${y.toFixed(1)}" x2="${w - pad.right}" y2="${y.toFixed(1)}" stroke="var(--grid-line)" stroke-dasharray="2 3"/>
                  <text x="${pad.left - 6}" y="${(y + 3.5).toFixed(1)}" text-anchor="end" fill="var(--text-secondary)" font-size="10.5" class="tabular">${v.toFixed(1)}</text>`;
        }).join('')}
        ${xHours.map((hr) => {
          const x = xOf(hr * 60);
          const lbl = `${String(hr).padStart(2, '0')}:00`;
          return `<line x1="${x.toFixed(1)}" y1="${pad.top}" x2="${x.toFixed(1)}" y2="${pad.top + plotH}" stroke="var(--grid-line)" stroke-dasharray="2 3"/>
                  <text x="${x.toFixed(1)}" y="${h - 6}" text-anchor="${hr === 0 ? 'start' : hr === 24 ? 'end' : 'middle'}" fill="var(--text-secondary)" font-size="10" class="tabular">${lbl}</text>`;
        }).join('')}
        ${yest.length > 1 ? `<polyline fill="none" stroke="var(--text-secondary)" stroke-width="1.5" opacity="0.8" points="${polyStr(yest)}"/>` : ''}
        ${yest.map((p) => `<circle cx="${xOf(p.minute).toFixed(1)}" cy="${yOf(p.pass_rate).toFixed(1)}" r="2.2" fill="var(--text-secondary)"><title>${esc(seriesObj.compare_date)} ${p.time_hm} · ${p.pass_rate.toFixed(2)}% (#${p.run_id})</title></circle>`).join('')}
        ${today.length > 1 ? `<polyline fill="none" stroke="var(--sem-danger)" stroke-width="2" points="${polyStr(today)}"/>` : ''}
        ${today.map((p) => `<circle cx="${xOf(p.minute).toFixed(1)}" cy="${yOf(p.pass_rate).toFixed(1)}" r="2.8" fill="var(--sem-danger)"><title>${esc(seriesObj.today_date)} ${p.time_hm} · ${p.pass_rate.toFixed(2)}% (#${p.run_id})</title></circle>`).join('')}
      </svg>`;
  }

  function renderHome(d) {
    homeData = d;
    const latest = d.latest;
    const obs = d.observability || {};
    const pf = d.prefilter || {};
    const ctrl = d.control || {};
    const params = d.params || {};
    const sched = d.schedule || {};
    const ts = d.today_stats || {};
    const rt = d.runtime || {};

    // 顶栏状态
    const convPill = document.getElementById('home-conv-pill');
    if (latest) {
      const ok = Boolean(latest.converged);
      convPill.className = `se-pill ${ok ? 'ok' : 'bad'}`;
      convPill.textContent = ok ? t('conv.ok') : t('conv.fail');
      document.getElementById('home-run-meta').textContent = `#${latest.run_id} · ${fmtTime(latest.calc_time)}`;
    } else {
      convPill.className = 'se-pill neutral';
      convPill.textContent = '—';
      document.getElementById('home-run-meta').textContent = '—';
    }

    // 左栏：量测分析与控制
    const busText = obs.ac_bus_count != null && obs.dc_bus_count != null
      ? `${obs.bus_count ?? 0} (${obs.ac_bus_count}/${obs.dc_bus_count})`
      : String(obs.bus_count ?? 0);
    setVal('h-bus-count', busText);
    setVal('h-meas-count', String(obs.meas_count ?? 0));
    setVal('h-valid-meas', String(obs.valid_meas_count ?? 0));
    setVal('h-state-count', String(obs.state_count ?? 0));
    setVal('h-rank', String(obs.rank ?? 0));
    setVal('h-deficiency', String(obs.deficiency ?? 0), (obs.deficiency || 0) > 0 ? 'bad' : 'ok');
    setVal('h-redundancy', obs.redundancy != null ? `${Number(obs.redundancy).toFixed(2)}x` : '—');

    setVal('h-pf-total', String(pf.total ?? 0), (pf.total || 0) > 0 ? 'warn' : '');
    setVal('h-pf-rate', pf.prefilter_rate != null ? `${Number(pf.prefilter_rate).toFixed(1)}%` : '—');
    setVal('h-pf-rule', String(pf.by_rule ?? 0));
    setVal('h-pf-kernel', String(pf.by_kernel ?? 0));
    setVal('h-pf-rules', `${pf.rule_enabled ?? 0} / ${pf.rule_total ?? 0}`);
    setVal('h-nomeas', String(pf.nomeas_count ?? 0), (pf.nomeas_count || 0) > 0 ? 'warn' : '');
    setVal('h-suspect', String(pf.suspect_count ?? 0), (pf.suspect_count || 0) > 0 ? 'bad' : '');

    setVal('h-pseudo-stat', `${ctrl.pseudo_stat_enabled ?? 0} / ${ctrl.pseudo_stat_total ?? 0}`);
    setVal('h-pseudo-meas', `${ctrl.pseudo_meas_enabled ?? 0} / ${ctrl.pseudo_result_total ?? 0}`);
    setVal('h-policy', `${ctrl.policy_enabled ?? 0} / ${ctrl.policy_total ?? 0}`);
    setVal('h-bad-left', `${ctrl.bad_unacked ?? 0} / ${ctrl.bad_total ?? 0}`, (ctrl.bad_total || 0) > 0 ? 'bad' : 'ok');
    setVal('h-branches', String(ctrl.branch_count ?? 0));
    setVal('h-converters', String(ctrl.converter_count ?? 0));
    setVal('h-dev-total', String(ctrl.total_devices ?? 0));

    // 中栏：计算控制
    const btnToggle = document.getElementById('btn-home-toggle-daemon');
    btnToggle.dataset.running = rt.daemon_running ? '1' : '0';
    btnToggle.textContent = rt.daemon_running ? t('btn.pause_calc') : t('btn.resume_calc');

    document.getElementById('h-snap-time').textContent = latest ? fmtTime(latest.calc_time) : '—';
    document.getElementById('h-model-scene').textContent = rt.scenario ? `${rt.runtime || 'realtime'} / ${rt.scenario}` : '—';

    setVal('h-p-periodic', sched.enabled ? t('yes') : t('no'), sched.enabled ? 'ok' : '');
    setVal('h-p-cycle', sched.period_seconds != null ? `${sched.period_seconds} s` : `${params.do_cycle ?? 60} s`);
    setVal('h-p-trigger', String(params.calc_trigger ?? 1));
    setVal('h-p-flat', params.flat_start ? t('yes') : t('no'));
    setVal('h-p-tol', params.tol != null ? Number(params.tol).toExponential(1) : '—');
    setVal('h-p-diffstep', params.diff_step != null ? Number(params.diff_step).toExponential(1) : '—');
    setVal('h-p-maxiter', params.max_iterator != null ? String(params.max_iterator) : '—');
    setVal('h-p-badeps', params.baderr_eps != null ? String(params.baderr_eps) : '—');
    setVal('h-p-badmax', params.badnum_max != null ? String(params.badnum_max) : '—');
    setVal('h-p-badstep', params.badnum_step != null ? String(params.badnum_step) : '—');
    setVal('h-p-pweight', params.pseudo_measurement_weight != null ? Number(params.pseudo_measurement_weight).toExponential(1) : '—');
    setVal('h-p-pmax', params.targeted_pseudo_measurement_max != null ? String(params.targeted_pseudo_measurement_max) : '—');
    setVal('h-p-vfloor', params.voltage_floor != null ? String(params.voltage_floor) : '—');
    setVal('h-p-pftol', params.power_flow_tol != null ? Number(params.power_flow_tol).toExponential(1) : '—');
    setVal('h-p-pfiter', params.power_flow_max_iter != null ? String(params.power_flow_max_iter) : '—');

    // 右上：合格率摘要 + 双曲线
    document.getElementById('h-r-cur').textContent = ts.current_pass_rate != null ? `${ts.current_pass_rate.toFixed(2)}%` : '—';
    document.getElementById('h-r-today').textContent = ts.today_avg_pass_rate != null ? `${ts.today_avg_pass_rate.toFixed(2)}%` : '—';
    document.getElementById('h-r-yest').textContent = ts.yesterday_avg_pass_rate != null ? `${ts.yesterday_avg_pass_rate.toFixed(2)}%` : '—';
    document.getElementById('h-r-conv').textContent = `${Number(ts.today_conv_rate || 0).toFixed(1)}%`;
    renderPassChart(d.pass_rate_series);

    // 左下：计算结果
    setVal('h-res-start', latest ? fmtTime(latest.started_at || latest.calc_time) : '—');
    setVal('h-res-end', latest ? fmtTime(latest.finished_at || latest.calc_time) : '—');
    setVal('h-res-elapsed', latest ? `${Number(latest.elapsed_seconds || 0).toFixed(3)} s` : '—');
    setVal('h-res-iters', latest ? String(latest.iterations ?? 0) : '—');
    setVal('h-res-obj', latest ? fmtNum(latest.objective, 4) : '—');
    setVal('h-res-residual', latest ? `${fmtNum(latest.total_residual, 2)} / ${fmtNum(latest.residual_inf, 2)}` : '—');
    setVal('h-res-bad', latest ? String(latest.bad_data_count ?? 0) : '0', (latest?.bad_data_count || 0) > 0 ? 'bad' : 'ok');

    // 右下：指标统计
    setVal('h-st-host', rt.host || '—');
    setVal('h-st-runs', String(ts.today_runs ?? 0));
    setVal('h-st-conv-cnt', String(ts.today_converged ?? 0));
    setVal('h-st-conv-rate', `${Number(ts.today_conv_rate || 0).toFixed(1)}%`, 'ok');
    setVal('h-st-pass-rate', ts.current_pass_rate != null ? `${ts.current_pass_rate.toFixed(2)}%` : '—', 'ok');
    setVal('h-st-good-valid', `${obs.good_meas_count ?? 0} / ${obs.valid_meas_count ?? 0}`);
    const covPct = obs.meas_count > 0 ? ((obs.valid_meas_count / obs.meas_count) * 100).toFixed(1) + '%' : '—';
    setVal('h-st-coverage', covPct);

    // 底部运行信息条
    const log = d.latest_log;
    if (log) {
      document.getElementById('h-log-time').textContent = fmtTime(log.calc_time);
      document.getElementById('h-log-msg').textContent = `[${log.level}/${log.stage}] ${log.message}`;
    } else {
      document.getElementById('h-log-time').textContent = '—';
      document.getElementById('h-log-msg').textContent = '—';
    }
  }

  async function refreshAll() {
    try {
      const data = await api('/api/se/home');
      renderHome(data);
    } catch (err) {
      notify(err.message, true);
    }
  }

  function bindEvents() {
    document.getElementById('btn-home-start').addEventListener('click', async () => {
      const btn = document.getElementById('btn-home-start');
      btn.disabled = true;
      try {
        notify(t('msg.se_submitted'));
        await api('/api/actions/trigger', { method: 'POST', body: JSON.stringify({ task: 'se' }) });
        notify(t('msg.se_done'));
        await refreshAll();
      } catch (err) {
        notify(err.message, true);
      } finally {
        btn.disabled = false;
      }
    });

    document.getElementById('btn-home-toggle-daemon').addEventListener('click', async (e) => {
      const running = e.currentTarget.dataset.running === '1';
      try {
        await api(running ? '/api/actions/daemon/stop' : '/api/actions/daemon/start', { method: 'POST', body: '{}' });
        notify(running ? t('msg.daemon_off') : t('msg.daemon_on'));
        await refreshAll();
      } catch (err) {
        notify(err.message, true);
      }
    });

    let timer;
    window.addEventListener('resize', () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        if (homeData) renderPassChart(homeData.pass_rate_series);
      }, 150);
    });
  }

  /**
   * 绑定主画面 4 处可拖拽分割符（左/中列宽、右栏上下高度、右下两卡比例），支持双击复位与持久化。
   */
  function initHomeSplitters() {
    const grid = document.getElementById('se-home-grid');
    const right = document.getElementById('se-home-right');
    const bottom = document.getElementById('se-home-bottom');
    const sCol1 = document.getElementById('split-col1');
    const sCol2 = document.getElementById('split-col2');
    const sRightH = document.getElementById('split-right-h');
    const sBotV = document.getElementById('split-bottom-v');
    if (!grid || !right || !bottom) return;

    const LAYOUT_KEY = 'pas_se_home_layout';
    const DEFAULTS = { col1: 248, col2: 252, bottomH: null, botRatio: 0.5 };

    let layout = { ...DEFAULTS };
    try {
      const saved = JSON.parse(localStorage.getItem(LAYOUT_KEY) || '{}');
      if (saved && typeof saved === 'object') {
        if (Number.isFinite(saved.col1)) layout.col1 = Math.max(180, Math.min(460, Number(saved.col1)));
        if (Number.isFinite(saved.col2)) layout.col2 = Math.max(180, Math.min(460, Number(saved.col2)));
        if (Number.isFinite(saved.bottomH) && saved.bottomH >= 140) layout.bottomH = Number(saved.bottomH);
        if (Number.isFinite(saved.botRatio)) layout.botRatio = Math.max(0.28, Math.min(0.72, Number(saved.botRatio)));
      }
    } catch (_) {
      layout = { ...DEFAULTS };
    }

    let rafId = 0;
    const scheduleChartRedraw = () => {
      if (rafId) return;
      rafId = requestAnimationFrame(() => {
        rafId = 0;
        if (homeData) renderPassChart(homeData.pass_rate_series);
      });
    };

    const applyLayout = (redraw = false) => {
      grid.style.setProperty('--col1', `${Math.round(layout.col1)}px`);
      grid.style.setProperty('--col2', `${Math.round(layout.col2)}px`);
      right.style.setProperty('--bottom-h', layout.bottomH != null ? `${Math.round(layout.bottomH)}px` : 'auto');
      bottom.style.setProperty('--bot-left', `calc(${(layout.botRatio * 100).toFixed(2)}% - 4px)`);
      if (redraw) scheduleChartRedraw();
    };

    const saveLayout = () => {
      try {
        localStorage.setItem(LAYOUT_KEY, JSON.stringify(layout));
      } catch (_) {}
    };

    const bindDrag = (el, orientation, onMove, onReset) => {
      if (!el) return;
      let dragging = false;
      const bodyCls = orientation === 'v' ? 'se-splitting-v' : 'se-splitting-h';

      el.addEventListener('dblclick', () => {
        onReset();
        applyLayout(true);
        saveLayout();
      });

      el.addEventListener('pointerdown', (e) => {
        if (e.button !== 0) return;
        dragging = true;
        el.setPointerCapture(e.pointerId);
        el.classList.add('is-active');
        document.body.classList.add(bodyCls);
      });

      el.addEventListener('pointermove', (e) => {
        if (!dragging) return;
        onMove(e);
        applyLayout(true);
      });

      const end = (e) => {
        if (!dragging) return;
        dragging = false;
        if (e && el.hasPointerCapture?.(e.pointerId)) el.releasePointerCapture(e.pointerId);
        el.classList.remove('is-active');
        document.body.classList.remove(bodyCls);
        saveLayout();
        scheduleChartRedraw();
      };

      el.addEventListener('pointerup', end);
      el.addEventListener('pointercancel', end);
    };

    bindDrag(
      sCol1,
      'v',
      (e) => {
        const rect = grid.getBoundingClientRect();
        const maxCol1 = Math.max(180, Math.min(460, rect.width - layout.col2 - 340 - 16));
        layout.col1 = Math.max(180, Math.min(maxCol1, e.clientX - rect.left - 4));
      },
      () => { layout.col1 = DEFAULTS.col1; },
    );

    bindDrag(
      sCol2,
      'v',
      (e) => {
        const rect = grid.getBoundingClientRect();
        const maxCol2 = Math.max(180, Math.min(460, rect.width - layout.col1 - 340 - 16));
        layout.col2 = Math.max(180, Math.min(maxCol2, e.clientX - rect.left - layout.col1 - 12));
      },
      () => { layout.col2 = DEFAULTS.col2; },
    );

    bindDrag(
      sRightH,
      'h',
      (e) => {
        const rect = right.getBoundingClientRect();
        const maxBottom = Math.max(140, rect.height - 188);
        layout.bottomH = Math.max(140, Math.min(maxBottom, rect.bottom - e.clientY - 4));
      },
      () => { layout.bottomH = DEFAULTS.bottomH; },
    );

    bindDrag(
      sBotV,
      'v',
      (e) => {
        const rect = bottom.getBoundingClientRect();
        if (rect.width <= 0) return;
        const ratio = (e.clientX - rect.left) / rect.width;
        layout.botRatio = Math.max(0.28, Math.min(0.72, ratio));
      },
      () => { layout.botRatio = DEFAULTS.botRatio; },
    );

    applyLayout(false);
  }

  common.initShell({ onRefresh: refreshAll, afterRunSE: refreshAll });
  initHomeSplitters();
  bindEvents();
  refreshAll();
})();
