/* PAS 在线静态安全分析 (CA) 5 页统一前端引擎（三语 + 8 主题 + 接线图风险分布 + 故障集管理） */
(() => {
  'use strict';

  const THEMES = [
    'minimalist-light', 'precision-dark', 'bento-grid', 'glassmorphism',
    'editorial', 'sci-fi-cyan', 'sci-fi-purple', 'sci-fi-matrix',
  ];

  const I18N = {
    'zh-CN': {
      'brand.subtitle': '在线分析平台',
      'nav.overview': '总览', 'nav.analysis': '分析功能', 'nav.ops': '运行管理',
      'nav.se': '状态估计 SE', 'nav.lf': '潮流分析 LF', 'nav.ca': '静态安全 CA',
      'nav.ca_main': '主画面', 'nav.ca_risks': '风险与图谱', 'nav.ca_contingencies': '预想故障集',
      'nav.ca_config': '参数与限值', 'nav.ca_logs': '运行日志',
      'nav.runs': '运行历史', 'nav.measurements': '设备量测', 'nav.limits': '安全限值',
      'nav.workspace': '工作目录', 'nav.settings': '系统设置',
      'service.checking': '服务检查中', 'service.daemon': '周期调度运行中', 'service.online': 'Web 在线 · 周期停止', 'service.offline': '服务暂不可用',
      'theme.light': '极简明亮', 'theme.dark': '精密暗黑', 'theme.bento': '便当盒网格', 'theme.glass': '毛玻璃拟态',
      'theme.editorial': '编辑杂志', 'theme.cyan': '科幻 · 电光青', 'theme.purple': '科幻 · 赛博紫', 'theme.matrix': '科幻 · 矩阵绿',
      'title.ca_main': '静态安全 CA', 'title.ca_risks': '安全风险与故障图谱',
      'title.ca_contingencies': '预想故障集管理', 'title.ca_config': 'CA 参数与安全限值', 'title.ca_logs': 'CA 运行日志与调度',
      'action.run_ca': '立即执行 CA', 'action.scan_now': '立即扫描当前故障集', 'action.refresh': '刷新',
      'action.export_csv': '导出 CSV', 'action.more': '全部 →', 'action.cancel': '取消', 'action.confirm': '确认',
      'action.save': '保存', 'action.edit': '编辑', 'action.delete': '删除', 'action.enable': '启用', 'action.disable': '停用',
      'action.add_cont': '+ 新增故障', 'action.sync_n1': '从模型生成 N-1', 'action.enable_filtered': '全部启用',
      'action.disable_filtered': '全部停用', 'action.clear_conts': '清空故障集',
      'action.reset_default': '恢复默认', 'action.save_params': '保存参数', 'action.save_and_trial': '保存并试算对比',
      'action.seed_limits': '从模型播种限值', 'action.open_limits': '限值管理页 →',
      'action.save_sched': '保存调度', 'action.purge_now': '立即按策略清理', 'action.replay': '回放',
      'home.security_overview': '安全评估与基态', 'home.risk_dist': '风险分级分布', 'home.scan_extremes': '故障扫描与极值',
      'home.recent_runs': '近期 CA 运行', 'home.trend_title': '安全健康与风险趋势',
      'home.top_risks': '高危风险排行', 'home.top_contingencies': '严重预想故障 Top', 'home.view_source_lf': '查看源 LF',
      'metric.score': '安全评分', 'metric.total_risks': '风险总数', 'metric.max_loading': '最大负载 %',
      'tab.risks': '风险明细表', 'tab.cont_results': '故障扫描总览', 'tab.risk_map': '接线图风险分布',
      'tab.ca_params': '扫描与越限参数', 'tab.ca_limits': '设备安全限值',
      'tab.log_list': '日志明细', 'tab.run_sched': '运行与调度', 'tab.log_policy': '清理策略',
      'opt.all_cat': '全部场景', 'opt.all_sev': '全部等级', 'opt.all_rtype': '全部类型', 'opt.all_type': '全部设备类',
      'opt.all_level': '全部级别', 'opt.all_stage': '全部阶段', 'opt.all_time': '全部时间',
      'opt.enabled': '启用', 'opt.disabled': '停用', 'opt.none': '— 不选 —', 'opt.latest_run': '最新断面',
      'sev.critical': '严重', 'sev.high': '高', 'sev.medium': '中', 'sev.low': '低', 'sev.normal': '正常',
      'rtype.divergence': '潮流发散', 'rtype.load_loss': '负荷损失', 'rtype.overload': '设备过载',
      'rtype.heavy_load': '重载预警', 'rtype.voltage_low': '电压越下限', 'rtype.voltage_high': '电压越上限',
      'col.severity': '等级', 'col.category': '类别', 'col.contingency': '故障场景', 'col.risk_type': '风险类型',
      'col.device': '设备', 'col.dev_type': '设备类', 'col.actual': '实算值', 'col.limit': '限值',
      'col.violation': '越限幅', 'col.detail': '详情', 'col.targets': '开断元件', 'col.conv': '收敛',
      'col.load_loss': '失电负荷', 'col.max_loading': '最大负载 %', 'col.min_v': '最低电压', 'col.risk_cnt': '风险数',
      'col.elapsed_ms': '耗时 ms', 'col.priority': '优先级', 'col.source': '来源', 'col.status': '状态', 'col.actions': '操作',
      'col.source_lf': 'LF', 'col.risk_level': '等级', 'col.score': '评分', 'col.n1_risk': 'N-0/N-1',
      'col.metric': '指标', 'col.min_val': '下限', 'col.max_val': '上限', 'col.unit': '单位', 'col.note': '备注',
      'col.time': '时间', 'col.level': '级别', 'col.stage': '阶段', 'col.message': '消息',
      'topo.fit': '适应画布', 'topo.risk_devices': '高风险设备', 'topo.dev_risks': '设备风险详情', 'topo.locate': '定位风险设备...',
      'dlg.cont_title': '预想故障定义', 'dlg.dev1_type': '主故障元件类型', 'dlg.dev1_name': '主故障元件',
      'dlg.dev2_type': '第二元件类型（N-k 可选）', 'dlg.dev2_name': '第二元件（N-k 可选）',
      'sec.base_scan': '基态来源与预想故障扫描', 'sec.ca_thresholds': '越限与失电门槛',
      'param.use_lf_base': 'LF 基态注入', 'param.scan_n1': '启用 N-1 扫描', 'param.scan_nk': '启用 N-k 扫描',
      'param.max_scan': '单轮最大扫描数', 'param.v_min_pu': '电压下限 (pu)', 'param.v_max_pu': '电压上限 (pu)',
      'param.ol_warn': '重载预警 (%)', 'param.ol_limit': '过载越限 (%)', 'param.loss_thr': '失电告警门槛 (kW)', 'param.do_cycle': '计算周期参考 (s)',
      'logs.history_runs': 'CA 历史运行记录', 'logs.schedule_card': 'CA 周期调度',
      'sched.enabled': '周期自动执行', 'sched.period': '周期 (s)',
      'pol.enabled': '自动清理', 'pol.ret_days': '常规保留天数', 'pol.err_days': 'ERROR 保留天数', 'pol.max_rows': '最大保留条数',
      'ph.search_risk': '搜索设备/故障...', 'ph.search_cont': '搜索故障名/元件...', 'ph.search_limit': '搜索限值设备...', 'ph.search_log': '搜索日志消息...',
      'msg.empty': '—', 'msg.running_ca': '正在执行静态安全分析 CA…', 'msg.ca_done': '静态安全分析执行完成',
      'msg.saved': '已保存', 'msg.deleted': '已删除', 'msg.reset_done': '已恢复默认参数',
      'msg.synced': '模型 N-1 预想故障同步完成（新增 {n} 条）', 'msg.cleared': '已清空预想故障 {n} 条',
      'msg.purged': '已清理日志 {n} 条', 'msg.seeded': '设备安全限值播种完成',
      'msg.confirm_reset': '确认将所有 CA 扫描与越限参数恢复为默认值？',
      'msg.confirm_clear_conts': '确认清空全部预想故障定义？清空后可随时从模型重新生成。',
      'msg.confirm_del_cont': '确认删除预想故障「{name}」？',
      'msg.confirm_purge': '确认立即按当前策略清理过期或超限的 CA 日志？此操作不可撤销。',
    },
    'en-US': {
      'brand.subtitle': 'Online Analysis', 'nav.overview': 'Overview', 'nav.analysis': 'Analysis', 'nav.ops': 'Operations',
      'nav.se': 'State Estimation SE', 'nav.lf': 'Load Flow LF', 'nav.ca': 'Security CA',
      'nav.ca_main': 'Home', 'nav.ca_risks': 'Risks & Map', 'nav.ca_contingencies': 'Contingencies',
      'nav.ca_config': 'Params & Limits', 'nav.ca_logs': 'Logs',
      'nav.runs': 'Runs', 'nav.measurements': 'Measurements', 'nav.limits': 'Limits', 'nav.workspace': 'Workspace', 'nav.settings': 'Settings',
      'service.checking': 'Checking', 'service.daemon': 'Daemon Running', 'service.online': 'Web Online · Idle', 'service.offline': 'Offline',
      'theme.light': 'Minimal Light', 'theme.dark': 'Precision Dark', 'theme.bento': 'Bento Grid', 'theme.glass': 'Glassmorphism',
      'theme.editorial': 'Editorial', 'theme.cyan': 'Sci-Fi Cyan', 'theme.purple': 'Sci-Fi Purple', 'theme.matrix': 'Sci-Fi Matrix',
      'title.ca_main': 'Contingency Analysis CA', 'title.ca_risks': 'Risks & Security Map',
      'title.ca_contingencies': 'Contingency Catalog', 'title.ca_config': 'CA Params & Limits', 'title.ca_logs': 'CA Logs & Schedule',
      'action.run_ca': 'Run CA', 'action.scan_now': 'Scan Contingencies', 'action.refresh': 'Refresh',
      'action.export_csv': 'Export CSV', 'action.more': 'All →', 'action.cancel': 'Cancel', 'action.confirm': 'Confirm',
      'action.save': 'Save', 'action.edit': 'Edit', 'action.delete': 'Delete', 'action.enable': 'Enable', 'action.disable': 'Disable',
      'action.add_cont': '+ Add', 'action.sync_n1': 'Sync N-1', 'action.enable_filtered': 'Enable All',
      'action.disable_filtered': 'Disable All', 'action.clear_conts': 'Clear All',
      'action.reset_default': 'Reset Default', 'action.save_params': 'Save Params', 'action.save_and_trial': 'Save & Trial',
      'action.seed_limits': 'Seed Limits', 'action.open_limits': 'Limits Page →',
      'action.save_sched': 'Save Schedule', 'action.purge_now': 'Purge Now', 'action.replay': 'Replay',
      'home.security_overview': 'Security & Base', 'home.risk_dist': 'Risk Breakdown', 'home.scan_extremes': 'Scan & Extremes',
      'home.recent_runs': 'Recent CA Runs', 'home.trend_title': 'Security Score & Risk Trend',
      'home.top_risks': 'Top Risks', 'home.top_contingencies': 'Worst Contingencies', 'home.view_source_lf': 'Source LF',
      'metric.score': 'Score', 'metric.total_risks': 'Total Risks', 'metric.max_loading': 'Max Load %',
      'tab.risks': 'Risks', 'tab.cont_results': 'Scan Results', 'tab.risk_map': 'Topology Map',
      'tab.ca_params': 'Scan Params', 'tab.ca_limits': 'Device Limits',
      'tab.log_list': 'Logs', 'tab.run_sched': 'Runs & Schedule', 'tab.log_policy': 'Retention',
      'opt.all_cat': 'All Cases', 'opt.all_sev': 'All Levels', 'opt.all_rtype': 'All Types', 'opt.all_type': 'All Devices',
      'opt.all_level': 'All Levels', 'opt.all_stage': 'All Stages', 'opt.all_time': 'All Time',
      'opt.enabled': 'Enabled', 'opt.disabled': 'Disabled', 'opt.none': '— None —', 'opt.latest_run': 'Latest',
      'sev.critical': 'Critical', 'sev.high': 'High', 'sev.medium': 'Medium', 'sev.low': 'Low', 'sev.normal': 'Normal',
      'rtype.divergence': 'Divergence', 'rtype.load_loss': 'Load Loss', 'rtype.overload': 'Overload',
      'rtype.heavy_load': 'Heavy Load', 'rtype.voltage_low': 'Under-V', 'rtype.voltage_high': 'Over-V',
      'col.severity': 'Severity', 'col.category': 'Cat', 'col.contingency': 'Contingency', 'col.risk_type': 'Type',
      'col.device': 'Device', 'col.dev_type': 'Class', 'col.actual': 'Actual', 'col.limit': 'Limit',
      'col.violation': 'Excess', 'col.detail': 'Detail', 'col.targets': 'Outage', 'col.conv': 'Conv',
      'col.load_loss': 'Loss', 'col.max_loading': 'Max Load%', 'col.min_v': 'Min V', 'col.risk_cnt': 'Risks',
      'col.elapsed_ms': 'ms', 'col.priority': 'Prio', 'col.source': 'Source', 'col.status': 'Status', 'col.actions': 'Actions',
      'col.source_lf': 'LF', 'col.risk_level': 'Level', 'col.score': 'Score', 'col.n1_risk': 'N-0/N-1',
      'col.metric': 'Metric', 'col.min_val': 'Min', 'col.max_val': 'Max', 'col.unit': 'Unit', 'col.note': 'Note',
      'col.time': 'Time', 'col.level': 'Level', 'col.stage': 'Stage', 'col.message': 'Message',
      'topo.fit': 'Fit', 'topo.risk_devices': 'Risk Devices', 'topo.dev_risks': 'Device Risks', 'topo.locate': 'Locate risk...',
      'dlg.cont_title': 'Contingency Definition', 'dlg.dev1_type': 'Element 1 Type', 'dlg.dev1_name': 'Element 1',
      'dlg.dev2_type': 'Element 2 Type (N-k)', 'dlg.dev2_name': 'Element 2 (N-k)',
      'sec.base_scan': 'Base & Scan Control', 'sec.ca_thresholds': 'Thresholds',
      'param.use_lf_base': 'Use LF Base', 'param.scan_n1': 'Scan N-1', 'param.scan_nk': 'Scan N-k',
      'param.max_scan': 'Max Cases', 'param.v_min_pu': 'V min (pu)', 'param.v_max_pu': 'V max (pu)',
      'param.ol_warn': 'Warn Load (%)', 'param.ol_limit': 'Limit Load (%)', 'param.loss_thr': 'Loss Thr (kW)', 'param.do_cycle': 'Cycle (s)',
      'logs.history_runs': 'CA Run History', 'logs.schedule_card': 'CA Schedule',
      'sched.enabled': 'Auto Schedule', 'sched.period': 'Period (s)',
      'pol.enabled': 'Auto Purge', 'pol.ret_days': 'Retain Days', 'pol.err_days': 'Error Days', 'pol.max_rows': 'Max Rows',
      'ph.search_risk': 'Search risks...', 'ph.search_cont': 'Search cases...', 'ph.search_limit': 'Search limits...', 'ph.search_log': 'Search logs...',
      'msg.empty': '—', 'msg.running_ca': 'Running CA…', 'msg.ca_done': 'CA completed',
      'msg.saved': 'Saved', 'msg.deleted': 'Deleted', 'msg.reset_done': 'Defaults restored',
      'msg.synced': 'Synced N-1 contingencies (+{n})', 'msg.cleared': 'Cleared {n} contingencies',
      'msg.purged': 'Purged {n} logs', 'msg.seeded': 'Limits seeded from model',
      'msg.confirm_reset': 'Reset all CA parameters to defaults?',
      'msg.confirm_clear_conts': 'Clear all contingencies? You can re-sync from model anytime.',
      'msg.confirm_del_cont': 'Delete contingency "{name}"?',
      'msg.confirm_purge': 'Purge expired/overflow CA logs immediately? Cannot be undone.',
    },
    'ru-RU': {
      'brand.subtitle': 'Онлайн-анализ', 'nav.overview': 'Обзор', 'nav.analysis': 'Анализ', 'nav.ops': 'Управление',
      'nav.se': 'Оценка сост. SE', 'nav.lf': 'Потоки LF', 'nav.ca': 'Надежность CA',
      'nav.ca_main': 'Главная', 'nav.ca_risks': 'Риски и схема', 'nav.ca_contingencies': 'Возмущения',
      'nav.ca_config': 'Параметры', 'nav.ca_logs': 'Журнал',
      'nav.runs': 'Запуски', 'nav.measurements': 'Измерения', 'nav.limits': 'Пределы', 'nav.workspace': 'Каталог', 'nav.settings': 'Настройки',
      'service.checking': 'Проверка', 'service.daemon': 'Планировщик активен', 'service.online': 'Веб онлайн', 'service.offline': 'Нет связи',
      'theme.light': 'Светлая', 'theme.dark': 'Темная', 'theme.bento': 'Бенто', 'theme.glass': 'Стекло',
      'theme.editorial': 'Журнал', 'theme.cyan': 'Неон циан', 'theme.purple': 'Кибер фиол.', 'theme.matrix': 'Матрица',
      'title.ca_main': 'Статическая надежность CA', 'title.ca_risks': 'Риски и карта сети',
      'title.ca_contingencies': 'Список возмущений', 'title.ca_config': 'Параметры и пределы CA', 'title.ca_logs': 'Журнал и расписание CA',
      'action.run_ca': 'Запуск CA', 'action.scan_now': 'Сканировать', 'action.refresh': 'Обновить',
      'action.export_csv': 'Экспорт CSV', 'action.more': 'Все →', 'action.cancel': 'Отмена', 'action.confirm': 'Подтвердить',
      'action.save': 'Сохранить', 'action.edit': 'Изм.', 'action.delete': 'Удалить', 'action.enable': 'Вкл.', 'action.disable': 'Выкл.',
      'action.add_cont': '+ Добавить', 'action.sync_n1': 'Синхр. N-1', 'action.enable_filtered': 'Вкл. все',
      'action.disable_filtered': 'Выкл. все', 'action.clear_conts': 'Очистить',
      'action.reset_default': 'Сброс', 'action.save_params': 'Сохранить', 'action.save_and_trial': 'Сохр. и расчет',
      'action.seed_limits': 'Заполнить пределы', 'action.open_limits': 'Пределы →',
      'action.save_sched': 'Сохранить', 'action.purge_now': 'Очистить', 'action.replay': 'Обзор',
      'home.security_overview': 'Надежность и база', 'home.risk_dist': 'Уровни риска', 'home.scan_extremes': 'Сканирование',
      'home.recent_runs': 'Последние запуски CA', 'home.trend_title': 'Динамика надежности',
      'home.top_risks': 'Топ рисков', 'home.top_contingencies': 'Опасные возмущения', 'home.view_source_lf': 'База LF',
      'metric.score': 'Индекс', 'metric.total_risks': 'Риски', 'metric.max_loading': 'Загрузка %',
      'tab.risks': 'Список рисков', 'tab.cont_results': 'Итоги сканирования', 'tab.risk_map': 'Схема рисков',
      'tab.ca_params': 'Параметры CA', 'tab.ca_limits': 'Пределы',
      'tab.log_list': 'Журнал', 'tab.run_sched': 'Запуски и график', 'tab.log_policy': 'Очистка',
      'opt.all_cat': 'Все сценарии', 'opt.all_sev': 'Все уровни', 'opt.all_rtype': 'Все типы', 'opt.all_type': 'Все классы',
      'opt.all_level': 'Все уровни', 'opt.all_stage': 'Все этапы', 'opt.all_time': 'Весь период',
      'opt.enabled': 'Вкл.', 'opt.disabled': 'Выкл.', 'opt.none': '— Нет —', 'opt.latest_run': 'Последний',
      'sev.critical': 'Крит.', 'sev.high': 'Выс.', 'sev.medium': 'Сред.', 'sev.low': 'Низк.', 'sev.normal': 'Норма',
      'rtype.divergence': 'Расходимость', 'rtype.load_loss': 'Потеря нагр.', 'rtype.overload': 'Перегрузка',
      'rtype.heavy_load': 'Предупр.', 'rtype.voltage_low': 'Низк. U', 'rtype.voltage_high': 'Выс. U',
      'col.severity': 'Уровень', 'col.category': 'Кат.', 'col.contingency': 'Возмущение', 'col.risk_type': 'Тип',
      'col.device': 'Элемент', 'col.dev_type': 'Класс', 'col.actual': 'Факт', 'col.limit': 'Предел',
      'col.violation': 'Превыш.', 'col.detail': 'Детали', 'col.targets': 'Отключения', 'col.conv': 'Сход.',
      'col.load_loss': 'Потеря', 'col.max_loading': 'Макс %', 'col.min_v': 'Мин U', 'col.risk_cnt': 'Риски',
      'col.elapsed_ms': 'мс', 'col.priority': 'Приор.', 'col.source': 'Источник', 'col.status': 'Статус', 'col.actions': 'Действия',
      'col.source_lf': 'LF', 'col.risk_level': 'Уровень', 'col.score': 'Индекс', 'col.n1_risk': 'N-0/N-1',
      'col.metric': 'Параметр', 'col.min_val': 'Мин', 'col.max_val': 'Макс', 'col.unit': 'Ед.', 'col.note': 'Прим.',
      'col.time': 'Время', 'col.level': 'Уровень', 'col.stage': 'Этап', 'col.message': 'Сообщение',
      'topo.fit': 'Вписать', 'topo.risk_devices': 'Узлы риска', 'topo.dev_risks': 'Риски элемента', 'topo.locate': 'Найти...',
      'dlg.cont_title': 'Возмущение', 'dlg.dev1_type': 'Класс 1', 'dlg.dev1_name': 'Элемент 1',
      'dlg.dev2_type': 'Класс 2 (N-k)', 'dlg.dev2_name': 'Элемент 2 (N-k)',
      'sec.base_scan': 'База и сканирование', 'sec.ca_thresholds': 'Пороги',
      'param.use_lf_base': 'База LF', 'param.scan_n1': 'Скан N-1', 'param.scan_nk': 'Скан N-k',
      'param.max_scan': 'Макс. число', 'param.v_min_pu': 'U мин (о.е.)', 'param.v_max_pu': 'U макс (о.е.)',
      'param.ol_warn': 'Предупр. (%)', 'param.ol_limit': 'Предел (%)', 'param.loss_thr': 'Порог потерь', 'param.do_cycle': 'Цикл (с)',
      'logs.history_runs': 'История CA', 'logs.schedule_card': 'Расписание CA',
      'sched.enabled': 'Автозапуск', 'sched.period': 'Период (с)',
      'pol.enabled': 'Автоочистка', 'pol.ret_days': 'Хранить (дн.)', 'pol.err_days': 'ERROR (дн.)', 'pol.max_rows': 'Макс. строк',
      'ph.search_risk': 'Поиск...', 'ph.search_cont': 'Поиск...', 'ph.search_limit': 'Поиск...', 'ph.search_log': 'Поиск...',
      'msg.empty': '—', 'msg.running_ca': 'Выполнение CA…', 'msg.ca_done': 'Расчет CA завершен',
      'msg.saved': 'Сохранено', 'msg.deleted': 'Удалено', 'msg.reset_done': 'Сброшено',
      'msg.synced': 'Синхронизировано N-1 (+{n})', 'msg.cleared': 'Удалено возмущений: {n}',
      'msg.purged': 'Удалено записей: {n}', 'msg.seeded': 'Пределы обновлены',
      'msg.confirm_reset': 'Сбросить все параметры CA?',
      'msg.confirm_clear_conts': 'Очистить весь список возмущений?',
      'msg.confirm_del_cont': 'Удалить возмущение "{name}"?',
      'msg.confirm_purge': 'Очистить устаревшие записи журнала CA?',
    },
  };

  const st = {
    page: document.body.dataset.page || '/ca-main',
    lang: localStorage.getItem('pas_se_lang') || 'zh-CN',
    theme: localStorage.getItem('pas_se_theme') || 'minimalist-light',
    selectedRunId: new URLSearchParams(location.search).get('run_id') || '',
    trendMetric: 'security_score',
    homeData: null,
    riskTab: new URLSearchParams(location.search).get('tab') || 'risks',
    riskFilter: { cat: 'all', sev: 'all', rtype: 'all', q: '', page: 0, size: 40 },
    contFilter: { page: 0, size: 40 },
    cdefFilter: { cat: 'all', dtype: 'all', q: '' },
    cdefRows: [],
    catalog: null,
    cfgTab: 'params',
    logTab: 'list',
    logs: { level: 'all', stage: 'all', win: 'all', q: '', page: 0, size: 40 },
    svgLoaded: false,
    svgData: null,
    svgView: { scale: 1, x: 0, y: 0, vbW: 1200, vbH: 800, dragging: false, sx: 0, sy: 0 },
  };

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  const num = (v, d = 2) => (v == null || Number.isNaN(Number(v)) ? '—' : Number(v).toFixed(d));
  const fmtTime = (s) => (s ? String(s).replace('T', ' ').slice(0, 19) : '—');
  const t = (key, vars) => {
    const dict = I18N[st.lang] || I18N['zh-CN'];
    let out = dict[key] ?? I18N['zh-CN'][key] ?? key;
    if (vars) for (const [k, v] of Object.entries(vars)) out = out.replaceAll(`{${k}}`, String(v));
    return out;
  };

  async function api(url, body = null, method = null) {
    const m = method || (body != null ? 'POST' : 'GET');
    const opts = { method: m, headers: {} };
    if (body != null && m !== 'GET' && m !== 'DELETE') {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const resp = await fetch(url, opts);
    const data = await resp.json();
    if (!resp.ok || data.ok === false) throw new Error(data.error || `HTTP ${resp.status}`);
    return data.data;
  }

  let noticeTimer = null;
  function notify(msg, isErr = false) {
    const el = $('#notice');
    if (!el) return;
    el.textContent = msg;
    el.className = `notice ${isErr ? 'error' : 'ok'}`;
    el.hidden = false;
    clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => { el.hidden = true; }, isErr ? 6000 : 3200);
  }

  function applyTheme(theme) {
    const valid = THEMES.includes(theme) ? theme : 'minimalist-light';
    st.theme = valid;
    document.documentElement.dataset.theme = valid;
    localStorage.setItem('pas_se_theme', valid);
    const sel = $('#theme-select');
    if (sel) sel.value = valid;
  }

  function applyLang(lang) {
    st.lang = I18N[lang] ? lang : 'zh-CN';
    document.documentElement.lang = st.lang;
    localStorage.setItem('pas_se_lang', st.lang);
    const sel = $('#lang-select');
    if (sel) sel.value = st.lang;
    $$('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
    $$('[data-i18n-placeholder]').forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  }

  function confirmAction(title, msg) {
    const dlg = $('#confirm-dialog');
    if (!dlg) return Promise.resolve(window.confirm(msg));
    $('#confirm-title').textContent = title;
    $('#confirm-msg').textContent = msg;
    return new Promise((resolve) => {
      const okBtn = $('#confirm-ok');
      const cancelBtn = $('#confirm-cancel');
      const cleanup = (val) => {
        okBtn.onclick = null;
        cancelBtn.onclick = null;
        dlg.oncancel = null;
        if (dlg.open) dlg.close();
        resolve(val);
      };
      okBtn.onclick = () => cleanup(true);
      cancelBtn.onclick = () => cleanup(false);
      dlg.oncancel = () => cleanup(false);
      dlg.showModal();
      cancelBtn.focus();
    });
  }

  function sevClass(sev) {
    if (sev === 'critical' || sev === '严重') return 'bad';
    if (sev === 'high' || sev === '高') return 'bad';
    if (sev === 'medium' || sev === '中') return 'warn';
    if (sev === 'low' || sev === '低') return 'neutral';
    return 'ok';
  }

  function sevLabel(sev) {
    const map = { critical: t('sev.critical'), high: t('sev.high'), medium: t('sev.medium'), low: t('sev.low'), normal: t('sev.normal') };
    return map[sev] || sev || '—';
  }

  function rtypeLabel(rt) {
    const map = {
      divergence: t('rtype.divergence'), load_loss: t('rtype.load_loss'), overload: t('rtype.overload'),
      heavy_load: t('rtype.heavy_load'), voltage_low: t('rtype.voltage_low'), voltage_high: t('rtype.voltage_high'),
    };
    return map[rt] || rt || '—';
  }

  async function refreshServiceStatus() {
    try {
      const s = await api('/api/status');
      const dot = $('#service-dot');
      const txt = $('#service-state');
      if (dot) dot.className = `status-dot ${s.daemon_running ? 'ok' : ''}`;
      if (txt) txt.textContent = s.daemon_running ? t('service.daemon') : t('service.online');
    } catch {
      const txt = $('#service-state');
      if (txt) txt.textContent = t('service.offline');
    }
  }

  async function runCaNow() {
    const btn = $('#btn-run-ca');
    if (btn) btn.disabled = true;
    notify(t('msg.running_ca'));
    try {
      await api('/api/actions/trigger', { task: 'ca' });
      notify(t('msg.ca_done'));
      await refreshCurrentPage();
    } catch (err) {
      notify(err.message, true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  // -------------------- 主画面 /ca-main --------------------
  function renderTrendSvg(series, metric) {
    const box = $('#ca-home-trend');
    if (!box) return;
    if (!series || !series.length) {
      box.innerHTML = `<div class="se-empty">${t('msg.empty')}</div>`;
      return;
    }
    const vals = series.map((p) => {
      if (metric === 'total_risks') return (p.n0_risk_count || 0) + (p.n1_risk_count || 0) + (p.nk_risk_count || 0);
      return Number(p[metric] ?? 0);
    });
    const w = 720, h = 196, padL = 42, padR = 14, padT = 14, padB = 24;
    const minV = metric === 'security_score' ? 0 : Math.min(0, ...vals);
    const maxV = metric === 'security_score' ? 100 : Math.max(1, ...vals) * 1.1;
    const span = Math.max(1e-6, maxV - minV);
    const xAt = (i) => padL + (series.length === 1 ? (w - padL - padR) / 2 : (i / (series.length - 1)) * (w - padL - padR));
    const yAt = (v) => padT + (1 - (v - minV) / span) * (h - padT - padB);
    const pts = vals.map((v, i) => `${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`).join(' ');
    const area = `${padL},${h - padB} ${pts} ${xAt(vals.length - 1).toFixed(1)},${h - padB}`;
    const ticks = [0, 0.5, 1].map((r) => {
      const y = padT + r * (h - padT - padB);
      const val = maxV - r * span;
      return `<line x1="${padL}" y1="${y.toFixed(1)}" x2="${w - padR}" y2="${y.toFixed(1)}" stroke="var(--line)" stroke-dasharray="3 3"/>` +
        `<text x="${padL - 6}" y="${(y + 4).toFixed(1)}" text-anchor="end" font-size="10" fill="var(--muted)">${val.toFixed(metric === 'total_risks' ? 0 : 1)}</text>`;
    }).join('');
    const dots = vals.map((v, i) => `<circle cx="${xAt(i).toFixed(1)}" cy="${yAt(v).toFixed(1)}" r="3" fill="var(--accent)"><title>#${series[i].run_id} (${fmtTime(series[i].calc_time)}): ${v.toFixed(1)}</title></circle>`).join('');
    box.innerHTML = `<svg viewBox="0 0 ${w} ${h}" style="width:100%;height:196px;display:block">${ticks}<polygon points="${area}" fill="var(--accent)" opacity="0.12"/><polyline points="${pts}" fill="none" stroke="var(--accent)" stroke-width="2"/>${dots}<text x="${padL}" y="${h - 6}" font-size="10" fill="var(--muted)">#${series[0].run_id}</text><text x="${w - padR}" y="${h - 6}" text-anchor="end" font-size="10" fill="var(--muted)">#${series[series.length - 1].run_id}</text></svg>`;
  }

  async function loadMainView() {
    const data = await api('/api/ca/home');
    st.homeData = data;
    const lat = data.latest;
    const pill = $('#ca-level-pill');
    const meta = $('#ca-run-meta');
    if (pill) {
      pill.textContent = lat ? `${lat.risk_level} · ${num(lat.security_score, 1)} 分` : '—';
      pill.className = `se-pill ${lat ? sevClass(lat.risk_level) : 'neutral'}`;
    }
    if (meta) {
      meta.textContent = lat ? `CA #${lat.run_id} · LF #${lat.source_lf_run_id ?? '—'} · SE #${lat.source_se_run_id ?? '—'} · ${fmtTime(lat.calc_time)}` : '—';
    }
    if ($('#ca-home-score')) {
      $('#ca-home-score').textContent = lat ? `${num(lat.security_score, 1)} / 100` : '—';
      $('#ca-home-score').className = `se-pill tabular ${lat ? sevClass(lat.risk_level) : 'neutral'}`;
    }
    if ($('#ca-src-lf-link') && lat?.source_lf_run_id) {
      $('#ca-src-lf-link').href = `/lf-results.html?run_id=${lat.source_lf_run_id}`;
    }
    const defs = data.contingency_defs || { total: 0, enabled: 0, n1: 0, nk: 0 };
    if ($('#ca-kv-overview')) {
      $('#ca-kv-overview').innerHTML = [
        ['总体定级', lat ? lat.risk_level : '—'],
        ['源 LF 断面', lat?.source_lf_run_id ? `LF #${lat.source_lf_run_id}` : '—'],
        ['溯源 SE 断面', lat?.source_se_run_id ? `SE #${lat.source_se_run_id}` : '—'],
        ['N-0 基态风险', lat ? String(lat.n0_risk_count) : '—'],
        ['N-1 扫描 / 风险', lat ? `${lat.n1_total_count} / ${lat.n1_risk_count}` : '—'],
        ['N-k 扫描 / 风险', lat ? `${lat.nk_total_count} / ${lat.nk_risk_count}` : '—'],
        ['启用故障定义', `${defs.enabled} / ${defs.total}`],
      ].map(([k, v]) => `<div class="se-kv-row"><span>${esc(k)}</span><strong class="tabular">${esc(v)}</strong></div>`).join('');
    }
    const totRisks = lat ? (lat.critical_count + lat.high_count + lat.medium_count + lat.low_count) : 0;
    if ($('#ca-home-total-risks')) $('#ca-home-total-risks').textContent = String(totRisks);
    if ($('#ca-kv-severity')) {
      $('#ca-kv-severity').innerHTML = [
        [t('sev.critical'), lat ? lat.critical_count : 0, 'bad'],
        [t('sev.high'), lat ? lat.high_count : 0, 'bad'],
        [t('sev.medium'), lat ? lat.medium_count : 0, 'warn'],
        [t('sev.low'), lat ? lat.low_count : 0, 'neutral'],
      ].map(([k, v, cls]) => `<div class="se-kv-row"><span>${esc(k)}</span><span class="se-pill ${v > 0 ? cls : 'ok'} tabular">${v}</span></div>`).join('');
    }
    if ($('#ca-home-elapsed')) $('#ca-home-elapsed').textContent = lat ? `${num(lat.elapsed_seconds, 2)} s` : '—';
    if ($('#ca-kv-extremes')) {
      $('#ca-kv-extremes').innerHTML = [
        ['最严重预想故障', lat?.worst_contingency || '—'],
        ['N-1 收敛 / 发散', lat ? `${lat.n1_converged_count} / ${lat.n1_diverged_count}` : '—'],
        ['最大支路负载率', lat ? `${num(lat.max_loading_pct, 2)}% ${lat.max_loading_dev ? `(${lat.max_loading_dev})` : ''}` : '—'],
        ['最低母线电压', lat?.min_v_pu != null ? `${num(lat.min_v_pu, 4)} pu (${lat.min_v_bus || ''})` : '—'],
        ['最高母线电压', lat?.max_v_pu != null ? `${num(lat.max_v_pu, 4)} pu (${lat.max_v_bus || ''})` : '—'],
        ['最大失电负荷', lat ? `${num(lat.max_load_loss_kw, 2)} ${lat.p_unit || 'kW'}` : '—'],
      ].map(([k, v]) => `<div class="se-kv-row"><span>${esc(k)}</span><strong class="tabular">${esc(v)}</strong></div>`).join('');
    }
    if ($('#ca-home-runs')) {
      const runs = (data.recent_runs || []).slice(0, 8);
      $('#ca-home-runs').innerHTML = runs.length ? runs.map((r) => `<tr>
        <td class="tabular"><a class="se-link" href="/ca-risks.html?run_id=${r.run_id}">#${r.run_id}</a></td>
        <td class="tabular">${r.source_lf_run_id ? `#${r.source_lf_run_id}` : '—'}</td>
        <td><span class="se-pill ${sevClass(r.risk_level)}">${esc(r.risk_level || r.status)}</span></td>
        <td class="tabular">${r.security_score != null ? num(r.security_score, 1) : '—'}</td>
      </tr>`).join('') : `<tr><td colspan="4" class="se-empty">${t('msg.empty')}</td></tr>`;
    }
    renderTrendSvg(data.trend_series || [], st.trendMetric);
    if ($('#ca-home-top-risks')) {
      const tr = data.top_risks || [];
      $('#ca-home-top-risks').innerHTML = tr.length ? tr.map((r) => `<tr>
        <td><span class="se-pill ${sevClass(r.severity)}">${esc(sevLabel(r.severity))}</span></td>
        <td title="${esc(r.contingency_name)}">${esc(r.contingency_name)}</td>
        <td title="${esc(r.detail)}">${esc(r.device_name)}</td>
        <td class="tabular">${num(r.violation_pct, 1)}%</td>
      </tr>`).join('') : `<tr><td colspan="4" class="se-empty">${t('msg.empty')}</td></tr>`;
    }
    if ($('#ca-home-top-conts')) {
      const tc = data.top_contingencies || [];
      $('#ca-home-top-conts').innerHTML = tc.length ? tc.map((c) => `<tr>
        <td title="${esc(c.target_desc)}">${esc(c.contingency_name)}</td>
        <td><span class="se-pill ${c.converged ? 'ok' : 'bad'}">${c.converged ? 'OK' : 'FAIL'}</span></td>
        <td class="tabular">${num(c.load_loss_kw, 1)}</td>
        <td class="tabular"><span class="se-pill ${sevClass(c.severity)}">${c.risk_count}</span></td>
      </tr>`).join('') : `<tr><td colspan="4" class="se-empty">${t('msg.empty')}</td></tr>`;
    }
  }

  // -------------------- 风险与图谱 /ca-risks --------------------
  async function loadRunSelect() {
    const sel = $('#ca-run-select');
    if (!sel) return;
    const runs = await api('/api/ca/runs/history?limit=30').catch(() => []);
    sel.innerHTML = `<option value="">${esc(t('opt.latest_run'))}</option>` + runs.map((r) =>
      `<option value="${r.run_id}" ${String(r.run_id) === String(st.selectedRunId) ? 'selected' : ''}>#${r.run_id} · ${esc(r.risk_level)} (${num(r.security_score, 1)}) · ${fmtTime(r.calc_time)}</option>`
    ).join('');
  }

  function switchRiskTab(tab) {
    st.riskTab = tab;
    $$('[data-risk-tab]').forEach((b) => b.classList.toggle('active', b.dataset.riskTab === tab));
    $('#pane-ca-risks').hidden = tab !== 'risks';
    $('#pane-ca-conts').hidden = tab !== 'contingencies';
    $('#pane-ca-topo').hidden = tab !== 'topology';
    $('#ca-risk-filters').hidden = tab === 'topology';
    if (tab === 'risks') loadRisksTable();
    else if (tab === 'contingencies') loadContResultsTable();
    else loadTopoRisks();
  }

  function renderPager(el, total, page, size, onPage) {
    if (!el) return;
    const pages = Math.max(1, Math.ceil(total / size));
    el.innerHTML = `<span>${page + 1} / ${pages} (${total})</span><div style="display:flex;gap:6px"><button type="button" class="se-btn mini" data-p="${page - 1}" ${page <= 0 ? 'disabled' : ''}>‹</button><button type="button" class="se-btn mini" data-p="${page + 1}" ${page >= pages - 1 ? 'disabled' : ''}>›</button></div>`;
    el.querySelectorAll('button[data-p]').forEach((b) => b.addEventListener('click', () => onPage(Number(b.dataset.p))));
  }

  async function loadRisksTable() {
    const f = st.riskFilter;
    const qs = new URLSearchParams({
      category: f.cat, severity: f.sev, risk_category: f.rtype, q: f.q,
      limit: String(f.size), offset: String(f.page * f.size),
    });
    if (st.selectedRunId) qs.set('run_id', st.selectedRunId);
    const data = await api(`/api/ca/risks?${qs}`);
    const lat = data.latest;
    if ($('#ca-level-pill')) {
      $('#ca-level-pill').textContent = lat ? `${lat.risk_level} · ${num(lat.security_score, 1)}` : '—';
      $('#ca-level-pill').className = `se-pill ${lat ? sevClass(lat.risk_level) : 'neutral'}`;
    }
    const rows = data.rows || [];
    $('#ca-risks-tbody').innerHTML = rows.length ? rows.map((r) => `<tr>
      <td><span class="se-pill ${sevClass(r.severity)}">${esc(sevLabel(r.severity))}</span></td>
      <td><span class="se-tag">${esc(r.category)}</span></td>
      <td>${esc(r.contingency_name)}</td>
      <td>${esc(rtypeLabel(r.risk_category))}</td>
      <td>${esc(r.device_name)} <small style="color:var(--muted)">${esc(r.device_type)}</small></td>
      <td class="tabular">${r.actual_value != null ? `${num(r.actual_value, 2)} ${esc(r.unit)}` : '—'}</td>
      <td class="tabular">${r.limit_value != null ? `${num(r.limit_value, 2)} ${esc(r.unit)}` : '—'}</td>
      <td class="tabular">${num(r.violation_pct, 2)}%</td>
      <td>${esc(r.detail)}</td>
    </tr>`).join('') : `<tr><td colspan="9" class="se-empty">${t('msg.empty')}</td></tr>`;
    renderPager($('#ca-risks-pager'), data.meta?.total || 0, f.page, f.size, (p) => { f.page = p; loadRisksTable(); });
  }

  async function loadContResultsTable() {
    const f = st.riskFilter;
    const cf = st.contFilter;
    const qs = new URLSearchParams({
      category: f.cat, severity: f.sev, q: f.q,
      limit: String(cf.size), offset: String(cf.page * cf.size),
    });
    if (st.selectedRunId) qs.set('run_id', st.selectedRunId);
    const data = await api(`/api/ca/contingencies/results?${qs}`);
    const rows = data.rows || [];
    $('#ca-conts-tbody').innerHTML = rows.length ? rows.map((c) => `<tr>
      <td><span class="se-pill ${sevClass(c.severity)}">${esc(sevLabel(c.severity))}</span></td>
      <td><span class="se-tag">${esc(c.category)}</span></td>
      <td>${esc(c.contingency_name)}</td>
      <td title="${esc(c.target_desc)}">${esc(c.target_desc)}</td>
      <td><span class="se-pill ${c.converged ? 'ok' : 'bad'}">${c.converged ? 'OK' : 'FAIL'}</span></td>
      <td class="tabular">${num(c.load_loss_kw, 2)}</td>
      <td class="tabular">${num(c.max_loading_pct, 2)}% ${c.max_loading_dev ? `<small style="color:var(--muted)">${esc(c.max_loading_dev)}</small>` : ''}</td>
      <td class="tabular">${c.min_v_pu != null ? `${num(c.min_v_pu, 4)} pu` : '—'}</td>
      <td class="tabular">${c.risk_count}</td>
      <td class="tabular">${num(c.elapsed_ms, 1)}</td>
    </tr>`).join('') : `<tr><td colspan="10" class="se-empty">${t('msg.empty')}</td></tr>`;
    renderPager($('#ca-conts-pager'), data.meta?.total || 0, cf.page, cf.size, (p) => { cf.page = p; loadContResultsTable(); });
  }

  function updateSvgTransform() {
    const canvas = $('#ca-svg-canvas');
    if (!canvas) return;
    const v = st.svgView;
    canvas.style.transform = `translate(${v.x}px, ${v.y}px) scale(${v.scale})`;
    const lbl = $('#svg-zoom-label');
    if (lbl) lbl.textContent = `${Math.round(v.scale * 100)}%`;
  }

  function fitSvg() {
    const vp = $('#ca-svg-viewport');
    const v = st.svgView;
    if (!vp || !v.vbW || !v.vbH) return;
    const pad = 12;
    const r = vp.getBoundingClientRect();
    if (r.width < 10 || r.height < 10) return;
    const s = Math.min((r.width - pad * 2) / v.vbW, (r.height - pad * 2) / v.vbH);
    v.scale = Math.max(0.1, Math.min(4, s));
    v.x = (r.width - v.vbW * v.scale) / 2;
    v.y = (r.height - v.vbH * v.scale) / 2;
    updateSvgTransform();
  }

  function focusRiskDevice(devId) {
    const dev = st.svgData?.devices?.[devId];
    if (!dev) return;
    $('#ca-insp-title').textContent = dev.device_name || devId;
    $('#ca-insp-sev').textContent = sevLabel(dev.severity);
    $('#ca-insp-sev').className = `se-pill ${sevClass(dev.severity)}`;
    $('#ca-insp-body').innerHTML = (dev.risks || []).map((r) => `
      <div class="se-kv-row" style="flex-direction:column;align-items:flex-start;gap:2px;padding:6px 0;border-bottom:1px solid var(--line)">
        <div style="display:flex;gap:6px;align-items:center;width:100%">
          <span class="se-pill ${sevClass(r.severity)}">${esc(sevLabel(r.severity))}</span>
          <span class="se-tag">${esc(r.category)}</span>
          <strong style="font-size:12px">${esc(r.contingency_name)}</strong>
        </div>
        <div style="font-size:12px;color:var(--muted)">${esc(r.detail)}</div>
      </div>
    `).join('') || `<div class="se-empty">${t('msg.empty')}</div>`;
  }

  async function loadTopoRisks() {
    const qs = st.selectedRunId ? `?run_id=${encodeURIComponent(st.selectedRunId)}` : '';
    const data = await api(`/api/ca/topology-risks${qs}`);
    st.svgData = data;
    const riskIds = data.risk_dev_ids || [];
    if ($('#ca-topo-risk-count')) {
      $('#ca-topo-risk-count').textContent = String(riskIds.length);
      $('#ca-topo-risk-count').className = `se-pill tabular ${riskIds.length ? 'bad' : 'ok'}`;
    }
    const list = $('#ca-topo-risk-list');
    if (list) {
      list.innerHTML = riskIds.length ? riskIds.map((id) => {
        const d = data.devices[id];
        return `<button type="button" class="se-bad-item" data-dev="${esc(id)}">
          <div class="se-bad-item-top"><strong>${esc(d.device_name || id)}</strong><span class="se-pill ${sevClass(d.severity)}">${esc(sevLabel(d.severity))}</span></div>
          <div class="se-bad-item-sub">${esc(d.device_type)} · ${d.risk_count} 项风险</div>
        </button>`;
      }).join('') : `<div class="se-empty">${t('msg.empty')}</div>`;
      list.querySelectorAll('[data-dev]').forEach((b) => b.addEventListener('click', () => focusRiskDevice(b.dataset.dev)));
    }
    const jump = $('#ca-device-jump');
    if (jump) {
      jump.innerHTML = `<option value="">${esc(t('topo.locate'))}</option>` + riskIds.map((id) => `<option value="${esc(id)}">${esc(data.devices[id].device_name || id)}</option>`).join('');
    }
    if (!st.svgLoaded && data.svg_available) {
      const resp = await fetch('/api/se/svg');
      if (resp.ok) {
        const svgText = await resp.text();
        const canvas = $('#ca-svg-canvas');
        canvas.innerHTML = svgText;
        const svgEl = canvas.querySelector('svg');
        if (svgEl) {
          const vb = (svgEl.getAttribute('viewBox') || '0 0 1200 800').split(/[\s,]+/).map(Number);
          st.svgView.vbW = vb[2] || 1200;
          st.svgView.vbH = vb[3] || 800;
          svgEl.style.width = `${st.svgView.vbW}px`;
          svgEl.style.height = `${st.svgView.vbH}px`;
          svgEl.style.display = 'block';
        }
        st.svgLoaded = true;
      }
    }
    // 给风险设备附加高亮边框并支持点击选中
    const canvas = $('#ca-svg-canvas');
    if (canvas) {
      canvas.querySelectorAll('.ca-risk-hl').forEach((el) => el.classList.remove('ca-risk-hl'));
      for (const id of riskIds) {
        const el = canvas.querySelector(`[id="${CSS.escape(id)}"], [dev-id="${CSS.escape(id)}"]`);
        if (el) {
          el.classList.add('ca-risk-hl');
          el.style.cursor = 'pointer';
          el.style.outline = '3px solid #ef4444';
          el.onclick = () => focusRiskDevice(id);
        }
      }
    }
    requestAnimationFrame(() => fitSvg());
    if (riskIds.length) focusRiskDevice(riskIds[0]);
  }

  // -------------------- 预想故障集 /ca-contingencies --------------------
  async function loadCatalog() {
    if (!st.catalog) st.catalog = await api('/api/ca/model-catalog');
    return st.catalog;
  }

  function fillDeviceSelect(dtSel, dnSel, allowEmpty = false) {
    const cat = st.catalog || { devices_by_type: {}, contingency_types: [] };
    const types = cat.contingency_types || [];
    dtSel.innerHTML = (allowEmpty ? `<option value="">${esc(t('opt.none'))}</option>` : '') +
      types.map((x) => `<option value="${esc(x.type)}">${esc(x.type)} (${esc(x.label)})</option>`).join('');
    const refreshNames = () => {
      const dt = dtSel.value;
      const list = (cat.devices_by_type || {})[dt] || [];
      dnSel.innerHTML = !dt
        ? `<option value="">${esc(t('opt.none'))}</option>`
        : list.map((d) => `<option value="${esc(d.idx)}" data-name="${esc(d.name)}">${esc(d.name)} (#${d.idx})</option>`).join('');
    };
    dtSel.onchange = refreshNames;
    refreshNames();
  }

  async function loadContingenciesView() {
    const f = st.cdefFilter;
    const qs = new URLSearchParams({ category: f.cat === 'all' ? '' : f.cat, device_type: f.dtype === 'all' ? '' : f.dtype, q: f.q });
    const rows = await api(`/api/ca/contingencies/defs?${qs}`);
    st.cdefRows = rows || [];
    const enabledCnt = st.cdefRows.filter((r) => r.enabled).length;
    if ($('#ca-def-stat-pill')) $('#ca-def-stat-pill').textContent = `${enabledCnt} / ${st.cdefRows.length}`;
    $('#cdef-tbody').innerHTML = st.cdefRows.length ? st.cdefRows.map((r) => `<tr>
      <td class="tabular">${r.priority}</td>
      <td><span class="se-tag">${esc(r.category)}</span></td>
      <td><strong>${esc(r.name)}</strong></td>
      <td>${esc(r.target_desc)}</td>
      <td><span class="se-tag">${r.auto_generated ? 'AUTO' : 'CUSTOM'}</span></td>
      <td><span class="se-pill ${r.enabled ? 'ok' : 'neutral'}">${r.enabled ? t('opt.enabled') : t('opt.disabled')}</span></td>
      <td style="white-space:nowrap;display:flex;gap:4px">
        <button type="button" class="se-btn mini" data-cdef-toggle="${r.id}">${r.enabled ? t('action.disable') : t('action.enable')}</button>
        <button type="button" class="se-btn mini" data-cdef-edit="${r.id}">${t('action.edit')}</button>
        <button type="button" class="se-btn mini danger" data-cdef-del="${r.id}">${t('action.delete')}</button>
      </td>
    </tr>`).join('') : `<tr><td colspan="7" class="se-empty">${t('msg.empty')}</td></tr>`;
  }

  async function openContingencyDialog(row = null) {
    await loadCatalog();
    fillDeviceSelect($('#cf-dt1'), $('#cf-dn1'), false);
    fillDeviceSelect($('#cf-dt2'), $('#cf-dn2'), true);
    $('#cf-id').value = row ? row.id : '';
    $('#cf-name').value = row ? row.name : '';
    $('#cf-prio').value = row ? row.priority : 20;
    $('#cf-enabled').value = row ? String(row.enabled ? 1 : 0) : '1';
    $('#cf-note').value = row ? (row.note || '') : '';
    if (row && Array.isArray(row.items) && row.items.length) {
      $('#cf-dt1').value = row.items[0].device_type;
      $('#cf-dt1').onchange();
      if (row.items[0].device_idx != null) $('#cf-dn1').value = String(row.items[0].device_idx);
      if (row.items.length > 1) {
        $('#cf-dt2').value = row.items[1].device_type;
        $('#cf-dt2').onchange();
        if (row.items[1].device_idx != null) $('#cf-dn2').value = String(row.items[1].device_idx);
      }
    }
    $('#cdef-dialog').showModal();
  }

  // -------------------- 参数与限值 /ca-config --------------------
  async function loadConfigView() {
    const p = await api('/api/ca/params');
    if ($('#ca-param-updated')) $('#ca-param-updated').textContent = fmtTime(p.updated_at);
    $('#cp-use-lf').value = String(p.use_lf_base ?? 1);
    $('#cp-scan-n1').value = String(p.scan_n1 ?? 1);
    $('#cp-scan-nk').value = String(p.scan_nk ?? 1);
    $('#cp-max-scan').value = p.max_scan_count ?? 40;
    $('#cp-vmin').value = p.v_min_pu ?? 0.93;
    $('#cp-vmax').value = p.v_max_pu ?? 1.07;
    $('#cp-ol-warn').value = p.overload_warn_pct ?? 80;
    $('#cp-ol-limit').value = p.overload_limit_pct ?? 100;
    $('#cp-loss-thr').value = p.load_loss_threshold_kw ?? 0.5;
    $('#cp-cycle').value = p.do_cycle ?? 300;
    if (st.cfgTab === 'limits') await loadLimitsTable();
  }

  function readParamsPayload() {
    return {
      use_lf_base: Number($('#cp-use-lf').value),
      scan_n1: Number($('#cp-scan-n1').value),
      scan_nk: Number($('#cp-scan-nk').value),
      max_scan_count: Number($('#cp-max-scan').value),
      v_min_pu: Number($('#cp-vmin').value),
      v_max_pu: Number($('#cp-vmax').value),
      overload_warn_pct: Number($('#cp-ol-warn').value),
      overload_limit_pct: Number($('#cp-ol-limit').value),
      load_loss_threshold_kw: Number($('#cp-loss-thr').value),
      do_cycle: Number($('#cp-cycle').value),
    };
  }

  async function loadLimitsTable() {
    const q = ($('#clim-q')?.value || '').trim();
    const res = await api(`/api/inputs/limits?size=100&q=${encodeURIComponent(q)}`);
    const rows = res.rows || [];
    $('#clim-tbody').innerHTML = rows.length ? rows.map((r) => `<tr>
      <td>${esc(r.model_table || r.device_type)}</td>
      <td>${esc(r.device_name)}</td>
      <td><code>${esc(r.field || r.metric)}</code></td>
      <td class="tabular">${(r.lower_value ?? r.min_value) != null ? num(r.lower_value ?? r.min_value, 2) : '—'}</td>
      <td class="tabular">${(r.upper_value ?? r.max_value) != null ? num(r.upper_value ?? r.max_value, 2) : '—'}</td>
      <td>${esc(r.unit || '')}</td>
      <td><span class="se-pill ${r.enabled ? 'ok' : 'neutral'}">${r.enabled ? t('opt.enabled') : t('opt.disabled')}</span></td>
    </tr>`).join('') : `<tr><td colspan="7" class="se-empty">${t('msg.empty')}</td></tr>`;
  }

  // -------------------- 日志与调度 /ca-logs --------------------
  function switchLogTab(tab) {
    st.logTab = tab;
    $$('[data-log-tab]').forEach((b) => b.classList.toggle('active', b.dataset.logTab === tab));
    $('#pane-ca-log-list').hidden = tab !== 'list';
    $('#pane-ca-log-runs').hidden = tab !== 'runs';
    $('#pane-ca-log-policy').hidden = tab !== 'policy';
    $('#ca-log-filters').hidden = tab !== 'list';
  }

  async function loadLogsView() {
    const lg = st.logs;
    const qs = new URLSearchParams({
      level: lg.level, stage: lg.stage, window: lg.win, q: lg.q,
      limit: String(lg.size), offset: String(lg.page * lg.size),
    });
    const [sum, page, home] = await Promise.all([
      api('/api/ca/logs/summary'),
      api(`/api/ca/logs?${qs}`),
      api('/api/ca/home'),
    ]);
    if ($('#ca-log-total-pill')) $('#ca-log-total-pill').textContent = `${sum.total} 条 · 24h ERR ${sum.error_24h}`;
    const rows = page.rows || [];
    $('#clog-tbody').innerHTML = rows.length ? rows.map((r) => `<tr>
      <td class="tabular">${fmtTime(r.calc_time)}</td>
      <td><span class="se-pill ${r.level === 'ERROR' ? 'bad' : r.level === 'WARN' ? 'warn' : 'ok'}">${esc(r.level)}</span></td>
      <td><span class="se-tag">${esc(r.stage)}</span></td>
      <td class="tabular">${r.run_id ? `#${r.run_id}` : '—'}</td>
      <td>${esc(r.source)}</td>
      <td class="tabular">${r.elapsed_ms != null ? num(r.elapsed_ms, 1) : '—'}</td>
      <td>${esc(r.message)}</td>
    </tr>`).join('') : `<tr><td colspan="7" class="se-empty">${t('msg.empty')}</td></tr>`;
    renderPager($('#clog-pager'), page.total || 0, lg.page, lg.size, (p) => { lg.page = p; loadLogsView(); });

    const runs = home.recent_runs || [];
    $('#crun-tbody').innerHTML = runs.length ? runs.map((r) => `<tr>
      <td class="tabular">#${r.run_id}</td>
      <td class="tabular">${fmtTime(r.started_at)}</td>
      <td class="tabular">${r.source_lf_run_id ? `#${r.source_lf_run_id}` : '—'}</td>
      <td><span class="se-pill ${sevClass(r.risk_level)}">${esc(r.risk_level || r.status)}</span></td>
      <td class="tabular">${r.security_score != null ? num(r.security_score, 1) : '—'}</td>
      <td class="tabular">${r.n0_risk_count ?? '—'}/${r.n1_risk_count ?? '—'}</td>
      <td><a class="se-btn mini" href="/ca-risks.html?run_id=${r.run_id}">${esc(t('action.replay'))}</a></td>
    </tr>`).join('') : `<tr><td colspan="7" class="se-empty">${t('msg.empty')}</td></tr>`;

    if (home.schedule) {
      $('#csched-enabled').value = home.schedule.enabled ? '1' : '0';
      $('#csched-period').value = home.schedule.period_seconds ?? 300;
    }
    const pol = sum.policy || {};
    $('#cpol-enabled').value = String(pol.enabled ?? 1);
    $('#cpol-ret').value = pol.retention_days ?? 30;
    $('#cpol-err').value = pol.keep_error_days ?? 90;
    $('#cpol-max').value = pol.max_rows ?? 50000;
  }

  async function refreshCurrentPage() {
    await refreshServiceStatus();
    if (st.page === '/ca-main') return loadMainView();
    if (st.page === '/ca-risks') {
      await loadRunSelect();
      return switchRiskTab(st.riskTab);
    }
    if (st.page === '/ca-contingencies') return loadContingenciesView();
    if (st.page === '/ca-config') return loadConfigView();
    if (st.page === '/ca-logs') return loadLogsView();
  }

  function bindCommon() {
    $('#theme-select')?.addEventListener('change', (e) => applyTheme(e.target.value));
    $('#lang-select')?.addEventListener('change', (e) => { applyLang(e.target.value); refreshCurrentPage(); });
    $('#btn-refresh')?.addEventListener('click', () => refreshCurrentPage());
    $('#btn-run-ca')?.addEventListener('click', () => runCaNow());

    if (st.page === '/ca-main') {
      $$('[data-trend-metric]').forEach((b) => b.addEventListener('click', () => {
        st.trendMetric = b.dataset.trendMetric;
        $$('[data-trend-metric]').forEach((x) => x.classList.toggle('active', x === b));
        renderTrendSvg(st.homeData?.trend_series || [], st.trendMetric);
      }));
    }

    if (st.page === '/ca-risks') {
      $$('[data-risk-tab]').forEach((b) => b.addEventListener('click', () => switchRiskTab(b.dataset.riskTab)));
      $('#ca-run-select')?.addEventListener('change', (e) => { st.selectedRunId = e.target.value; switchRiskTab(st.riskTab); });
      $('#ca-f-cat')?.addEventListener('change', (e) => { st.riskFilter.cat = e.target.value; st.riskFilter.page = 0; st.contFilter.page = 0; switchRiskTab(st.riskTab); });
      $('#ca-f-sev')?.addEventListener('change', (e) => { st.riskFilter.sev = e.target.value; st.riskFilter.page = 0; st.contFilter.page = 0; switchRiskTab(st.riskTab); });
      $('#ca-f-rtype')?.addEventListener('change', (e) => { st.riskFilter.rtype = e.target.value; st.riskFilter.page = 0; switchRiskTab(st.riskTab); });
      let qTimer = null;
      $('#ca-f-q')?.addEventListener('input', (e) => {
        clearTimeout(qTimer);
        qTimer = setTimeout(() => { st.riskFilter.q = e.target.value; st.riskFilter.page = 0; st.contFilter.page = 0; switchRiskTab(st.riskTab); }, 250);
      });
      $('#btn-export-risks')?.addEventListener('click', () => {
        const f = st.riskFilter;
        const qs = new URLSearchParams({ category: f.cat, severity: f.sev, risk_category: f.rtype, q: f.q });
        if (st.selectedRunId) qs.set('run_id', st.selectedRunId);
        location.href = `/api/ca/risks/export?${qs}`;
      });
      $('#btn-svg-zoom-in')?.addEventListener('click', () => { st.svgView.scale = Math.min(4, st.svgView.scale * 1.2); updateSvgTransform(); });
      $('#btn-svg-zoom-out')?.addEventListener('click', () => { st.svgView.scale = Math.max(0.1, st.svgView.scale / 1.2); updateSvgTransform(); });
      $('#btn-svg-fit')?.addEventListener('click', () => fitSvg());
      $('#ca-device-jump')?.addEventListener('change', (e) => { if (e.target.value) focusRiskDevice(e.target.value); });
      const vp = $('#ca-svg-viewport');
      if (vp) {
        vp.addEventListener('wheel', (e) => {
          e.preventDefault();
          const factor = e.deltaY < 0 ? 1.12 : 0.89;
          st.svgView.scale = Math.max(0.1, Math.min(4, st.svgView.scale * factor));
          updateSvgTransform();
        }, { passive: false });
        vp.addEventListener('mousedown', (e) => { st.svgView.dragging = true; st.svgView.sx = e.clientX - st.svgView.x; st.svgView.sy = e.clientY - st.svgView.y; });
        window.addEventListener('mousemove', (e) => { if (!st.svgView.dragging) return; st.svgView.x = e.clientX - st.svgView.sx; st.svgView.y = e.clientY - st.svgView.sy; updateSvgTransform(); });
        window.addEventListener('mouseup', () => { st.svgView.dragging = false; });
      }
    }

    if (st.page === '/ca-contingencies') {
      $('#cdef-cat')?.addEventListener('change', (e) => { st.cdefFilter.cat = e.target.value; loadContingenciesView(); });
      $('#cdef-dtype')?.addEventListener('change', (e) => { st.cdefFilter.dtype = e.target.value; loadContingenciesView(); });
      let qt = null;
      $('#cdef-q')?.addEventListener('input', (e) => { clearTimeout(qt); qt = setTimeout(() => { st.cdefFilter.q = e.target.value; loadContingenciesView(); }, 250); });
      $('#btn-cdef-add')?.addEventListener('click', () => openContingencyDialog(null));
      $('#cf-cancel')?.addEventListener('click', () => $('#cdef-dialog').close());
      $('#cdef-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const dn1Opt = $('#cf-dn1').selectedOptions[0];
        const items = [{ device_type: $('#cf-dt1').value, device_idx: Number($('#cf-dn1').value), device_name: dn1Opt?.dataset?.name || dn1Opt?.textContent || '' }];
        if ($('#cf-dt2').value && $('#cf-dn2').value) {
          const dn2Opt = $('#cf-dn2').selectedOptions[0];
          items.push({ device_type: $('#cf-dt2').value, device_idx: Number($('#cf-dn2').value), device_name: dn2Opt?.dataset?.name || dn2Opt?.textContent || '' });
        }
        const payload = {
          name: $('#cf-name').value.trim(),
          priority: Number($('#cf-prio').value),
          enabled: Number($('#cf-enabled').value),
          note: $('#cf-note').value.trim(),
          items,
        };
        const cid = $('#cf-id').value;
        try {
          if (cid) await api(`/api/ca/contingencies/defs/${cid}`, payload, 'PUT');
          else await api('/api/ca/contingencies/defs', payload, 'POST');
          $('#cdef-dialog').close();
          notify(t('msg.saved'));
          await loadContingenciesView();
        } catch (err) { notify(err.message, true); }
      });
      $('#btn-cdef-sync')?.addEventListener('click', async () => {
        try {
          const r = await api('/api/ca/contingencies/sync', {});
          notify(t('msg.synced', { n: r.inserted }));
          await loadContingenciesView();
        } catch (err) { notify(err.message, true); }
      });
      $('#btn-cdef-enable-all')?.addEventListener('click', async () => {
        try {
          await api('/api/ca/contingencies/bulk-toggle', { enabled: true, category: st.cdefFilter.cat === 'all' ? '' : st.cdefFilter.cat, device_type: st.cdefFilter.dtype === 'all' ? '' : st.cdefFilter.dtype });
          notify(t('msg.saved'));
          await loadContingenciesView();
        } catch (err) { notify(err.message, true); }
      });
      $('#btn-cdef-disable-all')?.addEventListener('click', async () => {
        try {
          await api('/api/ca/contingencies/bulk-toggle', { enabled: false, category: st.cdefFilter.cat === 'all' ? '' : st.cdefFilter.cat, device_type: st.cdefFilter.dtype === 'all' ? '' : st.cdefFilter.dtype });
          notify(t('msg.saved'));
          await loadContingenciesView();
        } catch (err) { notify(err.message, true); }
      });
      $('#btn-cdef-clear')?.addEventListener('click', async () => {
        if (!(await confirmAction(t('action.clear_conts'), t('msg.confirm_clear_conts')))) return;
        try {
          const r = await api('/api/ca/contingencies/clear', {});
          notify(t('msg.cleared', { n: r.deleted }));
          await loadContingenciesView();
        } catch (err) { notify(err.message, true); }
      });
      $('#cdef-tbody')?.addEventListener('click', async (e) => {
        const tg = e.target.closest('[data-cdef-toggle]');
        if (tg) {
          const row = st.cdefRows.find((x) => String(x.id) === tg.dataset.cdefToggle);
          if (!row) return;
          try { await api(`/api/ca/contingencies/defs/${row.id}`, { ...row, enabled: row.enabled ? 0 : 1 }, 'PUT'); notify(t('msg.saved')); await loadContingenciesView(); } catch (err) { notify(err.message, true); }
          return;
        }
        const ed = e.target.closest('[data-cdef-edit]');
        if (ed) {
          const row = st.cdefRows.find((x) => String(x.id) === ed.dataset.cdefEdit);
          if (row) openContingencyDialog(row);
          return;
        }
        const dl = e.target.closest('[data-cdef-del]');
        if (dl) {
          const row = st.cdefRows.find((x) => String(x.id) === dl.dataset.cdefDel);
          if (!row) return;
          if (!(await confirmAction(t('action.delete'), t('msg.confirm_del_cont', { name: row.name })))) return;
          try { await api(`/api/ca/contingencies/defs/${row.id}`, null, 'DELETE'); notify(t('msg.deleted')); await loadContingenciesView(); } catch (err) { notify(err.message, true); }
        }
      });
    }

    if (st.page === '/ca-config') {
      $$('[data-cfg-tab]').forEach((b) => b.addEventListener('click', () => {
        st.cfgTab = b.dataset.cfgTab;
        $$('[data-cfg-tab]').forEach((x) => x.classList.toggle('active', x === b));
        $('#pane-ca-params').hidden = st.cfgTab !== 'params';
        $('#pane-ca-limits').hidden = st.cfgTab !== 'limits';
        $('#ca-limit-tools').hidden = st.cfgTab !== 'limits';
        if (st.cfgTab === 'limits') loadLimitsTable();
      }));
      $('#btn-param-save')?.addEventListener('click', async () => {
        try { await api('/api/ca/params', readParamsPayload()); notify(t('msg.saved')); await loadConfigView(); } catch (err) { notify(err.message, true); }
      });
      $('#btn-param-save-run')?.addEventListener('click', async () => {
        try {
          const before = (await api('/api/ca/home'))?.latest;
          await api('/api/ca/params', readParamsPayload());
          notify(t('msg.running_ca'));
          await api('/api/actions/trigger', { task: 'ca' });
          const after = (await api('/api/ca/home'))?.latest;
          const banner = $('#ca-trial-diff');
          if (banner && after) {
            banner.innerHTML = `<strong>试算对比：</strong> 评分 ${before ? num(before.security_score, 1) : '—'} → <strong>${num(after.security_score, 1)}</strong> · 等级 ${before?.risk_level || '—'} → <strong>${esc(after.risk_level)}</strong> · N-0 风险 ${before?.n0_risk_count ?? '—'} → <strong>${after.n0_risk_count}</strong> · N-1 风险 ${before?.n1_risk_count ?? '—'} → <strong>${after.n1_risk_count}</strong>`;
            banner.hidden = false;
          }
          notify(t('msg.ca_done'));
          await loadConfigView();
        } catch (err) { notify(err.message, true); }
      });
      $('#btn-param-reset')?.addEventListener('click', async () => {
        if (!(await confirmAction(t('action.reset_default'), t('msg.confirm_reset')))) return;
        try { await api('/api/ca/params/reset', {}); notify(t('msg.reset_done')); await loadConfigView(); } catch (err) { notify(err.message, true); }
      });
      $('#btn-seed-limits')?.addEventListener('click', async () => {
        try { await api('/api/inputs/seed-limits', {}); notify(t('msg.seeded')); await loadLimitsTable(); } catch (err) { notify(err.message, true); }
      });
      let lt = null;
      $('#clim-q')?.addEventListener('input', () => { clearTimeout(lt); lt = setTimeout(loadLimitsTable, 250); });
    }

    if (st.page === '/ca-logs') {
      $$('[data-log-tab]').forEach((b) => b.addEventListener('click', () => switchLogTab(b.dataset.logTab)));
      $('#clog-level')?.addEventListener('change', (e) => { st.logs.level = e.target.value; st.logs.page = 0; loadLogsView(); });
      $('#clog-stage')?.addEventListener('change', (e) => { st.logs.stage = e.target.value; st.logs.page = 0; loadLogsView(); });
      $('#clog-win')?.addEventListener('change', (e) => { st.logs.win = e.target.value; st.logs.page = 0; loadLogsView(); });
      let lqt = null;
      $('#clog-q')?.addEventListener('input', (e) => { clearTimeout(lqt); lqt = setTimeout(() => { st.logs.q = e.target.value; st.logs.page = 0; loadLogsView(); }, 250); });
      $('#btn-log-export')?.addEventListener('click', () => {
        const lg = st.logs;
        const qs = new URLSearchParams({ level: lg.level, stage: lg.stage, window: lg.win, q: lg.q });
        location.href = `/api/ca/logs/export?${qs}`;
      });
      $('#ca-sched-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          await api('/api/schedules/ca', { enabled: $('#csched-enabled').value === '1', period_seconds: Number($('#csched-period').value) });
          notify(t('msg.saved'));
          await loadLogsView();
        } catch (err) { notify(err.message, true); }
      });
      $('#ca-policy-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          await api('/api/ca/logs/policy', {
            enabled: Number($('#cpol-enabled').value),
            retention_days: Number($('#cpol-ret').value),
            keep_error_days: Number($('#cpol-err').value),
            max_rows: Number($('#cpol-max').value),
          });
          notify(t('msg.saved'));
          await loadLogsView();
        } catch (err) { notify(err.message, true); }
      });
      $('#btn-clog-purge')?.addEventListener('click', async () => {
        if (!(await confirmAction(t('action.purge_now'), t('msg.confirm_purge')))) return;
        try {
          const r = await api('/api/ca/logs/purge', { dry_run: false });
          notify(t('msg.purged', { n: r.deleted }));
          await loadLogsView();
        } catch (err) { notify(err.message, true); }
      });
    }
  }

  applyTheme(st.theme);
  applyLang(st.lang);
  bindCommon();
  refreshCurrentPage().catch((err) => notify(err.message, true));
  if (st.page === '/ca-main') setInterval(() => { if (!document.hidden) loadMainView().catch(() => {}); }, 10000);
})();
