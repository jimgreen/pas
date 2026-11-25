(() => {
  'use strict';

  const SVG_NS = 'http://www.w3.org/2000/svg';

  /** 多语言字典：默认支持简体中文 (zh-CN)、英文 (en-US)、俄文 (ru-RU) */
  const I18N_DICT = {
    'zh-CN': {
      'brand.sub': '在线分析平台',
      'nav.overview': '总览',
      'nav.analysis': '分析功能',
      'nav.se_root': '状态估计 SE',
      'nav.se_main': '主画面',
      'nav.se_flow': '潮流图',
      'nav.se_curves': '历史曲线',
      'nav.se_devices': '设备对比',
      'nav.se_measurements': '全量测分析',
      'nav.se_params': '算法参数',
      'nav.se_prefilter': '预过滤量测',
      'nav.se_pseudo': '伪量测',
      'nav.se_bad': '坏量测',
      'nav.se_logs': '运行日志',
      'title.flow': '潮流图',
      'title.curves': '历史曲线',
      'title.devices': '设备对比',
      'title.measurements': '全量测分析',
      'title.params': 'SE 算法参数',
      'link.manage_bad': '处置 →',
      'link.manage_bad_full': '坏量测 →',
      'link.manage_pseudo': '伪量测 →',
      'link.view_logs': '运行日志 →',
      'link.run_log': '日志',
      'nav.lf': '潮流分析 LF',
      'nav.ca': '静态安全 CA',
      'nav.management': '运行管理',
      'nav.runs': '运行历史',
      'nav.measurements': '设备量测',
      'nav.limits': '安全限值',
      'nav.workspace': '工作目录',
      'nav.settings': '系统设置',
      'service.checking': '服务检查中',
      'service.daemon_on': '周期调度运行中',
      'service.daemon_off': 'Web 在线 · 周期停止',
      'service.offline': '服务暂不可用',
      'title.main': '状态估计主画面',
      'action.run_se': '立即执行 SE',
      'action.running_se': 'SE 执行中...',
      'action.refresh': '刷新',
      'action.export_csv': '导出 CSV',
      'action.cancel': '取消',
      'action.confirm_reset': '确认恢复',
      'action.locate': '定位',
      'action.curve': '曲线',
      'action.prefilter': '+预过滤',
      'action.suppress': '屏蔽',
      'action.pseudo': '伪量测',
      'action.weight': '权重',
      'action.force_close': '强制合位',
      'action.force_open': '强制分位',
      'action.edit': '编辑',
      'action.delete': '删除',
      'meas.high_res': '仅大残差',
      'meas.tab_list': '全量测明细',
      'meas.tab_devices': '设备对比',
      'meas.tab_balance': '母线平衡与可观测',
      'dev.mode_compare': 'Meas / SE',
      'dev.mode_delta': '残差 Δ',
      'topo.imb_overlay': '不平衡母线',
      'topo.imb_panel': '不平衡',
      'bal.only_imb': '仅不平衡',
      'ph.search_bus': '搜索母线',
      'bal.bus': '母线',
      'bal.domain': '域',
      'bal.v_meas_se': '电压 (Meas/SE)',
      'bal.p_in': '注入 P',
      'bal.p_out': '汇出 P',
      'bal.dp_meas': '实测 ΔP',
      'bal.dp_se': '估计 ΔP',
      'bal.dq_meas': '实测 ΔQ',
      'bal.meas_cnt': '量测数',
      'bal.status': '状态',
      'bal.st_imb': '不平衡',
      'bal.st_lowobs': '低可观测',
      'bal.st_ok': '平衡',
      'bal.summary': '母线 {total} · 不平衡 {imb} · 低可观测 {low} · 最大 |ΔP| {max}',
      'batch.suppress': '批量屏蔽',
      'batch.prefilter': '批量预过滤',
      'batch.clear': '清空',
      'batch.done': '批量保存 {n} 项成功',
      'qa.target': '目标量测',
      'qa.min_val': '下限 min',
      'qa.max_val': '上限 max',
      'qa.pseudo_val': '伪量测值',
      'qa.weight': '权重',
      'qa.note': '备注 / 原因',
      'qa.submit': '保存并生效',
      'qa.title_suppress': '就地屏蔽坏量测',
      'qa.title_prefilter': '就地新增预过滤规则',
      'qa.title_pseudo': '就地设为伪量测',
      'qa.title_weight': '就地设置量测权重',
      'qa.saved': '处置已生效',
      'snap.latest': '最新断面',
      'snap.history': '历史回放',
      'params.trial': '保存并试算对比',
      'params.trial_running': '保存参数并执行试算…',
      'params.tab_para': '算法参数',
      'params.tab_weights': '量测权重',
      'ph.search_wt': '搜索权重规则',
      'wt.add': '+ 新增权重',
      'wt.dlg_title': '量测权重规则',
      'wt.scope': '作用范围',
      'wt.scope_type': '按设备类',
      'wt.scope_dev': '按单设备',
      'wt.dev_type': '设备类型',
      'wt.dev_name': '目标设备',
      'wt.metric': '指标',
      'wt.status': '状态',
      'wt.saved': '权重规则已保存',
      'wt.deleted': '权重规则已删除',
      'wt.del_confirm': '确认删除该量测权重规则？',
      'trial.title': '试算对比',
      'trial.iters': '迭代',
      'trial.pass': '合格率',
      'trial.bad': '坏数据',
      'trial.obj': '目标 J(x)',
      'trial.elapsed': '耗时',
      'empty.no_match': '无匹配记录',
      'bool.off': '关闭',
      'bool.on': '开启',
      'topo.zoom_in': '放大',
      'topo.zoom_out': '缩小',
      'ui.sidebar_resize': '拖动调整宽度 / 双击隐藏或展开',
      'ui.sidebar_hide': '隐藏左侧目录树',
      'ui.sidebar_show': '展开左侧目录树',
      'theme.light': '极简明亮',
      'theme.dark': '精密暗黑',
      'theme.bento': '便当盒网格',
      'theme.glass': '毛玻璃拟态',
      'theme.editorial': '编辑杂志',
      'theme.cyan': '科幻 · 电光青',
      'theme.purple': '科幻 · 赛博紫',
      'theme.matrix': '科幻 · 矩阵绿',
      'kpi.status': '收敛与可观测',
      'kpi.pass_rate': '状态估计合格率',
      'kpi.bad_data': '坏数据点',
      'kpi.residual': '总残差 / 最大残差',
      'kpi.elapsed': '计算用时',
      'unit.count': '条',
      'status.converged': '收敛',
      'status.diverged': '未收敛',
      'status.observable': '可观测',
      'status.unobservable': '不可观测',
      'status.no_bad': '无坏数据告警',
      'status.bad_alert': '{n} 处坏数据告警',
      'status.closed': '合位',
      'status.open': '分位',
      'status.succeeded': '成功',
      'status.failed': '失败',
      'status.running': '运行中',
      'tab.topology': '潮流图可视化',
      'tab.curves': '历史曲线',
      'tab.devices': '设备对比',
      'tab.measurements': '全量测分析',
      'tab.params': '算法参数',
      'tab.runs': '运行与调度',
      'topo.mode': '显示模式',
      'topo.mode_compare': 'Meas / SE',
      'topo.mode_se': 'SE',
      'topo.mode_meas': 'Meas',
      'topo.mode_residual': 'Δ (Meas-SE)',
      'topo.jump_placeholder': '定位设备…',
      'topo.fit': '适应画布',
      'topo.bad_panel': '坏数据',
      'topo.dev_detail': '设备对比',
      'topo.no_bad_empty': '—',
      'topo.select_hint': '—',
      'topo.svg_missing': '未找到 SVG',
      'legend.meas': '实测 Meas',
      'legend.se': '估计 SE',
      'legend.bad': '坏数据告警',
      'curves.global_title': '系统状态估计历史曲线',
      'curves.pass_rate': '合格率 (%)',
      'curves.residual': '总残差 / 最大残差',
      'curves.bad_data': '坏数据数',
      'curves.elapsed': '计算耗时 (s)',
      'curves.window': '样本窗口',
      'curves.point_title': '量测点与残差历史曲线',
      'curves.meas_vs_se': 'Meas vs SE',
      'curves.point_residual': '残差 Δ',
      'curves.norm_residual': '标准化残差',
      'curves.bad_hotspot_placeholder': '历史坏数据热点...',
      'curves.no_data': '暂无足够的历史计算记录',
      'curves.threshold': '坏数据门槛 ±{v}',
      'curves.total_res': '总残差',
      'curves.max_res': '最大残差',
      'curves.elapsed_total': '总耗时 (s)',
      'curves.elapsed_kernel': '内核耗时 (s)',
      'devices.bad_only': '仅坏数据设备',
      'devices.summary': '共 {n} 台设备',
      'ph.search_device': '筛选设备编号或名称',
      'ph.search_meas': '搜索设备/量测',
      'meas.all': '全部',
      'meas.bad': '坏数据',
      'meas.normal': '正常',
      'meas.prefiltered': '预过滤',
      'meas.pseudo': '伪量测',
      'sort.abs_res': '残差绝对值',
      'sort.abs_norm': '标准化残差',
      'sort.id': '量测序号',
      'sort.dev': '设备名称',
      'col.idx': '编号',
      'col.device': '设备',
      'col.metric': '指标',
      'col.meas': '实测 Meas',
      'col.se': '估计 SE',
      'col.residual': '残差 Δ',
      'col.norm_res': '标准化残差',
      'col.source': '类别',
      'col.actions': '操作',
      'col.run': '运行',
      'col.time': '计算时刻',
      'col.status': '状态',
      'col.pass_rate': '合格率',
      'col.bad_count': '坏数据',
      'col.elapsed': '用时 (s)',
      'params.title': 'SE 算法参数 (pas_se_para)',
      'params.reset': '恢复默认',
      'params.save': '保存参数',
      'params.saved': 'SE 算法参数已保存并生效',
      'params.reset_done': '已从 se.para 恢复默认算法参数',
      'params.group_core': '核心求解与坏数据检测',
      'params.group_pseudo': '伪量测与可观测性',
      'params.group_pf': '初值潮流与运行控制',
      'runs.title': 'SE 历史运行记录',
      'runs.open_legacy': '打开明细与 dbdef 页 →',
      'sched.title': 'SE 周期调度',
      'sched.period': '周期 (s)',
      'sched.enabled': '启用周期自动执行',
      'sched.save': '保存调度',
      'sched.daemon_start': '启动周期',
      'sched.daemon_stop': '停止周期',
      'sched.saved': 'SE 周期调度已保存',
      'modal.reset_title': '重置 pas_se_para',
      'modal.reset_desc': '恢复 se.para 默认值？',
      'pager.prev': '上一页',
      'pager.next': '下一页',
      'pager.info': '{page} / {pages} 页 · {total} 条',
      'notice.se_submitted': 'SE 任务已提交后台执行',
      'notice.se_done': 'SE 计算完成 (#{id})',
      'notice.se_failed': 'SE 计算失败：{msg}',
      'devtype.ACNode': '交流节点 ACNode',
      'devtype.DCNode': '直流节点 DCNode',
      'devtype.ACBranch': '交流线路 ACBranch',
      'devtype.DCBranch': '直流线路 DCBranch',
      'devtype.ACZeroBranch': '交流零阻抗 ACZeroBranch',
      'devtype.ACGenerator': '交流电源 ACGenerator',
      'devtype.DCGenerator': '直流电源 DCGenerator',
      'devtype.ACLoad': '交流负荷 ACLoad',
      'devtype.DCLoad': '直流负荷 DCLoad',
      'devtype.DCDCConverter': 'DC/DC 换流器',
      'devtype.DCACConverter': 'DC/AC 变流器',
      'devtype.ACBreak': '交流断路器 ACBreak',
      'devtype.DCBreak': '直流断路器 DCBreak',
      'devtype.ACRealBs': '交流实母线 ACRealBs',
      'devtype.DCRealBs': '直流实母线 DCRealBs',
      'devtype.ACPowerBalance': '交流功率平衡 ACPowerBalance',
      'devtype.all': '全部设备类',
    },
    'en-US': {
      'brand.sub': 'Online Power Analysis',
      'nav.overview': 'Overview',
      'nav.analysis': 'Analysis',
      'nav.se_main': 'Home',
      'nav.se': 'SE Details',
      'nav.lf': 'Load Flow LF',
      'nav.ca': 'Contingency CA',
      'nav.se_root': 'State Estimation SE',
      'nav.se_flow': 'Power Flow Map',
      'nav.se_curves': 'History Curves',
      'nav.se_devices': 'Device Compare',
      'nav.se_measurements': 'All Measurements',
      'nav.se_params': 'SE Parameters',
      'nav.se_prefilter': 'Prefilter Meas',
      'nav.se_pseudo': 'Pseudo Meas',
      'nav.se_bad': 'Bad Data',
      'nav.se_logs': 'Run Logs',
      'title.flow': 'Power Flow Map',
      'title.curves': 'History Curves',
      'title.devices': 'Device Comparison',
      'title.measurements': 'All Measurements',
      'title.params': 'SE Parameters',
      'link.manage_bad': 'Handle →',
      'link.manage_bad_full': 'Bad Data →',
      'link.manage_pseudo': 'Pseudo Meas →',
      'link.view_logs': 'Run Logs →',
      'link.run_log': 'Logs',
      'nav.management': 'Operations',
      'nav.runs': 'Run History',
      'nav.measurements': 'Measurements',
      'nav.limits': 'Security Limits',
      'nav.workspace': 'Workspace',
      'nav.settings': 'Settings',
      'service.checking': 'Checking service',
      'service.daemon_on': 'Scheduler Running',
      'service.daemon_off': 'Web Online · Stopped',
      'service.offline': 'Service Unavailable',
      'title.main': 'State Estimation Console',
      'action.run_se': 'Run SE Now',
      'action.running_se': 'Running SE...',
      'action.refresh': 'Refresh',
      'action.export_csv': 'Export CSV',
      'action.cancel': 'Cancel',
      'action.confirm_reset': 'Confirm Reset',
      'action.locate': 'Locate',
      'action.curve': 'Trend',
      'action.prefilter': '+Prefilter',
      'action.suppress': 'Suppress',
      'action.pseudo': 'Pseudo',
      'action.weight': 'Weight',
      'action.force_close': 'Force Close',
      'action.force_open': 'Force Open',
      'action.edit': 'Edit',
      'action.delete': 'Delete',
      'meas.high_res': 'High Res',
      'meas.tab_list': 'Measurements',
      'meas.tab_devices': 'Device Compare',
      'meas.tab_balance': 'Bus Balance & Obs',
      'dev.mode_compare': 'Meas / SE',
      'dev.mode_delta': 'Residual Δ',
      'topo.imb_overlay': 'Imb. Buses',
      'topo.imb_panel': 'Imbalance',
      'bal.only_imb': 'Imbalanced Only',
      'ph.search_bus': 'Search bus',
      'bal.bus': 'Bus',
      'bal.domain': 'Domain',
      'bal.v_meas_se': 'V (Meas/SE)',
      'bal.p_in': 'P In',
      'bal.p_out': 'P Out',
      'bal.dp_meas': 'Meas ΔP',
      'bal.dp_se': 'SE ΔP',
      'bal.dq_meas': 'Meas ΔQ',
      'bal.meas_cnt': 'Meas',
      'bal.status': 'Status',
      'bal.st_imb': 'Imbalanced',
      'bal.st_lowobs': 'Low Obs',
      'bal.st_ok': 'Balanced',
      'bal.summary': 'Buses {total} · Imb {imb} · LowObs {low} · Max |ΔP| {max}',
      'batch.suppress': 'Batch Suppress',
      'batch.prefilter': 'Batch Prefilter',
      'batch.clear': 'Clear',
      'batch.done': 'Saved {n} items',
      'qa.target': 'Target Measurement',
      'qa.min_val': 'Min Limit',
      'qa.max_val': 'Max Limit',
      'qa.pseudo_val': 'Pseudo Value',
      'qa.weight': 'Weight',
      'qa.note': 'Note / Reason',
      'qa.submit': 'Save & Apply',
      'qa.title_suppress': 'Suppress Measurement',
      'qa.title_prefilter': 'Add Prefilter Rule',
      'qa.title_pseudo': 'Set Pseudo Measurement',
      'qa.title_weight': 'Set Measurement Weight',
      'qa.saved': 'Saved and applied',
      'snap.latest': 'Latest',
      'snap.history': 'Replay',
      'params.trial': 'Save & Trial Run',
      'params.trial_running': 'Saving params & running trial SE…',
      'params.tab_para': 'Parameters',
      'params.tab_weights': 'Weights',
      'ph.search_wt': 'Search weight rules',
      'wt.add': '+ Add Weight',
      'wt.dlg_title': 'Measurement Weight Rule',
      'wt.scope': 'Scope',
      'wt.scope_type': 'Device Type',
      'wt.scope_dev': 'Single Device',
      'wt.dev_type': 'Device Type',
      'wt.dev_name': 'Device',
      'wt.metric': 'Metric',
      'wt.status': 'Status',
      'wt.saved': 'Weight rule saved',
      'wt.deleted': 'Weight rule deleted',
      'wt.del_confirm': 'Delete this weight rule?',
      'trial.title': 'Trial Diff',
      'trial.iters': 'Iter',
      'trial.pass': 'Pass',
      'trial.bad': 'Bad',
      'trial.obj': 'J(x)',
      'trial.elapsed': 'Time',
      'empty.no_match': 'No matching records',
      'bool.off': 'Off',
      'bool.on': 'On',
      'topo.zoom_in': 'Zoom in',
      'topo.zoom_out': 'Zoom out',
      'ui.sidebar_resize': 'Drag to resize / Double-click to toggle',
      'ui.sidebar_hide': 'Hide sidebar',
      'ui.sidebar_show': 'Show sidebar',
      'theme.light': 'Minimalist Light',
      'theme.dark': 'Precision Dark',
      'theme.bento': 'Bento Grid',
      'theme.glass': 'Glassmorphism',
      'theme.editorial': 'Editorial',
      'theme.cyan': 'Sci-Fi Cyan',
      'theme.purple': 'Sci-Fi Purple',
      'theme.matrix': 'Sci-Fi Matrix',
      'kpi.status': 'Convergence & Obs.',
      'kpi.pass_rate': 'SE Pass Rate',
      'kpi.bad_data': 'Bad Data Points',
      'kpi.residual': 'Total / Max Residual',
      'kpi.elapsed': 'Elapsed Time',
      'unit.count': 'pts',
      'status.converged': 'Converged',
      'status.diverged': 'Diverged',
      'status.observable': 'Observable',
      'status.unobservable': 'Unobservable',
      'status.no_bad': 'No Bad Data Alarm',
      'status.bad_alert': '{n} Bad Data Alarms',
      'status.closed': 'Closed',
      'status.open': 'Open',
      'status.succeeded': 'OK',
      'status.failed': 'Failed',
      'status.running': 'Running',
      'tab.topology': 'SVG Topology',
      'tab.curves': 'History Curves',
      'tab.devices': 'Device Compare',
      'tab.measurements': 'Valid Measurements',
      'tab.params': 'Parameters',
      'tab.runs': 'Runs & Schedule',
      'topo.mode': 'Display',
      'topo.mode_compare': 'Meas / SE Compare',
      'topo.mode_se': 'SE Only',
      'topo.mode_meas': 'Meas Only',
      'topo.mode_residual': 'Residual Δ',
      'topo.jump_placeholder': 'Locate device...',
      'topo.fit': 'Fit View',
      'topo.bad_panel': 'Bad Data Alarms',
      'topo.dev_detail': 'Device Comparison',
      'topo.no_bad_empty': '—',
      'topo.select_hint': '—',
      'topo.svg_missing': 'No SVG',
      'legend.meas': 'Measured',
      'legend.se': 'Estimated',
      'legend.bad': 'Bad Data Alarm',
      'curves.global_title': 'System SE Quality History',
      'curves.pass_rate': 'Pass Rate (%)',
      'curves.residual': 'Total / Max Residual',
      'curves.bad_data': 'Bad Data Count',
      'curves.elapsed': 'Elapsed (s)',
      'curves.window': 'Window',
      'curves.point_title': 'Point Measurement & Residual History',
      'curves.meas_vs_se': 'Meas vs SE',
      'curves.point_residual': 'Residual Δ',
      'curves.norm_residual': 'Norm. Residual',
      'curves.bad_hotspot_placeholder': 'Bad data hotspots...',
      'curves.no_data': 'No history data available',
      'curves.threshold': 'Bad threshold ±{v}',
      'curves.total_res': 'Total Residual',
      'curves.max_res': 'Max Residual',
      'curves.elapsed_total': 'Total (s)',
      'curves.elapsed_kernel': 'Kernel (s)',
      'devices.bad_only': 'Bad devices only',
      'devices.summary': '{n} devices',
      'ph.search_device': 'Filter ID or name',
      'ph.search_meas': 'Search device/meas',
      'meas.all': 'All',
      'meas.bad': 'Bad Data',
      'meas.normal': 'Normal',
      'meas.prefiltered': 'Prefiltered',
      'meas.pseudo': 'Pseudo',
      'sort.abs_res': '|Residual|',
      'sort.abs_norm': '|Norm. Residual|',
      'sort.id': 'Meas ID',
      'sort.dev': 'Device Name',
      'col.idx': 'ID',
      'col.device': 'Device',
      'col.metric': 'Metric',
      'col.meas': 'Meas',
      'col.se': 'SE',
      'col.residual': 'Δ',
      'col.norm_res': 'Norm. Res',
      'col.source': 'Source',
      'col.actions': 'Actions',
      'col.run': 'Run',
      'col.time': 'Calc Time',
      'col.status': 'Status',
      'col.pass_rate': 'Pass Rate',
      'col.bad_count': 'Bad',
      'col.elapsed': 'Elapsed (s)',
      'params.title': 'SE Algorithm Parameters (pas_se_para)',
      'params.reset': 'Reset Defaults',
      'params.save': 'Save Params',
      'params.saved': 'SE parameters saved',
      'params.reset_done': 'SE parameters reset from se.para',
      'params.group_core': 'Solver & Bad Data Detection',
      'params.group_pseudo': 'Pseudo Measurements & Observability',
      'params.group_pf': 'Initial Power Flow & Cycle',
      'runs.title': 'SE Run History',
      'runs.open_legacy': 'Open Details & dbdef →',
      'sched.title': 'SE Periodic Schedule',
      'sched.period': 'Period (s)',
      'sched.enabled': 'Enable periodic execution',
      'sched.save': 'Save Schedule',
      'sched.daemon_start': 'Start Daemon',
      'sched.daemon_stop': 'Stop Daemon',
      'sched.saved': 'SE schedule saved',
      'modal.reset_title': 'Reset pas_se_para',
      'modal.reset_desc': 'Restore defaults from se.para?',
      'pager.prev': 'Prev',
      'pager.next': 'Next',
      'pager.info': 'Page {page} / {pages} · {total}',
      'notice.se_submitted': 'SE job submitted',
      'notice.se_done': 'SE completed (#{id})',
      'notice.se_failed': 'SE failed: {msg}',
      'devtype.ACNode': 'ACNode',
      'devtype.DCNode': 'DCNode',
      'devtype.ACBranch': 'ACBranch',
      'devtype.DCBranch': 'DCBranch',
      'devtype.ACZeroBranch': 'ACZeroBranch',
      'devtype.ACGenerator': 'ACGenerator',
      'devtype.DCGenerator': 'DCGenerator',
      'devtype.ACLoad': 'ACLoad',
      'devtype.DCLoad': 'DCLoad',
      'devtype.DCDCConverter': 'DCDCConverter',
      'devtype.DCACConverter': 'DCACConverter',
      'devtype.ACBreak': 'ACBreak',
      'devtype.DCBreak': 'DCBreak',
      'devtype.ACRealBs': 'ACRealBs',
      'devtype.DCRealBs': 'DCRealBs',
      'devtype.ACPowerBalance': 'ACPowerBalance',
      'devtype.all': 'All Device Types',
    },
    'ru-RU': {
      'brand.sub': 'Онлайн-анализ сети',
      'nav.overview': 'Обзор',
      'nav.analysis': 'Анализ',
      'nav.se_root': 'Оценка сост. SE',
      'nav.se_main': 'Главная',
      'nav.se_flow': 'Схема потоков',
      'nav.se_curves': 'Графики истории',
      'nav.se_devices': 'Сравнение оборуд.',
      'nav.se_measurements': 'Анализ всех изм.',
      'nav.se_params': 'Параметры SE',
      'nav.se_prefilter': 'Предфильтр',
      'nav.se_pseudo': 'Псевдоизмерения',
      'nav.se_bad': 'Плохие данные',
      'nav.se_logs': 'Журнал работы',
      'title.flow': 'Схема потоков',
      'title.curves': 'Графики истории',
      'title.devices': 'Сравнение оборудования',
      'title.measurements': 'Анализ всех измерений',
      'title.params': 'Параметры алгоритма SE',
      'link.manage_bad': 'Обраб. →',
      'link.manage_bad_full': 'Плохие данные →',
      'link.manage_pseudo': 'Псевдоизм. →',
      'link.view_logs': 'Журнал →',
      'link.run_log': 'Лог',
      'nav.lf': 'Потокораспределение',
      'nav.ca': 'Надёжность N-1',
      'nav.management': 'Управление',
      'nav.runs': 'История расчётов',
      'nav.measurements': 'Измерения',
      'nav.limits': 'Ограничения',
      'nav.workspace': 'Рабочий каталог',
      'nav.settings': 'Настройки',
      'service.checking': 'Проверка сервиса',
      'service.daemon_on': 'Планировщик активен',
      'service.daemon_off': 'Веб онлайн · Остановлен',
      'service.offline': 'Сервис недоступен',
      'title.main': 'Оценка состояния сети',
      'action.run_se': 'Запустить ОС',
      'action.running_se': 'Расчёт ОС...',
      'action.refresh': 'Обновить',
      'action.export_csv': 'Экспорт CSV',
      'action.cancel': 'Отмена',
      'action.confirm_reset': 'Сбросить',
      'action.locate': 'На схеме',
      'action.curve': 'График',
      'action.prefilter': '+Фильтр',
      'action.suppress': 'Блок.',
      'action.pseudo': 'Псевдо',
      'action.weight': 'Вес',
      'action.force_close': 'Вкл (1)',
      'action.force_open': 'Откл (0)',
      'action.edit': 'Изм.',
      'action.delete': 'Удал.',
      'meas.high_res': 'Выс. невязка',
      'meas.tab_list': 'Все измерения',
      'meas.tab_devices': 'Оборудование',
      'meas.tab_balance': 'Баланс узлов',
      'dev.mode_compare': 'Meas / SE',
      'dev.mode_delta': 'Невязка Δ',
      'topo.imb_overlay': 'Небаланс узлов',
      'topo.imb_panel': 'Небаланс',
      'bal.only_imb': 'Небаланс',
      'ph.search_bus': 'Поиск узла',
      'bal.bus': 'Узел',
      'bal.domain': 'Тип',
      'bal.v_meas_se': 'U (Изм/SE)',
      'bal.p_in': 'P прит.',
      'bal.p_out': 'P отт.',
      'bal.dp_meas': 'ΔP изм.',
      'bal.dp_se': 'ΔP SE',
      'bal.dq_meas': 'ΔQ изм.',
      'bal.meas_cnt': 'ТИ',
      'bal.status': 'Статус',
      'bal.st_imb': 'Небаланс',
      'bal.st_lowobs': 'Мало ТИ',
      'bal.st_ok': 'Норма',
      'bal.summary': 'Узлов {total} · Небаланс {imb} · Мало ТИ {low} · Макс |ΔP| {max}',
      'batch.suppress': 'Пакет. блок.',
      'batch.prefilter': 'Пакет. фильтр',
      'batch.clear': 'Сброс',
      'batch.done': 'Сохранено: {n}',
      'qa.target': 'Измерение',
      'qa.min_val': 'Мин.',
      'qa.max_val': 'Макс.',
      'qa.pseudo_val': 'Значение',
      'qa.weight': 'Вес',
      'qa.note': 'Примечание',
      'qa.submit': 'Сохранить',
      'qa.title_suppress': 'Блокировать ТИ',
      'qa.title_prefilter': 'Правило предфильтра',
      'qa.title_pseudo': 'Задать псевдо-ТИ',
      'qa.title_weight': 'Задать вес ТИ',
      'qa.saved': 'Сохранено',
      'snap.latest': 'Последний',
      'snap.history': 'Архив',
      'params.trial': 'Сохранить и тест SE',
      'params.trial_running': 'Пробный расчёт SE…',
      'params.tab_para': 'Параметры',
      'params.tab_weights': 'Веса ТИ',
      'ph.search_wt': 'Поиск правил веса',
      'wt.add': '+ Вес',
      'wt.dlg_title': 'Правило веса измерения',
      'wt.scope': 'Область',
      'wt.scope_type': 'Тип оборуд.',
      'wt.scope_dev': 'Устройство',
      'wt.dev_type': 'Тип',
      'wt.dev_name': 'Устройство',
      'wt.metric': 'Параметр',
      'wt.status': 'Статус',
      'wt.saved': 'Правило веса сохранено',
      'wt.deleted': 'Правило веса удалено',
      'wt.del_confirm': 'Удалить правило веса?',
      'trial.title': 'Сравнение',
      'trial.iters': 'Итер.',
      'trial.pass': 'Годн.',
      'trial.bad': 'Сбои',
      'trial.obj': 'J(x)',
      'trial.elapsed': 'Время',
      'empty.no_match': 'Нет совпадений',
      'bool.off': 'Выкл',
      'bool.on': 'Вкл',
      'topo.zoom_in': 'Увеличить',
      'topo.zoom_out': 'Уменьшить',
      'ui.sidebar_resize': 'Перетащите ширину / Двойной клик скрыть',
      'ui.sidebar_hide': 'Скрыть меню',
      'ui.sidebar_show': 'Показать меню',
      'theme.light': 'Светлая',
      'theme.dark': 'Тёмная',
      'theme.bento': 'Бенто-сетка',
      'theme.glass': 'Стекло',
      'theme.editorial': 'Журнальный',
      'theme.cyan': 'Кибер-циан',
      'theme.purple': 'Кибер-фиолет',
      'theme.matrix': 'Матрица',
      'kpi.status': 'Сходимость и набл.',
      'kpi.pass_rate': 'Доля достоверных',
      'kpi.bad_data': 'Плохие данные',
      'kpi.residual': 'Сумм. / Макс. невязка',
      'kpi.elapsed': 'Время расчёта',
      'unit.count': 'шт.',
      'status.converged': 'Сходится',
      'status.diverged': 'Не сходится',
      'status.observable': 'Наблюдаема',
      'status.unobservable': 'Ненаблюдаема',
      'status.no_bad': 'Нет тревог',
      'status.bad_alert': 'Тревоги: {n}',
      'status.closed': 'Вкл',
      'status.open': 'Откл',
      'status.succeeded': 'Успешно',
      'status.failed': 'Ошибка',
      'status.running': 'В работе',
      'tab.topology': 'Схема SVG',
      'tab.curves': 'Графики истории',
      'tab.devices': 'Оборудование',
      'tab.measurements': 'Достоверные изм.',
      'tab.params': 'Параметры ОС',
      'tab.runs': 'Журнал и цикл',
      'topo.mode': 'Режим',
      'topo.mode_compare': 'Сравнение Meas / SE',
      'topo.mode_se': 'Только SE',
      'topo.mode_meas': 'Только Meas',
      'topo.mode_residual': 'Невязка Δ',
      'topo.jump_placeholder': 'Найти элемент...',
      'topo.fit': 'По экрану',
      'topo.bad_panel': 'Тревоги плохих данных',
      'topo.dev_detail': 'Сравнение элемента',
      'topo.no_bad_empty': '—',
      'topo.select_hint': '—',
      'topo.svg_missing': 'Нет SVG',
      'legend.meas': 'Измер. Meas',
      'legend.se': 'Оценка SE',
      'legend.bad': 'Плохие данные',
      'curves.global_title': 'История качества оценки состояния',
      'curves.pass_rate': 'Доля годных (%)',
      'curves.residual': 'Сумм. / Макс. невязка',
      'curves.bad_data': 'Число плохих',
      'curves.elapsed': 'Время (с)',
      'curves.window': 'Выборка',
      'curves.point_title': 'Графики точки измерения и невязок',
      'curves.meas_vs_se': 'Meas и SE',
      'curves.point_residual': 'Невязка Δ',
      'curves.norm_residual': 'Норм. невязка',
      'curves.bad_hotspot_placeholder': 'Частые плохие точки...',
      'curves.no_data': 'Нет данных истории',
      'curves.threshold': 'Порог ±{v}',
      'curves.total_res': 'Сумм. невязка',
      'curves.max_res': 'Макс. невязка',
      'curves.elapsed_total': 'Всего (с)',
      'curves.elapsed_kernel': 'Ядро (с)',
      'devices.bad_only': 'Только с ошибками',
      'devices.summary': 'Всего: {n}',
      'ph.search_device': 'Поиск по ID или имени',
      'ph.search_meas': 'Поиск измерения',
      'meas.all': 'Все',
      'meas.bad': 'Плохие',
      'meas.normal': 'Норма',
      'meas.prefiltered': 'Фильтр',
      'meas.pseudo': 'Псевдо',
      'sort.abs_res': '|Невязка|',
      'sort.abs_norm': '|Норм. невязка|',
      'sort.id': 'ID измер.',
      'sort.dev': 'Устройство',
      'col.idx': 'ID',
      'col.device': 'Оборудование',
      'col.metric': 'Параметр',
      'col.meas': 'Meas',
      'col.se': 'SE',
      'col.residual': 'Δ',
      'col.norm_res': 'Норм. r',
      'col.source': 'Тип',
      'col.actions': 'Действия',
      'col.run': 'Запуск',
      'col.time': 'Время расчёта',
      'col.status': 'Статус',
      'col.pass_rate': 'Годные',
      'col.bad_count': 'Плохие',
      'col.elapsed': 'Время (с)',
      'params.title': 'Параметры алгоритма ОС (pas_se_para)',
      'params.reset': 'Сбросить',
      'params.save': 'Сохранить',
      'params.saved': 'Параметры ОС сохранены',
      'params.reset_done': 'Параметры восстановлены из se.para',
      'params.group_core': 'Решатель и поиск плохих данных',
      'params.group_pseudo': 'Псевдоизмерения и наблюдаемость',
      'params.group_pf': 'Начальный расчёт и цикл',
      'runs.title': 'История запусков ОС',
      'runs.open_legacy': 'Открыть детали и dbdef →',
      'sched.title': 'Расписание ОС',
      'sched.period': 'Период (с)',
      'sched.enabled': 'Включить автозапуск',
      'sched.save': 'Сохранить',
      'sched.daemon_start': 'Старт цикла',
      'sched.daemon_stop': 'Стоп цикла',
      'sched.saved': 'Расписание ОС сохранено',
      'modal.reset_title': 'Сброс pas_se_para',
      'modal.reset_desc': 'Восстановить значения из se.para?',
      'pager.prev': 'Назад',
      'pager.next': 'Далее',
      'pager.info': 'Стр. {page} / {pages} · {total}',
      'notice.se_submitted': 'Расчёт ОС поставлен в очередь',
      'notice.se_done': 'Расчёт ОС завершён (#{id})',
      'notice.se_failed': 'Ошибка ОС: {msg}',
      'devtype.ACNode': 'Узлы AC (ACNode)',
      'devtype.DCNode': 'Узлы DC (DCNode)',
      'devtype.ACBranch': 'Линии AC (ACBranch)',
      'devtype.DCBranch': 'Линии DC (DCBranch)',
      'devtype.ACZeroBranch': 'Нулевые ветви AC',
      'devtype.ACGenerator': 'Генераторы AC',
      'devtype.DCGenerator': 'Генераторы DC',
      'devtype.ACLoad': 'Нагрузки AC',
      'devtype.DCLoad': 'Нагрузки DC',
      'devtype.DCDCConverter': 'Преобр. DC/DC',
      'devtype.DCACConverter': 'Преобр. DC/AC',
      'devtype.ACBreak': 'Выключатели AC',
      'devtype.DCBreak': 'Выключатели DC',
      'devtype.ACRealBs': 'Шины AC',
      'devtype.DCRealBs': 'Шины DC',
      'devtype.ACPowerBalance': 'Баланс P/Q (AC)',
      'devtype.all': 'Все типы',
    },
  };

  /** SE 算法参数分组与多语言字段名 */
  const PARAM_SCHEMA = [
    {
      group: 'params.group_core',
      fields: [
        { key: 'max_iterator', type: 'int', min: 1, max: 1000, label: { 'zh-CN': '迭代次数上限 (max_iterator)', 'en-US': 'Max Iterations', 'ru-RU': 'Макс. итераций' } },
        { key: 'badnum_max', type: 'int', min: 0, max: 500, label: { 'zh-CN': '坏数据总数上限 (badnum_max)', 'en-US': 'Max Bad Data Total', 'ru-RU': 'Лимит плохих данных' } },
        { key: 'badnum_step', type: 'int', min: 1, max: 100, label: { 'zh-CN': '坏数据单步上限 (badnum_step)', 'en-US': 'Max Bad Data / Step', 'ru-RU': 'Плохих за шаг' } },
        { key: 'baderr_eps', type: 'float', min: 1e-6, max: 1e6, step: 'any', label: { 'zh-CN': '坏数据门槛 (baderr_eps)', 'en-US': 'Bad Data Threshold', 'ru-RU': 'Порог плохих данных' } },
        { key: 'tol', type: 'float', min: 1e-14, max: 1, step: 'any', label: { 'zh-CN': '收敛精度容差 (tol)', 'en-US': 'Convergence Tolerance', 'ru-RU': 'Точность сходимости' } },
        { key: 'diff_step', type: 'float', min: 1e-12, max: 1, step: 'any', label: { 'zh-CN': '数值差分步长 (diff_step)', 'en-US': 'Diff Step', 'ru-RU': 'Шаг дифференцирования' } },
        { key: 'flat_start', type: 'bool', label: { 'zh-CN': '平启动模式 (flat_start)', 'en-US': 'Flat Start', 'ru-RU': 'Плоский старт' } },
        { key: 'voltage_floor', type: 'float', min: 1e-4, max: 1, step: 'any', label: { 'zh-CN': '电压下限保护 (voltage_floor)', 'en-US': 'Voltage Floor (p.u.)', 'ru-RU': 'Нижний предел U (о.е.)' } },
        { key: 'min_current_voltage', type: 'float', min: 1e-6, max: 1, step: 'any', label: { 'zh-CN': '电流计算最小电压', 'en-US': 'Min Current Voltage', 'ru-RU': 'Мин. U для расчёта I' } },
      ],
    },
    {
      group: 'params.group_pseudo',
      fields: [
        { key: 'pseudo_measurement_weight', type: 'float', min: 1e-12, max: 1e6, step: 'any', label: { 'zh-CN': '伪量测权重', 'en-US': 'Pseudo Meas Weight', 'ru-RU': 'Вес псевдоизмерений' } },
        { key: 'targeted_pseudo_measurement_max', type: 'int', min: 0, max: 100000, label: { 'zh-CN': '定向伪量测上限', 'en-US': 'Targeted Pseudo Max', 'ru-RU': 'Макс. целевых псевдо' } },
        { key: 'targeted_pseudo_measurement_redundancy_ratio', type: 'float', min: 0, max: 100, step: 'any', label: { 'zh-CN': '定向伪量测冗余比', 'en-US': 'Pseudo Redundancy Ratio', 'ru-RU': 'Коэф. избыточности' } },
        { key: 'targeted_pseudo_measurement_step', type: 'int', min: 1, max: 10000, label: { 'zh-CN': '定向伪量测步长', 'en-US': 'Targeted Pseudo Step', 'ru-RU': 'Шаг целевых псевдо' } },
        { key: 'obj_scaling_factor', type: 'float', min: 1e-9, max: 1e9, step: 'any', label: { 'zh-CN': '目标函数缩放因子', 'en-US': 'Objective Scaling', 'ru-RU': 'Масштаб целевой ф-ции' } },
      ],
    },
    {
      group: 'params.group_pf',
      fields: [
        { key: 'power_flow_tol', type: 'float', min: 1e-14, max: 1, step: 'any', label: { 'zh-CN': '初值潮流容差', 'en-US': 'PF Init Tolerance', 'ru-RU': 'Точность нач. УР' } },
        { key: 'power_flow_max_iter', type: 'int', min: 1, max: 5000, label: { 'zh-CN': '初值潮流最大迭代', 'en-US': 'PF Init Max Iter', 'ru-RU': 'Макс. итераций УР' } },
        { key: 'power_flow_min_voltage', type: 'float', min: 1e-6, max: 1, step: 'any', label: { 'zh-CN': '初值潮流最小电压', 'en-US': 'PF Init Min Voltage', 'ru-RU': 'Мин. U нач. УР' } },
        { key: 'do_cycle', type: 'int', min: 1, max: 604800, label: { 'zh-CN': '计算周期参考 (s)', 'en-US': 'Cycle Reference (s)', 'ru-RU': 'Период расчёта (с)' } },
      ],
    },
  ];

  const INITIAL_VIEW = document.body.dataset.seView || 'topology';
  const SINGLE_VIEW_PAGE = Boolean(document.body.dataset.seView);

  const appState = {
    lang: localStorage.getItem('pas_se_lang') || localStorage.getItem('se_lang') || 'zh-CN',
    theme: localStorage.getItem('pas_se_theme') || localStorage.getItem('se_theme') || 'minimalist-light',
    view: INITIAL_VIEW,
    overview: null,
    topology: null,
    svgLoaded: false,
    svgDisplayMode: 'compare',
    topoImbOverlay: false,
    topoSideTab: 'bad',
    selectedDevId: null,
    svgTransform: { scale: 1, tx: 0, ty: 0, vbW: 2518, vbH: 2143 },
    curves: {
      limit: 50,
      globalMetric: 'pass_rate',
      pointMode: 'value',
      statsSeries: [],
      badHistory: null,
      pointsCatalog: [],
      selectedPoint: null,
      pointSeries: null,
    },
    devices: { type: 'ACNode', q: '', badOnly: false, mode: 'compare', data: null },
    meas: { source: 'all', devType: '', sort: 'abs_residual', direction: 'desc', highResOnly: false, q: '', page: 0, size: 30, data: null, reqSeq: 0, subTab: 'list', selected: new Map() },
    balance: { domain: 'all', onlyImb: false, q: '', data: null },
    paramsSubTab: 'para',
    weights: { type: '', q: '', rows: [] },
    catalog: null,
    convergedRuns: [],
    selectedRunId: '',
    params: null,
    schedule: null,
    watchingJobId: null,
    noticeTimer: null,
  };

  function t(key, params = {}) {
    const dict = I18N_DICT[appState.lang] || I18N_DICT['zh-CN'];
    let text = dict[key] ?? I18N_DICT['zh-CN'][key] ?? key;
    for (const [k, v] of Object.entries(params)) {
      text = text.replaceAll(`{${k}}`, String(v));
    }
    return text;
  }

  function devTypeLabel(dt) {
    const key = `devtype.${dt}`;
    const dict = I18N_DICT[appState.lang] || I18N_DICT['zh-CN'];
    return dict[key] ?? I18N_DICT['zh-CN'][key] ?? String(dt || '');
  }

  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  }

  function fmtNum(v, digits = 2) {
    if (v === null || v === undefined || Number.isNaN(Number(v))) return '—';
    const n = Number(v);
    if (!Number.isFinite(n)) return '—';
    if (Math.abs(n) >= 1000) return n.toFixed(1);
    if (Math.abs(n) >= 100) return n.toFixed(2);
    if (Math.abs(n) >= 1) return n.toFixed(digits);
    if (Math.abs(n) === 0) return '0';
    return Number(n.toPrecision(3)).toString();
  }

  function fmtTime(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso).slice(0, 19).replace('T', ' ');
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }

  function fmtShortTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso).slice(11, 19);
    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }

  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function notify(msg, isError = false) {
    const box = document.getElementById('notice');
    box.textContent = msg;
    box.className = `notice ${isError ? 'error' : 'success'}`;
    box.hidden = false;
    clearTimeout(appState.noticeTimer);
    appState.noticeTimer = setTimeout(() => { box.hidden = true; }, 5500);
  }

  async function api(url, body, method) {
    const opts = method
      ? {
          method,
          headers: { 'Content-Type': 'application/json' },
          ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
        }
      : (body === undefined ? {} : {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
    const res = await fetch(url, opts);
    const payload = await res.json().catch(() => ({ ok: false, error: `HTTP ${res.status}` }));
    if (!res.ok || !payload.ok) {
      throw new Error(payload.error || (payload.data && payload.data.error_message) || `HTTP ${res.status}`);
    }
    return payload.data;
  }

  function applyI18n() {
    document.documentElement.lang = appState.lang;
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      el.placeholder = t(el.dataset.i18nPlaceholder);
    });
    document.querySelectorAll('[data-i18n-title]').forEach((el) => {
      el.title = t(el.dataset.i18nTitle);
    });
    const resizer = document.querySelector('.sidebar-resizer');
    const toggleBtn = resizer?.querySelector('.sidebar-toggle-btn');
    if (resizer) resizer.title = t('ui.sidebar_resize');
    if (toggleBtn) {
      const isCol = resizer.classList.contains('is-collapsed');
      toggleBtn.title = t(isCol ? 'ui.sidebar_show' : 'ui.sidebar_hide');
      toggleBtn.setAttribute('aria-label', toggleBtn.title);
    }
    const titleKeyMap = {
      topology: 'title.flow',
      curves: 'title.curves',
      devices: 'title.devices',
      measurements: 'title.measurements',
      params: 'title.params',
    };
    document.title = `${t(titleKeyMap[appState.view] || 'title.main')} · PAS`;
  }

  function applyTheme() {
    document.documentElement.dataset.theme = appState.theme;
    const sel = document.getElementById('theme-select');
    if (sel) sel.value = appState.theme;
  }

  /* ==================== KPI 与顶栏渲染（严格单行精简，不折行、无废话） ==================== */
  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function renderOverviewKPIs() {
    const ov = appState.overview;
    const latest = ov?.latest;
    const badList = ov?.bad_data || [];
    const convPill = document.getElementById('se-conv-pill');
    const badPill = document.getElementById('se-bad-pill');
    const runMeta = document.getElementById('se-run-meta');

    if (!latest) {
      if (convPill) { convPill.className = 'se-pill neutral'; convPill.textContent = '—'; }
      if (badPill) badPill.hidden = true;
      if (runMeta) runMeta.textContent = '—';
      return;
    }

    const conv = Boolean(latest.converged);
    const obs = Boolean(latest.observable);
    if (convPill) {
      convPill.className = `se-pill ${conv ? 'ok' : 'bad'}`;
      convPill.textContent = conv ? t('status.converged') : t('status.diverged');
    }
    if (badPill) {
      badPill.hidden = false;
      if (badList.length > 0) {
        badPill.className = 'se-pill bad bad-pulse';
        badPill.textContent = t('status.bad_alert', { n: badList.length });
      } else {
        badPill.className = 'se-pill ok';
        badPill.textContent = t('status.no_bad');
      }
    }
    if (runMeta) runMeta.textContent = `#${latest.run_id} · ${fmtTime(latest.calc_time)}`;

    const dot = document.getElementById('kpi-dot-status');
    if (dot) dot.className = `se-dot ${conv && obs ? 'ok' : 'bad'}`;
    setText('kpi-conv', conv ? t('status.converged') : t('status.diverged'));
    setText('kpi-obs', `${obs ? t('status.observable') : t('status.unobservable')} · ${latest.iterations}it`);

    const passPct = (Number(latest.pass_rate || 0) * 100).toFixed(2);
    setText('kpi-pass', passPct);
    setText('kpi-meas-ratio', `${latest.good_meas_count}/${latest.valid_meas_count}`);

    const badCount = Number(latest.bad_data_count || badList.length || 0);
    setText('kpi-bad', String(badCount));
    const badCard = document.getElementById('kpi-card-bad');
    if (badCard) badCard.classList.toggle('is-alert', badCount > 0);

    setText('kpi-res-total', fmtNum(latest.total_residual, 2));
    setText('kpi-res-max', `max ${fmtNum(latest.residual_inf, 2)}`);
    setText('kpi-elapsed', Number(latest.elapsed_seconds || 0).toFixed(3));
  }

  /* ==================== 1. SVG 潮流图可视化与坏数据告警闪烁 ==================== */
  function applySvgTransform() {
    const canvas = document.getElementById('se-svg-canvas');
    const { scale, tx, ty } = appState.svgTransform;
    canvas.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
    document.getElementById('svg-zoom-label').textContent = `${Math.round(scale * 100)}%`;
  }

  function fitSvgToViewport() {
    const vp = document.getElementById('se-svg-viewport');
    const svg = document.querySelector('#se-svg-canvas > svg');
    if (!vp || !svg) return;
    const rect = vp.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    // SVG 自身 preserveAspectRatio="xMidYMid meet" 已经铺满 canvas (width/height 100%)
    appState.svgTransform.scale = 1;
    appState.svgTransform.tx = 0;
    appState.svgTransform.ty = 0;
    applySvgTransform();
  }

  function zoomSvgAt(factor, clientX, clientY) {
    const vp = document.getElementById('se-svg-viewport');
    const rect = vp.getBoundingClientRect();
    const ox = clientX !== undefined ? clientX - rect.left : rect.width / 2;
    const oy = clientY !== undefined ? clientY - rect.top : rect.height / 2;
    const prev = appState.svgTransform.scale;
    const next = Math.max(0.35, Math.min(6.0, prev * factor));
    const ratio = next / prev;
    appState.svgTransform.tx = ox - (ox - appState.svgTransform.tx) * ratio;
    appState.svgTransform.ty = oy - (oy - appState.svgTransform.ty) * ratio;
    appState.svgTransform.scale = next;
    applySvgTransform();
  }

  function focusSvgDevice(devId) {
    const svg = document.querySelector('#se-svg-canvas > svg');
    const vp = document.getElementById('se-svg-viewport');
    if (!svg || !vp || !devId) return;
    const target = svg.querySelector(`[id="${CSS.escape(devId)}"]`)
      || svg.querySelector(`use[dev-id="${CSS.escape(devId)}"]`)
      || svg.querySelector(`g.mg[dev="${CSS.escape(devId)}"]`);
    if (!target) return;

    selectTopologyDevice(devId);

    const vpRect = vp.getBoundingClientRect();
    // 临时重置 transform 获取基准屏幕坐标
    const prev = { ...appState.svgTransform };
    appState.svgTransform.scale = 1;
    appState.svgTransform.tx = 0;
    appState.svgTransform.ty = 0;
    applySvgTransform();

    const tRect = target.getBoundingClientRect();
    if (!tRect.width && !tRect.height) {
      appState.svgTransform = prev;
      applySvgTransform();
      return;
    }
    const cx = (tRect.left + tRect.width / 2) - vpRect.left;
    const cy = (tRect.top + tRect.height / 2) - vpRect.top;
    const targetScale = Math.max(2.2, Math.min(3.5, prev.scale > 1.8 ? prev.scale : 2.6));
    appState.svgTransform.scale = targetScale;
    appState.svgTransform.tx = vpRect.width / 2 - cx * targetScale;
    appState.svgTransform.ty = vpRect.height / 2 - cy * targetScale;
    applySvgTransform();
  }

  function initSvgInteractions() {
    const vp = document.getElementById('se-svg-viewport');
    if (!vp) return;
    let dragging = false;
    let startX = 0;
    let startY = 0;
    let moved = false;

    vp.addEventListener('wheel', (e) => {
      e.preventDefault();
      zoomSvgAt(e.deltaY < 0 ? 1.16 : 1 / 1.16, e.clientX, e.clientY);
    }, { passive: false });

    vp.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      dragging = true;
      moved = false;
      startX = e.clientX - appState.svgTransform.tx;
      startY = e.clientY - appState.svgTransform.ty;
      vp.classList.add('dragging');
    });

    window.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      const nx = e.clientX - startX;
      const ny = e.clientY - startY;
      if (Math.hypot(nx - appState.svgTransform.tx, ny - appState.svgTransform.ty) > 3) moved = true;
      appState.svgTransform.tx = nx;
      appState.svgTransform.ty = ny;
      applySvgTransform();
    });

    window.addEventListener('mouseup', () => {
      if (!dragging) return;
      dragging = false;
      vp.classList.remove('dragging');
    });

    vp.addEventListener('click', (e) => {
      if (moved) return;
      const devEl = e.target.closest('[dev-id], g.mg[dev]');
      if (!devEl) return;
      const devId = devEl.getAttribute('dev-id') || devEl.getAttribute('dev');
      if (devId) selectTopologyDevice(devId);
    });

    vp.addEventListener('mousemove', (e) => {
      if (dragging) {
        document.getElementById('se-svg-tooltip').hidden = true;
        return;
      }
      const devEl = e.target.closest('[dev-id], g.mg[dev]');
      const tip = document.getElementById('se-svg-tooltip');
      if (!devEl || !appState.topology) {
        tip.hidden = true;
        return;
      }
      const devId = devEl.getAttribute('dev-id') || devEl.getAttribute('dev');
      const dev = appState.topology.devices?.[devId];
      if (!dev) {
        tip.hidden = true;
        return;
      }
      const rows = Object.values(dev.metrics || {}).slice(0, 8).map((m) => `
        <div class="se-tt-row ${m.is_bad ? 'bad' : ''}">
          <span>${esc(m.metric)}</span>
          <span class="tabular">M: ${fmtNum(m.meas)}</span>
          <span class="tabular">SE: ${fmtNum(m.se)} ${esc(m.unit)}</span>
        </div>
      `).join('');
      tip.innerHTML = `<h4><span>${esc(dev.name)}</span><span class="se-tag">${esc(dev.device_type)}</span></h4>${rows}`;
      const rect = vp.getBoundingClientRect();
      let left = e.clientX - rect.left + 14;
      let top = e.clientY - rect.top + 14;
      if (left + 260 > rect.width) left = Math.max(8, left - 275);
      if (top + 180 > rect.height) top = Math.max(8, top - 160);
      tip.style.left = `${left}px`;
      tip.style.top = `${top}px`;
      tip.hidden = false;
    });

    vp.addEventListener('mouseleave', () => {
      document.getElementById('se-svg-tooltip').hidden = true;
    });
  }

  async function ensureSvgLoaded() {
    if (appState.svgLoaded) return true;
    const host = document.getElementById('se-svg-canvas');
    try {
      const res = await fetch('/api/se/svg');
      if (!res.ok) throw new Error(t('topo.svg_missing'));
      const svgText = await res.text();
      host.innerHTML = svgText;
      const svg = host.querySelector('svg');
      if (!svg) throw new Error(t('topo.svg_missing'));
      svg.setAttribute('width', '100%');
      svg.setAttribute('height', '100%');
      appState.svgLoaded = true;
      fitSvgToViewport();
      return true;
    } catch (err) {
      host.innerHTML = `<div class="se-empty">${esc(err.message)}</div>`;
      return false;
    }
  }

  function populateDeviceJumpSelect() {
    const sel = document.getElementById('svg-device-jump');
    const devs = appState.topology?.devices || {};
    const byType = new Map();
    Object.values(devs).forEach((d) => {
      if (!byType.has(d.device_type)) byType.set(d.device_type, []);
      byType.get(d.device_type).push(d);
    });
    let html = `<option value="">${esc(t('topo.jump_placeholder'))}</option>`;
    for (const [dtype, list] of byType.entries()) {
      list.sort((a, b) => a.idx - b.idx);
      html += `<optgroup label="${esc(devTypeLabel(dtype))}">`;
      for (const d of list) {
        const mark = d.has_bad ? '⚠ ' : '';
        html += `<option value="${esc(d.dev_id)}">${mark}${esc(d.name)} (#${d.idx})</option>`;
      }
      html += '</optgroup>';
    }
    sel.innerHTML = html;
    if (appState.selectedDevId) sel.value = appState.selectedDevId;
  }

  function renderSvgBindings() {
    const svg = document.querySelector('#se-svg-canvas > svg');
    if (!svg || !appState.topology) return;

    const devices = appState.topology.devices || {};
    const mode = appState.svgDisplayMode;
    const colorMeas = cssVar('--chart-meas') || '#D97706';
    const colorSe = cssVar('--chart-se') || '#2563EB';
    const colorBad = cssVar('--chart-bad') || '#DC2626';
    const colorMuted = cssVar('--text-secondary') || '#64748B';

    // 清理上一轮动态叠加层与闪烁类
    svg.querySelectorAll('.se-bad-ring,.se-imb-ring').forEach((n) => n.remove());
    svg.querySelectorAll('.se-bad-device').forEach((n) => n.classList.remove('se-bad-device'));
    svg.querySelectorAll('.se-bad-meas-text').forEach((n) => n.classList.remove('se-bad-meas-text'));

    // 1. 绑定每个量测框 <g class="mg" dev="...">
    svg.querySelectorAll('g.mg[dev]').forEach((mg) => {
      const devId = mg.getAttribute('dev');
      const dev = devices[devId];
      if (!dev) return;

      const slots = dev.svg_slots || {};
      let boxHasBad = Boolean(dev.has_bad);

      mg.querySelectorAll('text').forEach((textEl) => {
        const mv = textEl.querySelector('tspan.mv[mt]');
        if (!mv) return;
        const mt = mv.getAttribute('mt');
        const slot = slots[mt];
        if (!slot) return;

        // 修正单位 tspan（原图模板可能带 MW/kV）
        const tspans = Array.from(textEl.children).filter((n) => n.tagName.toLowerCase() === 'tspan');
        const unitSpan = tspans.length >= 3 ? tspans[tspans.length - 1] : null;
        if (unitSpan && slot.unit !== undefined) {
          unitSpan.textContent = slot.unit;
        }

        const isBad = Boolean(slot.is_bad || slot.any_bad);
        if (isBad) {
          boxHasBad = true;
          textEl.classList.add('se-bad-meas-text');
        }

        // 清空 mv 并按模式写入对比值
        mv.textContent = '';
        if (mt === 'status') {
          mv.textContent = slot.meas === 1 ? t('status.closed') : slot.meas === 0 ? t('status.open') : '--';
          mv.setAttribute('fill', slot.meas === 1 ? cssVar('--sem-ok') : colorMuted);
          return;
        }

        if (mode === 'compare') {
          const sM = document.createElementNS(SVG_NS, 'tspan');
          sM.textContent = fmtNum(slot.meas);
          sM.setAttribute('fill', isBad ? colorBad : colorMeas);
          const sSep = document.createElementNS(SVG_NS, 'tspan');
          sSep.textContent = ' / ';
          sSep.setAttribute('fill', colorMuted);
          const sE = document.createElementNS(SVG_NS, 'tspan');
          sE.textContent = fmtNum(slot.se);
          sE.setAttribute('fill', isBad ? colorBad : colorSe);
          mv.append(sM, sSep, sE);
        } else if (mode === 'se') {
          mv.textContent = fmtNum(slot.se);
          mv.setAttribute('fill', isBad ? colorBad : colorSe);
        } else if (mode === 'meas') {
          mv.textContent = fmtNum(slot.meas);
          mv.setAttribute('fill', isBad ? colorBad : colorMeas);
        } else {
          const d = slot.residual;
          mv.textContent = d == null ? '—' : `${d >= 0 ? '+' : ''}${fmtNum(d)}`;
          mv.setAttribute('fill', isBad ? colorBad : colorSe);
        }
      });

      // 为量测框补充自适应背景板，防止数值与底图导线重叠
      let bg = mg.querySelector('rect.se-mg-bg');
      if (bg) bg.remove();
      try {
        const bb = mg.getBBox();
        if (bb.width > 0 && bb.height > 0) {
          bg = document.createElementNS(SVG_NS, 'rect');
          bg.setAttribute('class', `se-mg-bg${boxHasBad ? ' is-bad' : ''}`);
          bg.setAttribute('x', String(bb.x - 5));
          bg.setAttribute('y', String(bb.y - 3));
          bg.setAttribute('width', String(bb.width + 10));
          bg.setAttribute('height', String(bb.height + 6));
          mg.insertBefore(bg, mg.firstChild);
        }
      } catch (_) {
        // 隐藏状态下 getBBox 可能抛出，切换到 topology 视图时重新调用即可
      }
    });

    // 2. 对存在坏数据的设备图元添加告警闪烁与脉冲光环
    const badIds = appState.topology.bad_dev_ids || [];
    badIds.forEach((devId) => {
      const elems = svg.querySelectorAll(`[dev-id="${CSS.escape(devId)}"]`);
      elems.forEach((el) => {
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
        } catch (_) { /* ignore */ }
      });
    });

    // 2b. 不平衡母线高亮叠加（映射 ACNode/DCNode 及其关联实母线 ACRealBs/DCRealBs）
    const imbBtn = document.getElementById('btn-topo-imb-overlay');
    const imbRows = (appState.balance.data?.rows || []).filter((r) => r.imbalanced);
    if (imbBtn) {
      imbBtn.classList.toggle('active', appState.topoImbOverlay);
      imbBtn.innerHTML = `${esc(t('topo.imb_overlay'))}<span class="cnt tabular">${imbRows.length}</span>`;
    }
    if (appState.topoImbOverlay && imbRows.length) {
      const imbNodeSet = new Set(imbRows.map((r) => r.dev_id));
      const targetSvgIds = new Set(imbNodeSet);
      Object.values(devices).forEach((dev) => {
        if (dev.linked_node) {
          const nid = `${dev.linked_node.device_type}-${dev.linked_node.idx}`;
          if (imbNodeSet.has(nid)) targetSvgIds.add(dev.dev_id);
        }
      });
      targetSvgIds.forEach((devId) => {
        svg.querySelectorAll(`[dev-id="${CSS.escape(devId)}"]`).forEach((el) => {
          if ((el.id || '').startsWith('label_')) return;
          try {
            const bb = el.getBBox();
            if (bb.width > 0 && bb.height > 0 && el.parentNode) {
              const ring = document.createElementNS(SVG_NS, 'rect');
              ring.setAttribute('class', 'se-imb-ring');
              ring.setAttribute('x', String(bb.x - 8));
              ring.setAttribute('y', String(bb.y - 8));
              ring.setAttribute('width', String(bb.width + 16));
              ring.setAttribute('height', String(bb.height + 16));
              ring.setAttribute('rx', '8');
              if (el.getAttribute('transform')) ring.setAttribute('transform', el.getAttribute('transform'));
              el.parentNode.insertBefore(ring, el);
            }
          } catch (_) { /* ignore */ }
        });
      });
    }

    // 3. 恢复当前选中设备高亮
    svg.querySelectorAll('.se-dev-selected').forEach((n) => n.classList.remove('se-dev-selected'));
    if (appState.selectedDevId) {
      svg.querySelectorAll(`[dev-id="${CSS.escape(appState.selectedDevId)}"]`).forEach((el) => {
        if (!(el.id || '').startsWith('label_')) el.classList.add('se-dev-selected');
      });
    }
  }

  function renderTopoBadPanel() {
    const badList = appState.topology?.bad_data || [];
    const imbList = (appState.balance.data?.rows || []).filter((r) => r.imbalanced);
    const isImb = appState.topoSideTab === 'imb';
    const pill = document.getElementById('topo-bad-count');
    const host = document.getElementById('topo-bad-list');
    const moreLink = document.getElementById('topo-side-more');
    document.querySelectorAll('#topo-side-seg .seg').forEach((b) => b.classList.toggle('active', b.dataset.tside === appState.topoSideTab));
    if (moreLink) {
      moreLink.href = isImb ? '/se-measurements.html?sub=balance' : '/se-bad.html';
    }
    if (isImb) {
      pill.textContent = String(imbList.length);
      pill.className = `se-pill tabular ${imbList.length ? 'warn' : 'ok'}`;
      if (!imbList.length) {
        host.innerHTML = `<div class="se-empty">${esc(t('topo.no_bad_empty'))}</div>`;
        return;
      }
      const pu = appState.balance.data?.units?.p_unit || 'kW';
      const devices = appState.topology?.devices || {};
      const nodeToBusId = {};
      Object.values(devices).forEach((d) => {
        if (d.linked_node) nodeToBusId[`${d.linked_node.device_type}-${d.linked_node.idx}`] = d.dev_id;
      });
      host.innerHTML = imbList.map((r) => {
        const focusId = nodeToBusId[r.dev_id] || r.dev_id;
        return `
          <button type="button" class="se-imb-item" data-focus-dev="${esc(focusId)}">
            <div class="top">
              <span>${esc(r.name)} <small class="se-muted">${esc(r.domain)}</small></span>
              <span class="tabular">ΔP=${fmtNum(r.dp_meas, 2)} ${esc(pu)}</span>
            </div>
            <div class="vals tabular">
              In: ${fmtNum(r.p_in_meas, 1)} / Out: ${fmtNum(r.p_out_meas, 1)} · SE ΔP: ${fmtNum(r.dp_se, 3)}
            </div>
          </button>`;
      }).join('');
      return;
    }

    pill.textContent = String(badList.length);
    pill.className = `se-pill tabular ${badList.length ? 'bad bad-pulse' : 'ok'}`;
    if (!badList.length) {
      host.innerHTML = `<div class="se-empty">${esc(t('topo.no_bad_empty'))}</div>`;
      return;
    }
    host.innerHTML = badList.map((b) => {
      const devId = b.device_idx != null ? `${b.device_type}-${b.device_idx}` : '';
      return `
        <button type="button" class="se-bad-item" data-focus-dev="${esc(devId)}" data-jump-curve="${esc(b.device_type)}|${esc(b.device_name)}|${esc(b.meas_type)}">
          <div class="top">
            <span>${esc(b.device_name)} · ${esc(b.metric || b.meas_type)}</span>
            <span class="tabular">rN=${fmtNum(b.normalized_residual, 2)}</span>
          </div>
          <div class="vals tabular">
            M: ${fmtNum(b.meas_value)} → SE: ${fmtNum(b.se_value)} ${esc(b.unit || '')} (Δ=${fmtNum(b.residual)})
          </div>
        </button>
      `;
    }).join('');
  }

  function selectTopologyDevice(devId) {
    appState.selectedDevId = devId;
    const sel = document.getElementById('svg-device-jump');
    if (sel && sel.value !== devId) sel.value = devId;
    renderSvgBindings();

    const dev = appState.topology?.devices?.[devId];
    const titleEl = document.getElementById('inspector-dev-title');
    const typeEl = document.getElementById('inspector-dev-type');
    const bodyEl = document.getElementById('inspector-dev-body');

    if (!dev) {
      titleEl.textContent = t('topo.dev_detail');
      typeEl.textContent = '--';
      bodyEl.innerHTML = `<div class="se-empty">${esc(t('topo.select_hint'))}</div>`;
      return;
    }

    titleEl.textContent = dev.name;
    typeEl.textContent = `${dev.device_type} #${dev.idx}`;
    const targetType = dev.linked_node?.device_type || dev.device_type;
    const targetIdx = dev.linked_node?.idx ?? dev.idx;
    const targetName = dev.linked_node?.name || dev.name;
    const canForceStatus = ['ACBreak', 'DCBreak', 'ACGenerator', 'DCGenerator', 'ACLoad', 'DCLoad', 'ACBranch', 'DCBranch', 'DCDCConverter', 'DCACConverter'].includes(targetType);

    const statusBar = canForceStatus ? `
      <div class="se-insp-actions">
        <button type="button" class="se-btn mini" data-force-stat="${esc(targetType)}|${esc(targetIdx)}|${esc(targetName)}|1">${esc(t('action.force_close'))}</button>
        <button type="button" class="se-btn mini danger-ghost" data-force-stat="${esc(targetType)}|${esc(targetIdx)}|${esc(targetName)}|0">${esc(t('action.force_open'))}</button>
      </div>` : '';

    const rows = Object.values(dev.metrics || {}).map((m) => {
      const qaPayload = esc(JSON.stringify({
        device_type: targetType,
        device_idx: targetIdx,
        device_name: targetName,
        metric: m.metric,
        unit: m.unit || '',
        meas_value: m.meas,
        se_value: m.se,
      }));
      return `
      <tr class="${m.is_bad ? 'is-bad' : ''}">
        <td class="clickable" data-open-curve="${esc(targetType)}|${esc(targetName)}|${esc(m.meas_type)}" title="${esc(t('action.curve'))}">${esc(m.metric)} <small class="se-muted">${esc(m.unit)}</small></td>
        <td class="num tabular">${fmtNum(m.meas)}</td>
        <td class="num tabular">${fmtNum(m.se)}</td>
        <td class="num tabular">${fmtNum(m.residual)}</td>
        <td class="se-insp-ops">
          <button type="button" class="se-btn mini" data-qa-mode="suppress" data-qa="${qaPayload}">${esc(t('action.suppress'))}</button>
          <button type="button" class="se-btn mini" data-qa-mode="pseudo" data-qa="${qaPayload}">${esc(t('action.pseudo'))}</button>
          <button type="button" class="se-btn mini" data-qa-mode="weight" data-qa="${qaPayload}">${esc(t('action.weight'))}</button>
        </td>
      </tr>`;
    }).join('');

    bodyEl.innerHTML = `
      ${statusBar}
      <table class="se-insp-table">
        <thead>
          <tr>
            <th>${esc(t('col.metric'))}</th>
            <th class="num">${esc(t('col.meas'))}</th>
            <th class="num">${esc(t('col.se'))}</th>
            <th class="num">${esc(t('col.residual'))}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }

  /* ==================== 页内就地处置模态框（屏蔽 / 预过滤 / 伪量测 / 权重） ==================== */
  function openQuickActionDialog(mode, item) {
    const dlg = document.getElementById('quick-action-dialog');
    if (!dlg || !item) return;
    const titles = {
      suppress: t('qa.title_suppress'),
      prefilter: t('qa.title_prefilter'),
      pseudo: t('qa.title_pseudo'),
      weight: t('qa.title_weight'),
    };
    document.getElementById('qa-title').textContent = titles[mode] || mode;
    document.getElementById('qa-mode').value = mode;
    document.getElementById('qa-dev-type').value = item.device_type || '';
    document.getElementById('qa-dev-idx').value = item.device_idx != null ? String(item.device_idx) : '';
    document.getElementById('qa-dev-name').value = item.device_name || '';
    document.getElementById('qa-metric').value = item.metric || '';
    document.getElementById('qa-unit').value = item.unit || '';
    document.getElementById('qa-target-display').value = `${item.device_type}.${item.device_name}.${item.metric}${item.unit ? ` (${item.unit})` : ''}`;

    const showMinMax = mode === 'prefilter';
    const showVal = mode === 'pseudo';
    const showWeight = mode === 'pseudo' || mode === 'weight';
    document.getElementById('qa-f-min').hidden = !showMinMax;
    document.getElementById('qa-f-max').hidden = !showMinMax;
    document.getElementById('qa-f-val').hidden = !showVal;
    document.getElementById('qa-f-weight').hidden = !showWeight;

    const refVal = item.se_value ?? item.meas_value ?? 0;
    const minEl = document.getElementById('qa-min');
    const maxEl = document.getElementById('qa-max');
    const valEl = document.getElementById('qa-val');
    const wtEl = document.getElementById('qa-weight');
    minEl.value = '';
    maxEl.value = '';
    valEl.value = Number.isFinite(Number(refVal)) ? String(Number(refVal).toFixed(3)) : '0';
    wtEl.value = mode === 'pseudo' ? '0.0001' : (item.weight != null ? String(item.weight) : '1');
    document.getElementById('qa-note').value = '';
    dlg.showModal();
  }

  /* ==================== 2. 交互式原生 SVG 历史曲线 ==================== */
  function renderLineChart(container, config) {
    const { series, xLabels, unit = '', thresholds = [], badPoints = [], emptyText = t('curves.no_data') } = config;
    const validSeries = series.filter((s) => s.values.some((v) => v !== null && v !== undefined && Number.isFinite(v)));
    if (!xLabels.length || !validSeries.length) {
      container.innerHTML = `<div class="se-empty">${esc(emptyText)}</div>`;
      return;
    }

    const rect = container.getBoundingClientRect();
    const width = Math.max(460, Math.floor(rect.width || 720));
    const height = Math.max(170, Math.floor(rect.height || 220));
    const pad = { left: 60, right: 36, top: 16, bottom: 28 };
    const plotW = width - pad.left - pad.right;
    const plotH = height - pad.top - pad.bottom;

    const allVals = validSeries.flatMap((s) => s.values).filter((v) => v !== null && v !== undefined && Number.isFinite(v));
    thresholds.forEach((th) => { if (Number.isFinite(th.value)) allVals.push(th.value); });
    let minV = Math.min(...allVals);
    let maxV = Math.max(...allVals);
    if (config.yMin !== undefined) minV = Math.min(minV, config.yMin);
    if (config.yMax !== undefined) maxV = Math.max(maxV, config.yMax);
    if (Math.abs(maxV - minV) < 1e-9) {
      const span = Math.max(1, Math.abs(maxV) * 0.1);
      minV -= span;
      maxV += span;
    } else {
      const margin = (maxV - minV) * 0.08;
      if (config.yMin === undefined) minV -= margin;
      if (config.yMax === undefined) maxV += margin;
    }

    const n = xLabels.length;
    const xAt = (i) => pad.left + (n === 1 ? plotW / 2 : (plotW * i) / (n - 1));
    const yAt = (v) => pad.top + plotH * (1 - (v - minV) / (maxV - minV));

    const gridColor = cssVar('--chart-grid') || '#E2E8F0';
    const textMuted = cssVar('--text-secondary') || '#64748B';
    const badColor = cssVar('--chart-bad') || '#DC2626';

    const ticks = 4;
    let gridSvg = '';
    for (let i = 0; i <= ticks; i++) {
      const v = minV + ((maxV - minV) * i) / ticks;
      const y = yAt(v);
      gridSvg += `<line x1="${pad.left}" x2="${width - pad.right}" y1="${y}" y2="${y}" stroke="${gridColor}" stroke-dasharray="3 3"/>`;
      gridSvg += `<text x="${pad.left - 8}" y="${y + 4}" text-anchor="end" font-size="11" fill="${textMuted}" class="tabular">${fmtNum(v, 2)}</text>`;
    }
    if (unit) {
      gridSvg += `<text x="${pad.left + 4}" y="${pad.top - 3}" font-size="11" fill="${textMuted}">${esc(unit)}</text>`;
    }

    // X 轴时间刻度（首尾对齐防止边缘裁切）
    const xTickIndices = n <= 5 ? [...Array(n).keys()] : [0, Math.floor((n - 1) * 0.25), Math.floor((n - 1) * 0.5), Math.floor((n - 1) * 0.75), n - 1];
    xTickIndices.forEach((idx, pos) => {
      const x = xAt(idx);
      const anchor = n === 1 ? 'middle' : pos === 0 ? 'start' : pos === xTickIndices.length - 1 ? 'end' : 'middle';
      gridSvg += `<text x="${x}" y="${height - 7}" text-anchor="${anchor}" font-size="11" fill="${textMuted}" class="tabular">${esc(xLabels[idx])}</text>`;
    });

    // 门槛虚线
    let thSvg = '';
    thresholds.forEach((th) => {
      const y = yAt(th.value);
      thSvg += `<line x1="${pad.left}" x2="${width - pad.right}" y1="${y}" y2="${y}" stroke="${th.color || badColor}" stroke-width="1.3" stroke-dasharray="6 4"/>`;
    });

    // 曲线与散点
    let linesSvg = '';
    validSeries.forEach((s) => {
      let d = '';
      let penUp = true;
      let dots = '';
      s.values.forEach((v, i) => {
        if (v === null || v === undefined || !Number.isFinite(v)) {
          penUp = true;
          return;
        }
        const x = xAt(i);
        const y = yAt(v);
        d += `${penUp ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)} `;
        penUp = false;
        if (n <= 40 || s.showDots) {
          dots += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${n === 1 ? 4.5 : 2.6}" fill="${s.color}"/>`;
        }
      });
      linesSvg += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2" ${s.dashed ? 'stroke-dasharray="5 3"' : ''}/>${dots}`;
    });

    // 坏数据红点高亮
    let badSvg = '';
    badPoints.forEach((bp) => {
      if (bp.value === null || bp.value === undefined || !Number.isFinite(bp.value)) return;
      const x = xAt(bp.index);
      const y = yAt(bp.value);
      badSvg += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="5.5" fill="none" stroke="${badColor}" stroke-width="2"/><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3" fill="${badColor}"/>`;
    });

    container.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
        ${gridSvg}
        ${thSvg}
        ${linesSvg}
        ${badSvg}
        <line class="se-crosshair" x1="0" x2="0" y1="${pad.top}" y2="${height - pad.bottom}" stroke="${textMuted}" stroke-width="1" stroke-dasharray="3 3" visibility="hidden"/>
      </svg>
      <div class="se-chart-tip tabular" hidden></div>
    `;

    const svgEl = container.querySelector('svg');
    const cross = container.querySelector('.se-crosshair');
    const tip = container.querySelector('.se-chart-tip');
    let lastIdx = -1;
    if (typeof config.onPointClick === 'function') {
      svgEl.style.cursor = 'pointer';
      svgEl.addEventListener('click', () => {
        if (lastIdx >= 0) config.onPointClick(lastIdx);
      });
    }

    svgEl.addEventListener('mousemove', (e) => {
      const box = svgEl.getBoundingClientRect();
      const relX = ((e.clientX - box.left) / box.width) * width;
      const clamped = Math.max(pad.left, Math.min(width - pad.right, relX));
      const idx = n === 1 ? 0 : Math.round(((clamped - pad.left) / plotW) * (n - 1));
      lastIdx = idx;
      const cx = xAt(idx);
      cross.setAttribute('x1', String(cx));
      cross.setAttribute('x2', String(cx));
      cross.setAttribute('visibility', 'visible');

      const header = config.fullLabels?.[idx] || xLabels[idx];
      const rows = validSeries.map((s) => {
        const val = s.values[idx];
        return `<div><span style="color:${s.color}">●</span> ${esc(s.name)}: <strong>${fmtNum(val, 3)} ${esc(s.unit ?? unit)}</strong></div>`;
      }).join('');
      const badMark = badPoints.some((bp) => bp.index === idx)
        ? `<div style="color:${badColor};font-weight:700">⚠ ${esc(t('legend.bad'))}</div>` : '';
      tip.innerHTML = `<div style="color:${textMuted};margin-bottom:3px">${esc(header)}</div>${rows}${badMark}`;
      tip.hidden = false;
      const tipLeft = e.clientX - box.left + 12;
      const tipTop = Math.max(6, e.clientY - box.top - 24);
      tip.style.left = `${tipLeft + 180 > box.width ? Math.max(6, tipLeft - 195) : tipLeft}px`;
      tip.style.top = `${tipTop}px`;
    });

    svgEl.addEventListener('mouseleave', () => {
      lastIdx = -1;
      cross.setAttribute('visibility', 'hidden');
      tip.hidden = true;
    });
  }

  function renderGlobalCurve() {
    const rows = appState.curves.statsSeries || [];
    const metric = appState.curves.globalMetric;
    const legendEl = document.getElementById('global-chart-legend');
    const hostEl = document.getElementById('global-chart-host');

    const xLabels = rows.map((r) => fmtShortTime(r.calc_time));
    const fullLabels = rows.map((r) => `#${r.run_id} · ${fmtTime(r.calc_time)}`);
    const cSe = cssVar('--chart-se') || '#2563EB';
    const cMeas = cssVar('--chart-meas') || '#D97706';
    const cOk = cssVar('--chart-ok') || '#0D9488';
    const cBad = cssVar('--chart-bad') || '#DC2626';

    let cfg;
    if (metric === 'pass_rate') {
      cfg = {
        xLabels, fullLabels, unit: '%', yMin: 0, yMax: 100,
        series: [{ name: t('curves.pass_rate'), color: cOk, values: rows.map((r) => Number(r.pass_rate || 0) * 100) }],
      };
    } else if (metric === 'residual') {
      cfg = {
        xLabels, fullLabels, unit: '',
        series: [
          { name: t('curves.total_res'), color: cSe, values: rows.map((r) => Number(r.total_residual || 0)) },
          { name: t('curves.max_res'), color: cMeas, dashed: true, values: rows.map((r) => Number(r.residual_inf || 0)) },
        ],
      };
    } else if (metric === 'bad_data') {
      cfg = {
        xLabels, fullLabels, unit: t('unit.count'), yMin: 0,
        series: [{ name: t('curves.bad_data'), color: cBad, values: rows.map((r) => Number(r.bad_data_count || 0)) }],
        badPoints: rows.map((r, i) => (r.bad_data_count > 0 ? { index: i, value: Number(r.bad_data_count) } : null)).filter(Boolean),
      };
    } else {
      cfg = {
        xLabels, fullLabels, unit: 's', yMin: 0,
        series: [
          { name: t('curves.elapsed_total'), color: cSe, values: rows.map((r) => Number(r.elapsed_seconds || 0)) },
          { name: t('curves.elapsed_kernel'), color: cMeas, dashed: true, values: rows.map((r) => Number(r.kernel_seconds || 0)) },
        ],
      };
    }
    cfg.onPointClick = (idx) => {
      const r = rows[idx];
      if (r?.run_id) window.location.href = `/se-flow.html?run_id=${r.run_id}`;
    };

    legendEl.innerHTML = cfg.series.map((s) => `<span><i class="${s.dashed ? 'dashed' : ''}" style="background:${s.color};border-color:${s.color}"></i>${esc(s.name)}</span>`).join('');
    renderLineChart(hostEl, cfg);
  }

  function populatePointSelectors() {
    const pts = appState.curves.pointsCatalog || [];
    const typeSel = document.getElementById('pt-type-select');
    const devSel = document.getElementById('pt-dev-select');
    const measSel = document.getElementById('pt-meas-select');
    const hotSel = document.getElementById('pt-bad-hotspot');

    const types = [...new Set(pts.map((p) => p.device_type))];
    const cur = appState.curves.selectedPoint || pts[0] || null;
    if (cur && !appState.curves.selectedPoint) appState.curves.selectedPoint = cur;

    typeSel.innerHTML = types.map((dt) => `<option value="${esc(dt)}">${esc(devTypeLabel(dt))}</option>`).join('');
    const selType = cur?.device_type && types.includes(cur.device_type) ? cur.device_type : (types[0] || '');
    typeSel.value = selType;

    const devsInType = [...new Set(pts.filter((p) => p.device_type === selType).map((p) => p.device_name))];
    devSel.innerHTML = devsInType.map((dn) => `<option value="${esc(dn)}">${esc(dn)}</option>`).join('');
    const selDev = cur?.device_name && devsInType.includes(cur.device_name) ? cur.device_name : (devsInType[0] || '');
    devSel.value = selDev;

    const measInDev = pts.filter((p) => p.device_type === selType && p.device_name === selDev);
    measSel.innerHTML = measInDev.map((m) => `<option value="${esc(m.meas_type)}">${esc(m.metric || m.meas_type)} (${esc(m.meas_type)}${m.unit ? ' · ' + esc(m.unit) : ''})${m.is_bad ? ' ⚠' : ''}</option>`).join('');
    const selMeas = cur?.meas_type && measInDev.some((m) => m.meas_type === cur.meas_type) ? cur.meas_type : (measInDev[0]?.meas_type || '');
    measSel.value = selMeas;

    if (selType && selDev && selMeas) {
      appState.curves.selectedPoint = { device_type: selType, device_name: selDev, meas_type: selMeas };
    }

    const hotspots = appState.curves.badHistory?.hotspots || [];
    hotSel.innerHTML = `<option value="">${esc(t('curves.bad_hotspot_placeholder'))} (${hotspots.length})</option>` + hotspots.map((h) => (
      `<option value="${esc(h.device_type)}|${esc(h.device_name)}|${esc(h.meas_type)}">⚠ ${esc(h.device_name)} · ${esc(h.meas_type)} (${h.bad_hits})</option>`
    )).join('');
  }

  async function loadSelectedPointSeries() {
    const sp = appState.curves.selectedPoint;
    if (!sp) {
      document.getElementById('point-chart-host').innerHTML = `<div class="se-empty">${esc(t('curves.no_data'))}</div>`;
      return;
    }
    const qs = new URLSearchParams({
      device_type: sp.device_type,
      device_name: sp.device_name,
      meas_type: sp.meas_type,
      limit: String(appState.curves.limit),
    });
    appState.curves.pointSeries = await api(`/api/se/history/point?${qs}`);
    renderPointCurve();
  }

  function renderPointCurve() {
    const data = appState.curves.pointSeries;
    const legendEl = document.getElementById('point-chart-legend');
    const hostEl = document.getElementById('point-chart-host');
    if (!data || !data.points?.length) {
      legendEl.innerHTML = '';
      hostEl.innerHTML = `<div class="se-empty">${esc(t('curves.no_data'))}</div>`;
      return;
    }
    const pts = data.points;
    const xLabels = pts.map((p) => fmtShortTime(p.calc_time));
    const fullLabels = pts.map((p) => `#${p.run_id} · ${fmtTime(p.calc_time)}`);
    const cSe = cssVar('--chart-se') || '#2563EB';
    const cMeas = cssVar('--chart-meas') || '#D97706';
    const cBad = cssVar('--chart-bad') || '#DC2626';
    const mode = appState.curves.pointMode;
    const th = Number(data.bad_threshold || 3.0);

    let cfg;
    if (mode === 'value') {
      cfg = {
        xLabels, fullLabels, unit: data.unit || '',
        series: [
          { name: t('legend.meas'), color: cMeas, values: pts.map((p) => p.meas_value) },
          { name: t('legend.se'), color: cSe, values: pts.map((p) => p.se_value) },
        ],
        badPoints: pts.map((p, i) => (p.is_bad ? { index: i, value: p.meas_value } : null)).filter(Boolean),
      };
    } else if (mode === 'residual') {
      cfg = {
        xLabels, fullLabels, unit: data.unit || '',
        series: [{ name: t('curves.point_residual'), color: cSe, values: pts.map((p) => p.residual) }],
        thresholds: [{ value: 0, color: cssVar('--text-secondary') }],
        badPoints: pts.map((p, i) => (p.is_bad ? { index: i, value: p.residual } : null)).filter(Boolean),
      };
    } else {
      cfg = {
        xLabels, fullLabels, unit: 'σ',
        series: [{ name: t('curves.norm_residual'), color: cSe, values: pts.map((p) => p.normalized_residual) }],
        thresholds: [{ value: th, color: cBad }, { value: -th, color: cBad }],
        badPoints: pts.map((p, i) => (p.is_bad ? { index: i, value: p.normalized_residual } : null)).filter(Boolean),
      };
    }

    const extraLegend = mode === 'norm'
      ? `<span><i class="dashed" style="border-color:${cBad}"></i>${esc(t('curves.threshold', { v: th }))}</span>`
      : `<span><i class="dot" style="background:${cBad}"></i>${esc(t('legend.bad'))}</span>`;
    legendEl.innerHTML = `<strong>${esc(data.device_name)} · ${esc(data.metric || data.meas_type)}</strong>`
      + cfg.series.map((s) => `<span><i style="background:${s.color}"></i>${esc(s.name)}</span>`).join('')
      + extraLegend;

    // 同步单点快捷处置栏（定位潮流图 + 屏蔽 / 预过滤 / 权重）
    const actsEl = document.getElementById('pt-curve-actions');
    if (actsEl) {
      const catItem = (appState.curves.pointsCatalog || []).find(
        (p) => p.device_type === data.device_type && p.device_name === data.device_name && p.meas_type === data.meas_type,
      );
      const lastPt = pts[pts.length - 1] || {};
      const metric = data.metric || catItem?.metric || '';
      const qaPayload = esc(JSON.stringify({
        device_type: data.device_type,
        device_idx: catItem?.device_idx ?? null,
        device_name: data.device_name,
        metric,
        unit: data.unit || '',
        meas_value: lastPt.meas_value,
        se_value: lastPt.se_value,
      }));
      const flowHref = `/se-flow.html?device_type=${encodeURIComponent(data.device_type)}&device_name=${encodeURIComponent(data.device_name)}`;
      actsEl.innerHTML = `
        <a class="se-btn mini se-link-btn" href="${flowHref}">${esc(t('action.locate'))}</a>
        ${metric ? `<button type="button" class="se-btn mini" data-qa-mode="suppress" data-qa="${qaPayload}">${esc(t('action.suppress'))}</button>` : ''}
        ${metric ? `<button type="button" class="se-btn mini" data-qa-mode="prefilter" data-qa="${qaPayload}">${esc(t('action.prefilter'))}</button>` : ''}
        ${metric ? `<button type="button" class="se-btn mini" data-qa-mode="weight" data-qa="${qaPayload}">${esc(t('action.weight'))}</button>` : ''}
      `;
    }

    cfg.onPointClick = (idx) => {
      const p = pts[idx];
      if (p?.run_id) window.location.href = `/se-flow.html?run_id=${p.run_id}`;
    };
    renderLineChart(hostEl, cfg);
  }

  async function loadCurvesTab() {
    const limit = appState.curves.limit;
    const [statsSeries, pointsData, badHistory] = await Promise.all([
      api(`/api/se/history/stats?limit=${limit}`),
      api('/api/se/history/points'),
      api(`/api/se/history/bad-data?limit=${limit}`),
    ]);
    appState.curves.statsSeries = statsSeries;
    appState.curves.pointsCatalog = pointsData.points || [];
    appState.curves.badHistory = badHistory;
    populatePointSelectors();
    renderGlobalCurve();
    await loadSelectedPointSeries();
  }

  /* ==================== 3. 设备对比宽表（支持历史断面与残差视角） ==================== */
  async function loadDevicesTab() {
    const qs = new URLSearchParams({
      type: appState.devices.type || '',
      q: appState.devices.q || '',
      bad_only: appState.devices.badOnly ? '1' : '0',
    });
    if (appState.selectedRunId) qs.set('run_id', appState.selectedRunId);
    const data = await api(`/api/se/devices?${qs}`);
    appState.devices.data = data;
    appState.devices.type = data.device_type;

    const sel = document.getElementById('dev-type-select');
    if (sel) {
      sel.innerHTML = (data.available_types || []).map((item) => {
        const warn = item.bad_device_count ? ` ⚠${item.bad_device_count}` : '';
        return `<option value="${esc(item.device_type)}">${esc(devTypeLabel(item.device_type))} (${item.count})${warn}</option>`;
      }).join('');
      sel.value = data.device_type;
    }
    document.querySelectorAll('#dev-mode-seg .seg').forEach((b) => b.classList.toggle('active', b.dataset.dmode === appState.devices.mode));

    const cntEl = document.getElementById('dev-count-summary');
    if (cntEl) cntEl.textContent = t('devices.summary', { n: data.rows.length });

    const metrics = data.metrics || [];
    const measMap = data.meas_type_map || {};
    const wrap = document.getElementById('dev-table-wrap');
    if (!wrap) return;
    if (!data.rows.length) {
      wrap.innerHTML = `<div class="se-empty">${esc(t('empty.no_match'))}</div>`;
      return;
    }

    const isDelta = appState.devices.mode === 'delta';
    const headCols = isDelta
      ? metrics.map((m) => `<th class="num">${esc(m)} Δ</th>`).join('')
      : metrics.map((m) => `<th class="num">${esc(m)} Meas</th><th class="num">${esc(m)} SE</th>`).join('');
    const bodyRows = data.rows.map((row) => {
      const badSet = new Set(row.bad_metrics || []);
      const cells = metrics.map((m) => {
        const isBad = badSet.has(m);
        const mtype = measMap[m] || '';
        const mv = row[`${m}_meas`];
        const sv = row[`${m}_se`];
        if (isDelta) {
          const d = (mv != null && sv != null && Number.isFinite(Number(mv)) && Number.isFinite(Number(sv)))
            ? (Number(mv) - Number(sv))
            : null;
          const cls = isBad ? 'num tabular cell-bad se-clickable-cell' : 'num tabular se-clickable-cell';
          const tip = `M: ${fmtNum(mv, 3)} / SE: ${fmtNum(sv, 3)}`;
          const txt = d == null ? '—' : `${d >= 0 ? '+' : ''}${fmtNum(d, 3)}`;
          return `<td class="${cls}" data-open-curve="${esc(data.device_type)}|${esc(row.name)}|${esc(mtype)}" title="${esc(tip)}">${txt}</td>`;
        }
        const cls = isBad ? 'num tabular cell-bad se-clickable-cell' : 'num tabular se-clickable-cell';
        return `<td class="${cls}" data-open-curve="${esc(data.device_type)}|${esc(row.name)}|${esc(mtype)}" title="${esc(t('action.curve'))}">${fmtNum(mv)}</td><td class="${cls}" data-open-curve="${esc(data.device_type)}|${esc(row.name)}|${esc(mtype)}" title="${esc(t('action.curve'))}">${fmtNum(sv)}</td>`;
      }).join('');
      const devId = `${data.device_type}-${row.idx}`;
      return `<tr class="${row.has_bad ? 'row-bad' : ''}">
        <td class="tabular">${row.idx}</td>
        <td class="se-sticky-left se-cell-ellipsis" title="${esc(row.name)}"><strong>${esc(row.name)}</strong></td>
        ${cells}
        <td class="se-sticky-right"><button type="button" class="se-btn mini" data-locate-dev="${esc(devId)}">${esc(t('action.locate'))}</button></td>
      </tr>`;
    }).join('');

    wrap.innerHTML = `
      <table class="se-data-table">
        <thead><tr><th>${esc(t('col.idx'))}</th><th class="se-sticky-left">${esc(t('col.device'))}</th>${headCols}<th class="se-sticky-right">${esc(t('col.actions'))}</th></tr></thead>
        <tbody>${bodyRows}</tbody>
      </table>
    `;
  }

  /* ==================== 4. 量测与坏数据明细 + 设备对比 + 母线平衡与可观测 ==================== */
  function syncMeasBatchBar() {
    const bar = document.getElementById('meas-batch-bar');
    const cntEl = document.getElementById('meas-batch-cnt');
    if (!bar || !cntEl) return;
    const n = appState.meas.selected.size;
    bar.hidden = n === 0 || appState.meas.subTab !== 'list';
    cntEl.textContent = `${n}`;
  }

  async function loadMeasurementsTab() {
    const m = appState.meas;
    const isList = m.subTab === 'list';
    const isDevices = m.subTab === 'devices';
    const isBalance = m.subTab === 'balance';
    const listCtrl = document.getElementById('meas-list-controls');
    const devCtrl = document.getElementById('meas-devices-controls');
    const balCtrl = document.getElementById('meas-balance-controls');
    const measWrap = document.getElementById('meas-table-wrap');
    const measPager = document.getElementById('meas-pager');
    const devWrap = document.getElementById('dev-table-wrap');
    const balWrap = document.getElementById('bal-table-wrap');
    const exportBtn = document.getElementById('btn-export-meas');
    if (listCtrl) listCtrl.hidden = !isList;
    if (devCtrl) devCtrl.hidden = !isDevices;
    if (balCtrl) balCtrl.hidden = !isBalance;
    if (measWrap) measWrap.hidden = !isList;
    if (measPager) measPager.hidden = !isList;
    if (devWrap) devWrap.hidden = !isDevices;
    if (balWrap) balWrap.hidden = !isBalance;
    if (exportBtn) exportBtn.hidden = !isList;
    document.querySelectorAll('#meas-subtab-seg .seg').forEach((b) => b.classList.toggle('active', b.dataset.msub === m.subTab));
    syncMeasBatchBar();
    if (isDevices) {
      await loadDevicesTab();
      return;
    }
    if (isBalance) {
      await loadBalanceTab();
      return;
    }

    const reqId = ++m.reqSeq;
    const qs = new URLSearchParams({
      source: m.source,
      device_type: m.devType,
      q: m.q,
      sort: m.sort,
      direction: m.direction,
      high_residual_only: m.highResOnly ? '1' : '0',
      limit: String(m.size),
      offset: String(m.page * m.size),
    });
    if (appState.selectedRunId) qs.set('run_id', appState.selectedRunId);
    const data = await api(`/api/se/measurements?${qs}`);
    if (reqId !== m.reqSeq) return; // 丢弃过期的并发搜索响应
    const total = data.meta?.total || 0;
    const pages = Math.max(1, Math.ceil(total / m.size));
    if (m.page >= pages && m.page > 0) {
      m.page = pages - 1;
      return loadMeasurementsTab();
    }
    m.data = data;

    // 填充/刷新设备类筛选下拉（切换语言时同步更新）
    const dtSel = document.getElementById('meas-devtype-select');
    if (dtSel) {
      const types = Object.keys(appState.overview?.device_counts || {});
      dtSel.innerHTML = `<option value="">${esc(t('devtype.all'))}</option>` + types.map((dt) => `<option value="${esc(dt)}">${esc(devTypeLabel(dt))}</option>`).join('');
      dtSel.value = m.devType;
    }

    // 同步排序下拉与方向按钮
    const sortSel = document.getElementById('meas-sort-select');
    if (sortSel && sortSel.value !== m.sort) sortSel.value = m.sort;
    const dirBtn = document.getElementById('btn-meas-dir');
    if (dirBtn) dirBtn.textContent = m.direction === 'asc' ? '↑' : '↓';

    // 更新来源微芯片数量徽章
    const counts = data.counts || {};
    document.querySelectorAll('#meas-source-seg .seg').forEach((btn) => {
      const key = btn.dataset.msrc;
      const base = t(key === 'bad_data' ? 'meas.bad' : `meas.${key}`);
      const c = key === 'all' ? counts.total : counts[key];
      btn.classList.toggle('active', key === m.source);
      btn.innerHTML = `${esc(base)}${c !== undefined ? `<span class="cnt tabular">${c}</span>` : ''}`;
    });
    const hrBtn = document.getElementById('btn-meas-high-res');
    if (hrBtn) {
      hrBtn.classList.toggle('active', m.highResOnly);
      const hc = counts.high_residual;
      hrBtn.innerHTML = `${esc(t('meas.high_res'))}${hc !== undefined ? `<span class="cnt tabular">${hc}</span>` : ''}`;
    }

    const thSort = (colKey, labelKey, numCls = '') => {
      const active = m.sort === colKey;
      const arrow = active ? (m.direction === 'asc' ? '▲' : '▼') : '';
      return `<th class="${numCls} se-th-sort ${active ? 'is-sorted' : ''}" data-meas-sort="${colKey}">${esc(t(labelKey))}${arrow ? `<span class="sort-arrow">${arrow}</span>` : ''}</th>`;
    };

    const wrap = document.getElementById('meas-table-wrap');
    if (!data.rows.length) {
      wrap.innerHTML = `<div class="se-empty">${esc(t('empty.no_match'))}</div>`;
    } else {
      const selectableRows = data.rows.filter((r) => r.metric);
      const allChecked = selectableRows.length > 0 && selectableRows.every((r) => m.selected.has(`${r.device_type}|${r.device_name}|${r.metric}`));
      wrap.innerHTML = `
        <table class="se-data-table">
          <thead>
            <tr>
              <th style="width:28px;text-align:center"><input type="checkbox" id="meas-check-all" ${allChecked ? 'checked' : ''} aria-label="Select all"></th>
              ${thSort('meas_id', 'col.idx')}
              ${thSort('device_name', 'col.device')}
              <th>${esc(t('col.metric'))}</th>
              ${thSort('meas_value', 'col.meas', 'num')}
              ${thSort('se_value', 'col.se', 'num')}
              ${thSort('abs_residual', 'col.residual', 'num')}
              ${thSort('abs_norm_residual', 'col.norm_res', 'num')}
              <th>${esc(t('col.source'))}</th>
              <th class="se-sticky-right">${esc(t('col.actions'))}</th>
            </tr>
          </thead>
          <tbody>
            ${data.rows.map((r) => {
              const devId = r.device_idx != null ? `${r.device_type}-${r.device_idx}` : '';
              const srcKey = r.is_bad ? 'meas.bad' : (r.source === 'normal' ? 'meas.normal' : r.source === 'prefiltered' ? 'meas.prefiltered' : 'meas.pseudo');
              const pillCls = r.is_bad ? 'bad' : r.source === 'normal' ? 'ok' : 'neutral';
              const rowKey = `${r.device_type}|${r.device_name}|${r.metric}`;
              const checked = r.metric && m.selected.has(rowKey);
              const qaPayload = esc(JSON.stringify({
                device_type: r.device_type || '',
                device_idx: r.device_idx,
                device_name: r.device_name || '',
                metric: r.metric || '',
                unit: r.unit || '',
                meas_value: r.meas_value,
                se_value: r.se_value,
                weight: r.weight,
              }));
              const normWarn = r.is_bad || (r.normalized_residual != null && Math.abs(Number(r.normalized_residual)) >= 2.0);
              return `<tr class="${r.is_bad ? 'row-bad' : ''}">
                <td style="text-align:center">${r.metric ? `<input type="checkbox" class="meas-row-chk" data-row-key="${esc(rowKey)}" data-qa="${qaPayload}" ${checked ? 'checked' : ''}>` : ''}</td>
                <td class="tabular">${r.meas_id}</td>
                <td class="se-cell-ellipsis" title="${esc(r.device_name)} (${esc(r.device_type)})"><strong>${esc(r.device_name)}</strong> <small class="se-muted">${esc(r.device_type)}</small></td>
                <td>${esc(r.metric || r.meas_type)} <small class="se-muted">${esc(r.unit || '')}</small></td>
                <td class="num tabular">${fmtNum(r.meas_value, 3)}</td>
                <td class="num tabular">${fmtNum(r.se_value, 3)}</td>
                <td class="num tabular ${normWarn ? 'cell-bad' : ''}">${fmtNum(r.residual, 3)}</td>
                <td class="num tabular ${normWarn ? 'cell-bad' : ''}">${fmtNum(r.normalized_residual, 3)}</td>
                <td><span class="se-pill ${pillCls}">${esc(t(srcKey))}</span></td>
                <td class="se-sticky-right">
                  ${devId ? `<button type="button" class="se-btn mini" data-locate-dev="${esc(devId)}">${esc(t('action.locate'))}</button>` : ''}
                  <button type="button" class="se-btn mini" data-open-curve="${esc(r.device_type)}|${esc(r.device_name)}|${esc(r.meas_type)}">${esc(t('action.curve'))}</button>
                  ${r.metric ? `<button type="button" class="se-btn mini" data-qa-mode="prefilter" data-qa="${qaPayload}">${esc(t('action.prefilter'))}</button>` : ''}
                  ${r.metric ? `<button type="button" class="se-btn mini" data-qa-mode="suppress" data-qa="${qaPayload}">${esc(t('action.suppress'))}</button>` : ''}
                  ${r.metric ? `<button type="button" class="se-btn mini" data-qa-mode="pseudo" data-qa="${qaPayload}">${esc(t('action.pseudo'))}</button>` : ''}
                  ${r.metric ? `<button type="button" class="se-btn mini" data-qa-mode="weight" data-qa="${qaPayload}">${esc(t('action.weight'))}</button>` : ''}
                </td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      `;
    }

    document.getElementById('meas-pager').innerHTML = `
      <button type="button" class="se-btn mini" id="btn-meas-prev" ${m.page <= 0 ? 'disabled' : ''}>${esc(t('pager.prev'))}</button>
      <span class="tabular">${esc(t('pager.info', { page: m.page + 1, pages, total }))}</span>
      <button type="button" class="se-btn mini" id="btn-meas-next" ${m.page >= pages - 1 ? 'disabled' : ''}>${esc(t('pager.next'))}</button>
    `;
  }

  async function loadBalanceTab() {
    const data = await api('/api/se/balance');
    appState.balance.data = data;
    renderBalanceTable();
  }

  function renderBalanceTable() {
    const data = appState.balance.data;
    const wrap = document.getElementById('bal-table-wrap');
    const meta = document.getElementById('bal-summary-meta');
    if (!data || !wrap) return;
    const s = data.summary || {};
    const pu = data.units?.p_unit || 'kW';
    const qu = data.units?.q_unit || 'kvar';
    if (meta) {
      meta.textContent = t('bal.summary', {
        total: s.bus_total ?? 0,
        imb: s.imbalanced_count ?? 0,
        low: s.low_obs_count ?? 0,
        max: `${fmtNum(s.max_dp_meas, 2)} ${pu}`,
      });
    }
    const q = (appState.balance.q || '').trim().toLowerCase();
    const rows = (data.rows || []).filter((r) => {
      if (appState.balance.domain !== 'all' && r.domain !== appState.balance.domain) return false;
      if (appState.balance.onlyImb && !r.imbalanced) return false;
      if (q && !`${r.idx} ${r.name} ${r.device_type}`.toLowerCase().includes(q)) return false;
      return true;
    });
    if (!rows.length) {
      wrap.innerHTML = `<div class="se-empty">${esc(t('empty.no_match'))}</div>`;
      return;
    }
    wrap.innerHTML = `
      <table class="se-data-table">
        <thead>
          <tr>
            <th>${esc(t('bal.bus'))}</th>
            <th>${esc(t('bal.domain'))}</th>
            <th class="num">${esc(t('bal.v_meas_se'))}</th>
            <th class="num">${esc(t('bal.p_in'))} (${esc(pu)})</th>
            <th class="num">${esc(t('bal.p_out'))} (${esc(pu)})</th>
            <th class="num">${esc(t('bal.dp_meas'))} (${esc(pu)})</th>
            <th class="num">${esc(t('bal.dp_se'))} (${esc(pu)})</th>
            <th class="num">${esc(t('bal.dq_meas'))} (${esc(qu)})</th>
            <th class="num">${esc(t('bal.meas_cnt'))}</th>
            <th>${esc(t('bal.status'))}</th>
            <th class="se-sticky-right">${esc(t('col.actions'))}</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((r) => {
            const stCls = r.imbalanced ? 'bad' : r.low_obs ? 'warn' : 'ok';
            const stLbl = r.imbalanced ? t('bal.st_imb') : r.low_obs ? t('bal.st_lowobs') : t('bal.st_ok');
            const vMetric = r.domain === 'AC' ? 'uab' : 'u';
            const qaPayload = esc(JSON.stringify({
              device_type: r.device_type,
              device_idx: r.idx,
              device_name: r.name,
              metric: vMetric,
              unit: data.units?.u_unit || 'V',
              meas_value: r.v_meas,
              se_value: r.v_se,
            }));
            return `<tr class="${r.imbalanced ? 'row-bad' : ''}">
              <td class="se-cell-ellipsis" title="${esc(r.name)}"><strong>${esc(r.name)}</strong> <small class="se-muted">#${r.idx}</small></td>
              <td><span class="se-pill neutral">${esc(r.domain)}</span></td>
              <td class="num tabular">${fmtNum(r.v_meas, 2)} / ${fmtNum(r.v_se, 2)}</td>
              <td class="num tabular">${fmtNum(r.p_in_meas, 2)}</td>
              <td class="num tabular">${fmtNum(r.p_out_meas, 2)}</td>
              <td class="num tabular ${r.imbalanced ? 'cell-bad' : ''}">${fmtNum(r.dp_meas, 2)}</td>
              <td class="num tabular">${fmtNum(r.dp_se, 3)}</td>
              <td class="num tabular">${fmtNum(r.dq_meas, 2)}</td>
              <td class="num tabular">${r.meas_cnt}</td>
              <td><span class="se-pill ${stCls}">${esc(stLbl)}</span></td>
              <td class="se-sticky-right">
                <button type="button" class="se-btn mini" data-locate-dev="${esc(r.dev_id)}">${esc(t('action.locate'))}</button>
                <button type="button" class="se-btn mini" data-qa-mode="pseudo" data-qa="${qaPayload}">${esc(t('action.pseudo'))}</button>
              </td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    `;
  }

  /* ==================== 5. 算法参数 (pas_se_para) + 量测权重 + 试算对比 ==================== */
  async function loadParamsTab() {
    const isWeights = appState.paramsSubTab === 'weights';
    const form = document.getElementById('se-params-form');
    const wtWrap = document.getElementById('weights-table-wrap');
    const wtTools = document.getElementById('weights-toolbar-right');
    if (form) form.hidden = isWeights;
    if (wtWrap) wtWrap.hidden = !isWeights;
    if (wtTools) wtTools.hidden = !isWeights;
    ['btn-params-reset', 'btn-params-save', 'btn-params-trial'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.hidden = isWeights;
    });
    if (isWeights) {
      const bar = document.getElementById('params-trial-bar');
      if (bar) bar.hidden = true;
    }
    document.querySelectorAll('#params-subtab-seg .seg').forEach((b) => b.classList.toggle('active', b.dataset.psub === appState.paramsSubTab));
    if (isWeights) {
      await loadWeightsTab();
      return;
    }

    const params = await api('/api/se/params');
    appState.params = params;
    document.getElementById('params-updated-at').textContent = params.updated_at ? fmtTime(params.updated_at) : '—';
    let html = '';
    PARAM_SCHEMA.forEach((grp) => {
      html += `<div class="se-param-group-title">${esc(t(grp.group))}</div>`;
      grp.fields.forEach((f) => {
        const label = f.label[appState.lang] || f.label['zh-CN'];
        const val = params[f.key];
        if (f.type === 'bool') {
          html += `
            <label class="se-field">
              <span>${esc(label)}</span>
              <select name="${esc(f.key)}">
                <option value="0" ${Number(val) === 0 ? 'selected' : ''}>${esc(t('bool.off'))}</option>
                <option value="1" ${Number(val) === 1 ? 'selected' : ''}>${esc(t('bool.on'))}</option>
              </select>
            </label>
          `;
        } else {
          html += `
            <label class="se-field">
              <span>${esc(label)}</span>
              <input class="tabular" type="number" name="${esc(f.key)}" value="${esc(val)}"
                ${f.min !== undefined ? `min="${f.min}"` : ''}
                ${f.max !== undefined ? `max="${f.max}"` : ''}
                step="${f.step || '1'}" required>
            </label>
          `;
        }
      });
    });
    form.innerHTML = html;
  }

  async function saveParams() {
    const form = document.getElementById('se-params-form');
    const fd = new FormData(form);
    const payload = {};
    PARAM_SCHEMA.forEach((grp) => {
      grp.fields.forEach((f) => {
        const raw = fd.get(f.key);
        if (raw === null) return;
        payload[f.key] = f.type === 'float' ? Number(raw) : parseInt(String(raw), 10);
      });
    });
    appState.params = await api('/api/se/params', payload);
    notify(t('params.saved'));
    await loadParamsTab();
  }

  async function saveAndTrialParams() {
    const btn = document.getElementById('btn-params-trial');
    const bar = document.getElementById('params-trial-bar');
    if (btn) btn.disabled = true;
    try {
      const beforeOv = await api('/api/se/overview');
      const before = beforeOv?.latest || null;
      await saveParams();
      notify(t('params.trial_running'));
      await api('/api/actions/trigger', { task: 'se' });
      const afterOv = await api('/api/se/overview');
      const after = afterOv?.latest || null;
      appState.overview = afterOv;
      if (bar && after) {
        const bIter = before?.iterations ?? '—';
        const bPass = before?.pass_rate != null ? `${(before.pass_rate * 100).toFixed(2)}%` : '—';
        const aPass = after.pass_rate != null ? `${(after.pass_rate * 100).toFixed(2)}%` : '—';
        const bBad = before?.bad_data_count ?? '—';
        const bObj = before?.objective != null ? fmtNum(before.objective, 4) : '—';
        const bEl = before?.elapsed_seconds != null ? `${Number(before.elapsed_seconds).toFixed(3)}s` : '—';
        bar.innerHTML = `
          <strong class="tag">${esc(t('trial.title'))}</strong>
          <span class="tabular">${esc(t('trial.iters'))}: ${bIter} → <b>${after.iterations}</b></span>
          <span class="tabular">${esc(t('trial.pass'))}: ${bPass} → <b>${aPass}</b></span>
          <span class="tabular">${esc(t('trial.bad'))}: ${bBad} → <b>${after.bad_data_count}</b></span>
          <span class="tabular">${esc(t('trial.obj'))}: ${bObj} → <b>${fmtNum(after.objective, 4)}</b></span>
          <span class="tabular">${esc(t('trial.elapsed'))}: ${bEl} → <b>${Number(after.elapsed_seconds || 0).toFixed(3)}s</b></span>
          <button type="button" class="se-btn mini" id="btn-trial-close">×</button>`;
        bar.hidden = false;
        document.getElementById('btn-trial-close')?.addEventListener('click', () => { bar.hidden = true; });
      }
      notify(t('notice.se_done', { id: after?.run_id || '' }));
    } catch (err) {
      notify(err.message, true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function ensureCatalog() {
    if (!appState.catalog) {
      appState.catalog = await api('/api/se/model-catalog');
    }
    return appState.catalog;
  }

  async function loadWeightsTab() {
    const [cat, rows] = await Promise.all([
      ensureCatalog(),
      api(`/api/se/weights?device_type=${encodeURIComponent(appState.weights.type)}&q=${encodeURIComponent(appState.weights.q)}`),
    ]);
    appState.weights.rows = rows || [];
    const typeFilter = document.getElementById('wt-type-filter');
    if (typeFilter) {
      const types = Object.keys(cat.solver_metrics || {});
      typeFilter.innerHTML = `<option value="">${esc(t('devtype.all'))}</option>` + types.map((dt) => `<option value="${esc(dt)}">${esc(devTypeLabel(dt))}</option>`).join('');
      typeFilter.value = appState.weights.type;
    }
    const wrap = document.getElementById('weights-table-wrap');
    if (!wrap) return;
    if (!appState.weights.rows.length) {
      wrap.innerHTML = `<div class="se-empty">${esc(t('empty.no_match'))}</div>`;
      return;
    }
    wrap.innerHTML = `
      <table class="se-data-table">
        <thead>
          <tr>
            <th>#</th>
            <th>${esc(t('wt.scope'))}</th>
            <th>${esc(t('wt.dev_type'))}</th>
            <th>${esc(t('wt.dev_name'))}</th>
            <th>${esc(t('wt.metric'))}</th>
            <th class="num">${esc(t('qa.weight'))}</th>
            <th>${esc(t('wt.status'))}</th>
            <th>${esc(t('qa.note'))}</th>
            <th class="se-sticky-right">${esc(t('col.actions'))}</th>
          </tr>
        </thead>
        <tbody>
          ${appState.weights.rows.map((r) => `
            <tr>
              <td class="tabular">${r.id}</td>
              <td><span class="se-pill neutral">${esc(t(r.scope === 'device' ? 'wt.scope_dev' : 'wt.scope_type'))}</span></td>
              <td>${esc(devTypeLabel(r.device_type))}</td>
              <td><strong>${esc(r.device_name)}</strong></td>
              <td class="tabular">${esc(r.metric)}</td>
              <td class="num tabular"><strong>${esc(r.weight)}</strong></td>
              <td><span class="se-pill ${r.enabled ? 'ok' : 'neutral'}">${esc(t(r.enabled ? 'bool.on' : 'bool.off'))}</span></td>
              <td class="se-cell-ellipsis" title="${esc(r.note)}">${esc(r.note || '—')}</td>
              <td class="se-sticky-right">
                <button type="button" class="se-btn mini" data-wt-act="edit" data-wt-id="${r.id}">${esc(t('action.edit'))}</button>
                <button type="button" class="se-btn mini" data-wt-act="toggle" data-wt-id="${r.id}">${esc(t(r.enabled ? 'bool.off' : 'bool.on'))}</button>
                <button type="button" class="se-btn mini danger-ghost" data-wt-act="del" data-wt-id="${r.id}">${esc(t('action.delete'))}</button>
              </td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  }

  async function openWeightDialog(rule) {
    const dlg = document.getElementById('weight-dialog');
    if (!dlg) return;
    const cat = await ensureCatalog();
    const dtSel = document.getElementById('fw-dev-type');
    const types = Object.keys(cat.solver_metrics || {});
    dtSel.innerHTML = types.map((dt) => `<option value="${esc(dt)}">${esc(devTypeLabel(dt))}</option>`).join('');

    const syncWeightForm = (selectedDev, selectedMetric) => {
      const scope = document.getElementById('fw-scope').value;
      const dt = dtSel.value;
      document.getElementById('fw-dev-row').hidden = scope !== 'device';
      const devSel = document.getElementById('fw-dev-name');
      const devs = (cat.devices || {})[dt] || [];
      devSel.innerHTML = devs.map((d) => `<option value="${esc(d.name)}" data-idx="${d.idx}">${esc(d.name)} (#${d.idx})</option>`).join('');
      if (selectedDev) devSel.value = selectedDev;
      const mSel = document.getElementById('fw-metric');
      const metrics = Object.keys((cat.solver_metrics || {})[dt] || {});
      mSel.innerHTML = metrics.map((mk) => `<option value="${esc(mk)}">${esc(mk)}</option>`).join('');
      if (selectedMetric) mSel.value = selectedMetric;
    };

    document.getElementById('fw-id').value = rule?.id || '';
    document.getElementById('fw-scope').value = rule?.scope || 'device_type';
    dtSel.value = rule?.device_type || types[0] || 'ACNode';
    document.getElementById('fw-weight').value = rule?.weight ?? 1;
    document.getElementById('fw-enabled').value = String(rule?.enabled ?? 1);
    document.getElementById('fw-note').value = rule?.note || '';
    syncWeightForm(rule?.device_name, rule?.metric);

    document.getElementById('fw-scope').onchange = () => syncWeightForm();
    dtSel.onchange = () => syncWeightForm();
    dlg.showModal();
  }

  /* ==================== 6. 运行与调度 ==================== */
  async function loadRunsTab() {
    const [ov, cfg] = await Promise.all([api('/api/se/overview'), api('/api/config')]);
    appState.overview = ov;
    const seCfg = cfg.tasks?.se || { period_seconds: 60, enabled: true };
    const form = document.getElementById('se-schedule-form');
    form.elements.period_seconds.value = seCfg.period_seconds;
    form.elements.enabled.checked = Boolean(seCfg.enabled);

    const rows = ov.recent_runs || [];
    const wrap = document.getElementById('runs-table-wrap');
    if (!rows.length) {
      wrap.innerHTML = `<div class="se-empty">${esc(t('curves.no_data'))}</div>`;
      return;
    }
    wrap.innerHTML = `
      <table class="se-data-table">
        <thead>
          <tr>
            <th>${esc(t('col.run'))}</th>
            <th>${esc(t('col.status'))}</th>
            <th>${esc(t('col.time'))}</th>
            <th class="num">${esc(t('col.pass_rate'))}</th>
            <th class="num">${esc(t('col.bad_count'))}</th>
            <th class="num">${esc(t('col.elapsed'))}</th>
            <th>${esc(t('col.actions'))}</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((r) => `
            <tr>
              <td class="tabular"><a href="/se-logs.html?run_id=${r.run_id}">#${r.run_id}</a></td>
              <td><span class="se-pill ${r.status === 'succeeded' ? 'ok' : r.status === 'failed' ? 'bad' : 'warn'}">${esc(t(`status.${r.status}`))}</span></td>
              <td class="tabular">${fmtTime(r.started_at)}</td>
              <td class="num tabular">${r.pass_rate != null ? (Number(r.pass_rate) * 100).toFixed(2) + '%' : '—'}</td>
              <td class="num tabular ${r.bad_data_count > 0 ? 'cell-bad' : ''}">${r.bad_data_count ?? '—'}</td>
              <td class="num tabular">${r.elapsed_seconds != null ? Number(r.elapsed_seconds).toFixed(3) : '—'}</td>
              <td><a class="se-btn mini se-link-btn" href="/se-logs.html?run_id=${r.run_id}">${esc(t('link.run_log'))}</a></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  /* ==================== CSV 导出 ==================== */
  function exportCsv(filename, headers, rows) {
    const cell = (v) => {
      let s = String(v ?? '');
      if (typeof v === 'string' && /^\s*[=+\-@\t\r]/.test(s)) s = `'${s}`;
      return `"${s.replaceAll('"', '""')}"`;
    };
    const csv = [headers.map(cell), ...rows.map((r) => r.map(cell))].map((r) => r.join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob(['\ufeff', csv], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  /* ==================== 视图切换与全量刷新 ==================== */
  async function switchView(viewName) {
    appState.view = viewName;
    document.querySelectorAll('#se-view-tabs .se-tab').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.view === viewName);
    });
    document.querySelectorAll('#se-workspace .se-panel').forEach((panel) => {
      panel.classList.toggle('active', panel.dataset.panel === viewName);
    });

    if (viewName === 'topology') {
      await ensureSvgLoaded();
      renderSvgBindings();
      renderTopoBadPanel();
      if (appState.selectedDevId && appState._pendingFocusDev) {
        appState._pendingFocusDev = false;
        focusSvgDevice(appState.selectedDevId);
      } else {
        selectTopologyDevice(appState.selectedDevId);
      }
    } else if (viewName === 'curves') {
      await loadCurvesTab();
    } else if (viewName === 'devices') {
      await loadDevicesTab();
    } else if (viewName === 'measurements') {
      await loadMeasurementsTab();
    } else if (viewName === 'params') {
      await loadParamsTab();
    } else if (viewName === 'runs') {
      await loadRunsTab();
    }
  }

  async function jumpToPointCurve(deviceType, deviceName, measType) {
    if (SINGLE_VIEW_PAGE && appState.view !== 'curves') {
      const qs = new URLSearchParams({ device_type: deviceType, device_name: deviceName, meas_type: measType });
      window.location.href = `/se-curves.html?${qs.toString()}`;
      return;
    }
    appState.curves.selectedPoint = { device_type: deviceType, device_name: deviceName, meas_type: measType };
    await switchView('curves');
  }

  function populateRunSelect() {
    const sel = document.getElementById('se-run-select');
    if (!sel) return;
    const runs = appState.convergedRuns || [];
    const opts = [`<option value="">${esc(t('snap.latest'))}</option>`];
    runs.forEach((r) => {
      const ts = fmtTime(r.calc_time || r.started_at).slice(5);
      const pr = r.pass_rate != null ? `${(Number(r.pass_rate) * 100).toFixed(2)}%` : '—';
      const bad = r.bad_data_count != null ? ` · B${r.bad_data_count}` : '';
      opts.push(`<option value="${r.run_id}">${esc(t('snap.history'))} #${r.run_id} · ${esc(ts)} · ${pr}${bad}</option>`);
    });
    sel.innerHTML = opts.join('');
    sel.value = appState.selectedRunId || '';
    sel.classList.toggle('is-history', Boolean(appState.selectedRunId));
  }

  async function refreshAll() {
    try {
      const qp = new URLSearchParams(window.location.search);
      if (!appState._urlInitDone) {
        appState._urlInitDone = true;
        const qSub = qp.get('sub');
        if (appState.view === 'measurements' && (qSub === 'balance' || qSub === 'devices')) {
          appState.meas.subTab = qSub;
        }
        if ((appState.view === 'topology' || appState.view === 'measurements') && qp.get('run_id')) {
          appState.selectedRunId = qp.get('run_id');
        }
      }
      const needRuns = appState.view === 'topology' || appState.view === 'measurements';
      const topoUrl = appState.selectedRunId
        ? `/api/se/topology-values?run_id=${encodeURIComponent(appState.selectedRunId)}`
        : '/api/se/topology-values';
      const [overview, topology, converged, balData] = await Promise.all([
        api('/api/se/overview'),
        appState.view === 'topology' ? api(topoUrl) : Promise.resolve(null),
        needRuns ? api('/api/se/runs/converged?limit=30').catch(() => []) : Promise.resolve(null),
        appState.view === 'topology' ? api('/api/se/balance').catch(() => null) : Promise.resolve(null),
      ]);
      appState.overview = overview;
      if (balData) appState.balance.data = balData;
      if (Array.isArray(converged)) {
        appState.convergedRuns = converged;
        populateRunSelect();
      }
      if (topology) {
        appState.topology = topology;
        // 支持跨页通过 ?dev_id=... 或 ?device_type=...&device_name=... 跳转定位
        if (!appState.selectedDevId) {
          const qDevId = qp.get('dev_id');
          const qType = qp.get('device_type');
          const qName = qp.get('device_name');
          if (qDevId && topology.devices?.[qDevId]) {
            appState.selectedDevId = qDevId;
            appState._pendingFocusDev = true;
          } else if (qType && qName) {
            const matched = Object.values(topology.devices || {}).find(
              (d) => d.device_type === qType && d.name === qName,
            );
            if (matched) {
              appState.selectedDevId = matched.dev_id;
              appState._pendingFocusDev = true;
            }
          }
        }
      }
      if (appState.view === 'curves' && !appState.curves.selectedPoint) {
        const dt = qp.get('device_type');
        const dn = qp.get('device_name');
        const mt = qp.get('meas_type');
        if (dt && dn && mt) appState.curves.selectedPoint = { device_type: dt, device_name: dn, meas_type: mt };
      }
      renderOverviewKPIs();
      if (appState.view === 'topology') populateDeviceJumpSelect();
      await switchView(appState.view);
    } catch (err) {
      notify(err.message, true);
    }
  }

  async function pollServiceStatus() {
    try {
      const st = await api('/api/status');
      const dot = document.getElementById('service-dot');
      const text = document.getElementById('service-state');
      text.textContent = st.daemon_running ? t('service.daemon_on') : t('service.daemon_off');
      dot.style.background = st.daemon_running ? '#10B981' : '#F59E0B';

      const busy = [...(st.active_tasks || []), ...(st.pending_tasks || [])].includes('se');
      const runBtn = document.getElementById('btn-run-se');
      runBtn.disabled = busy;
      runBtn.textContent = busy ? t('action.running_se') : t('action.run_se');

      if (appState.watchingJobId) {
        const job = (st.jobs || []).find((j) => j.job_id === appState.watchingJobId)
          || await api(`/api/jobs/${appState.watchingJobId}`).catch(() => null);
        if (job && ['succeeded', 'failed'].includes(job.status)) {
          appState.watchingJobId = null;
          if (job.status === 'succeeded') {
            notify(t('notice.se_done', { id: job.run_id || '' }));
            await refreshAll();
          } else {
            notify(t('notice.se_failed', { msg: job.error_message || '' }), true);
          }
        }
      }
    } catch (_) {
      document.getElementById('service-state').textContent = t('service.offline');
    }
  }

  /* ==================== 事件绑定（按当前页面 DOM 安全挂载） ==================== */
  function on(id, event, handler) {
    const el = document.getElementById(id);
    if (el) el.addEventListener(event, handler);
  }

  function bindEvents() {
    const langSel = document.getElementById('lang-select');
    if (langSel) langSel.value = appState.lang;
    on('lang-select', 'change', async (e) => {
      appState.lang = e.target.value;
      localStorage.setItem('se_lang', appState.lang);
      localStorage.setItem('pas_se_lang', appState.lang);
      applyI18n();
      renderOverviewKPIs();
      populateRunSelect();
      if (appState.view === 'topology') populateDeviceJumpSelect();
      await switchView(appState.view);
      await pollServiceStatus();
    });

    // 历史收敛断面选择器（潮流图 / 全量测分析）
    on('se-run-select', 'change', async (e) => {
      appState.selectedRunId = e.target.value || '';
      e.target.classList.toggle('is-history', Boolean(appState.selectedRunId));
      appState.meas.selected.clear();
      appState.meas.page = 0;
      if (appState.view === 'topology') {
        try {
          const url = appState.selectedRunId
            ? `/api/se/topology-values?run_id=${encodeURIComponent(appState.selectedRunId)}`
            : '/api/se/topology-values';
          appState.topology = await api(url);
          populateDeviceJumpSelect();
          renderSvgBindings();
          renderTopoBadPanel();
          selectTopologyDevice(appState.selectedDevId);
        } catch (err) {
          notify(err.message, true);
        }
      } else if (appState.view === 'measurements') {
        await loadMeasurementsTab();
      }
    });

    on('theme-select', 'change', (e) => {
      appState.theme = e.target.value;
      localStorage.setItem('se_theme', appState.theme);
      localStorage.setItem('pas_se_theme', appState.theme);
      applyTheme();
      if (appState.view === 'topology') renderSvgBindings();
      if (appState.view === 'curves') { renderGlobalCurve(); renderPointCurve(); }
    });

    on('btn-refresh', 'click', refreshAll);

    on('btn-run-se', 'click', async () => {
      try {
        const res = await api('/api/actions/submit', { task: 'se' });
        if (res.accepted) {
          appState.watchingJobId = res.job_id;
          notify(t('notice.se_submitted'));
        }
        await pollServiceStatus();
      } catch (err) {
        notify(err.message, true);
      }
    });

    on('se-view-tabs', 'click', (e) => {
      const btn = e.target.closest('.se-tab');
      if (btn) switchView(btn.dataset.view);
    });

    // 潮流图工具栏
    on('svg-display-mode', 'change', (e) => {
      appState.svgDisplayMode = e.target.value;
      renderSvgBindings();
    });
    on('svg-device-jump', 'change', (e) => {
      if (e.target.value) focusSvgDevice(e.target.value);
    });
    on('btn-topo-imb-overlay', 'click', () => {
      appState.topoImbOverlay = !appState.topoImbOverlay;
      renderSvgBindings();
    });
    on('topo-side-seg', 'click', (e) => {
      const btn = e.target.closest('.seg');
      if (!btn) return;
      appState.topoSideTab = btn.dataset.tside || 'bad';
      if (appState.topoSideTab === 'imb' && !appState.topoImbOverlay) {
        appState.topoImbOverlay = true;
        renderSvgBindings();
      }
      renderTopoBadPanel();
    });
    on('btn-svg-zoom-in', 'click', () => zoomSvgAt(1.25));
    on('btn-svg-zoom-out', 'click', () => zoomSvgAt(0.8));
    on('btn-svg-fit', 'click', fitSvgToViewport);

    // 历史曲线控件
    on('global-curve-metric', 'click', (e) => {
      const btn = e.target.closest('.seg');
      if (!btn) return;
      appState.curves.globalMetric = btn.dataset.gmetric;
      document.querySelectorAll('#global-curve-metric .seg').forEach((b) => b.classList.toggle('active', b === btn));
      renderGlobalCurve();
    });
    on('curve-limit', 'change', async (e) => {
      appState.curves.limit = Number(e.target.value);
      await loadCurvesTab();
    });
    on('pt-type-select', 'change', async (e) => {
      appState.curves.selectedPoint = { device_type: e.target.value, device_name: '', meas_type: '' };
      populatePointSelectors();
      await loadSelectedPointSeries();
    });
    on('pt-dev-select', 'change', async (e) => {
      appState.curves.selectedPoint = {
        device_type: document.getElementById('pt-type-select').value,
        device_name: e.target.value,
        meas_type: '',
      };
      populatePointSelectors();
      await loadSelectedPointSeries();
    });
    on('pt-meas-select', 'change', async (e) => {
      appState.curves.selectedPoint = {
        device_type: document.getElementById('pt-type-select').value,
        device_name: document.getElementById('pt-dev-select').value,
        meas_type: e.target.value,
      };
      await loadSelectedPointSeries();
    });
    on('pt-bad-hotspot', 'change', async (e) => {
      if (!e.target.value) return;
      const [dt, dn, mt] = e.target.value.split('|');
      appState.curves.selectedPoint = { device_type: dt, device_name: dn, meas_type: mt };
      populatePointSelectors();
      await loadSelectedPointSeries();
    });
    on('point-curve-mode', 'click', (e) => {
      const btn = e.target.closest('.seg');
      if (!btn) return;
      appState.curves.pointMode = btn.dataset.pmode;
      document.querySelectorAll('#point-curve-mode .seg').forEach((b) => b.classList.toggle('active', b === btn));
      renderPointCurve();
    });
    on('btn-pt-export-csv', 'click', () => {
      const d = appState.curves.pointSeries;
      if (!d?.points?.length) return;
      const cols = ['run_id', 'calc_time', 'meas_value', 'se_value', 'residual', 'normalized_residual', 'is_bad'];
      exportCsv(
        `se-point-${d.device_type}-${d.device_name}-${d.metric || d.meas_type}.csv`,
        cols,
        d.points.map((p) => cols.map((c) => p[c] ?? '')),
      );
    });

    // 设备对比控件
    on('dev-type-select', 'change', (e) => {
      appState.devices.type = e.target.value;
      loadDevicesTab();
    });
    on('dev-mode-seg', 'click', (e) => {
      const btn = e.target.closest('.seg');
      if (!btn) return;
      appState.devices.mode = btn.dataset.dmode || 'compare';
      loadDevicesTab();
    });
    let devSearchTimer;
    on('dev-search-input', 'input', (e) => {
      appState.devices.q = e.target.value;
      clearTimeout(devSearchTimer);
      devSearchTimer = setTimeout(() => loadDevicesTab(), 200);
    });
    on('dev-bad-only', 'change', (e) => {
      appState.devices.badOnly = e.target.checked;
      loadDevicesTab();
    });
    on('btn-export-devices', 'click', () => {
      const d = appState.devices.data;
      if (!d?.rows?.length) return;
      const cols = ['idx', 'name', ...d.metrics.flatMap((m) => [`${m}_meas`, `${m}_se`])];
      exportCsv(`se-dev-${d.device_type}.csv`, cols, d.rows.map((r) => cols.map((c) => r[c] ?? '')));
    });

    // 量测明细子标签、筛选、排序、批量操作与后端全量导出
    on('meas-subtab-seg', 'click', (e) => {
      const btn = e.target.closest('.seg');
      if (!btn) return;
      appState.meas.subTab = btn.dataset.msub || 'list';
      loadMeasurementsTab();
    });
    on('bal-domain-filter', 'change', (e) => {
      appState.balance.domain = e.target.value;
      renderBalanceTable();
    });
    on('btn-bal-only-imb', 'click', (e) => {
      appState.balance.onlyImb = !appState.balance.onlyImb;
      e.currentTarget.classList.toggle('active', appState.balance.onlyImb);
      renderBalanceTable();
    });
    let balSearchTimer;
    on('bal-search-input', 'input', (e) => {
      appState.balance.q = e.target.value;
      clearTimeout(balSearchTimer);
      balSearchTimer = setTimeout(() => renderBalanceTable(), 200);
    });
    on('meas-source-seg', 'click', (e) => {
      const btn = e.target.closest('.seg');
      if (!btn) return;
      appState.meas.source = btn.dataset.msrc;
      appState.meas.page = 0;
      document.querySelectorAll('#meas-source-seg .seg').forEach((b) => b.classList.toggle('active', b === btn));
      loadMeasurementsTab();
    });
    on('btn-meas-high-res', 'click', () => {
      appState.meas.highResOnly = !appState.meas.highResOnly;
      appState.meas.page = 0;
      loadMeasurementsTab();
    });
    on('meas-devtype-select', 'change', (e) => {
      appState.meas.devType = e.target.value;
      appState.meas.page = 0;
      loadMeasurementsTab();
    });
    on('meas-sort-select', 'change', (e) => {
      appState.meas.sort = e.target.value;
      appState.meas.direction = (e.target.value === 'meas_id' || e.target.value === 'device_name') ? 'asc' : 'desc';
      appState.meas.page = 0;
      loadMeasurementsTab();
    });
    on('btn-meas-dir', 'click', () => {
      appState.meas.direction = appState.meas.direction === 'asc' ? 'desc' : 'asc';
      appState.meas.page = 0;
      loadMeasurementsTab();
    });
    let measSearchTimer;
    on('meas-search-input', 'input', (e) => {
      appState.meas.q = e.target.value;
      appState.meas.page = 0;
      clearTimeout(measSearchTimer);
      measSearchTimer = setTimeout(() => loadMeasurementsTab(), 200);
    });
    on('meas-table-wrap', 'change', (e) => {
      if (e.target.id === 'meas-check-all') {
        const checked = e.target.checked;
        document.querySelectorAll('#meas-table-wrap .meas-row-chk').forEach((chk) => {
          chk.checked = checked;
          const key = chk.dataset.rowKey;
          if (checked) {
            try { appState.meas.selected.set(key, JSON.parse(chk.dataset.qa || '{}')); } catch (_) {}
          } else {
            appState.meas.selected.delete(key);
          }
        });
        syncMeasBatchBar();
      } else if (e.target.classList.contains('meas-row-chk')) {
        const key = e.target.dataset.rowKey;
        if (e.target.checked) {
          try { appState.meas.selected.set(key, JSON.parse(e.target.dataset.qa || '{}')); } catch (_) {}
        } else {
          appState.meas.selected.delete(key);
        }
        const allChks = [...document.querySelectorAll('#meas-table-wrap .meas-row-chk')];
        const allEl = document.getElementById('meas-check-all');
        if (allEl) allEl.checked = allChks.length > 0 && allChks.every((c) => c.checked);
        syncMeasBatchBar();
      }
    });
    on('btn-batch-clear', 'click', () => {
      appState.meas.selected.clear();
      document.querySelectorAll('#meas-table-wrap .meas-row-chk, #meas-check-all').forEach((c) => { c.checked = false; });
      syncMeasBatchBar();
    });
    on('btn-batch-suppress', 'click', async () => {
      const items = [...appState.meas.selected.values()].map((it) => ({
        device_type: it.device_type,
        device_idx: it.device_idx,
        device_name: it.device_name,
        metric: it.metric,
        action: 'suppress',
        enabled: 1,
        note: 'batch suppress',
      }));
      if (!items.length) return;
      try {
        const res = await api('/api/se/bad/policies/batch', { items });
        appState.meas.selected.clear();
        syncMeasBatchBar();
        notify(t('batch.done', { n: Array.isArray(res) ? res.length : (res?.saved ?? items.length) }));
        await loadMeasurementsTab();
      } catch (err) {
        notify(err.message, true);
      }
    });
    on('btn-batch-prefilter', 'click', async () => {
      const items = [...appState.meas.selected.values()].map((it) => ({
        scope: 'device',
        device_type: it.device_type,
        device_idx: it.device_idx,
        device_name: it.device_name,
        metric: it.metric,
        rule_type: 'force_filter',
        enabled: 1,
        note: 'batch prefilter',
      }));
      if (!items.length) return;
      try {
        const res = await api('/api/se/prefilter/rules/batch', { items });
        appState.meas.selected.clear();
        syncMeasBatchBar();
        notify(t('batch.done', { n: Array.isArray(res) ? res.length : (res?.saved ?? items.length) }));
        await loadMeasurementsTab();
      } catch (err) {
        notify(err.message, true);
      }
    });
    on('btn-export-meas', 'click', () => {
      const m = appState.meas;
      const qs = new URLSearchParams({
        source: m.source,
        device_type: m.devType,
        q: m.q,
        sort: m.sort,
        direction: m.direction,
        high_residual_only: m.highResOnly ? '1' : '0',
      });
      if (appState.selectedRunId) qs.set('run_id', appState.selectedRunId);
      window.location.href = `/api/se/measurements/export?${qs.toString()}`;
    });

    // 页内就地处置模态框（屏蔽 / 预过滤 / 伪量测 / 权重）
    const qaDialog = document.getElementById('quick-action-dialog');
    on('btn-qa-cancel', 'click', () => qaDialog?.close());
    on('qa-form', 'submit', async (e) => {
      e.preventDefault();
      const mode = document.getElementById('qa-mode').value;
      const device_type = document.getElementById('qa-dev-type').value;
      const idxRaw = document.getElementById('qa-dev-idx').value;
      const device_idx = idxRaw !== '' ? Number(idxRaw) : null;
      const device_name = document.getElementById('qa-dev-name').value;
      const metric = document.getElementById('qa-metric').value;
      const unit = document.getElementById('qa-unit').value;
      const note = document.getElementById('qa-note').value.trim();
      try {
        if (mode === 'suppress') {
          await api('/api/se/bad/policies', {
            device_type,
            device_idx,
            device_name,
            metric,
            action: 'suppress',
            enabled: 1,
            note,
          });
        } else if (mode === 'prefilter') {
          const minRaw = document.getElementById('qa-min').value.trim();
          const maxRaw = document.getElementById('qa-max').value.trim();
          const hasRange = minRaw !== '' || maxRaw !== '';
          await api('/api/se/prefilter/rules', {
            scope: 'device',
            device_type,
            device_idx,
            device_name,
            metric,
            rule_type: hasRange ? 'range' : 'force_filter',
            min_value: minRaw !== '' ? Number(minRaw) : null,
            max_value: maxRaw !== '' ? Number(maxRaw) : null,
            enabled: 1,
            note,
          });
        } else if (mode === 'pseudo') {
          await api('/api/se/pseudo/meas', {
            device_type,
            device_idx,
            device_name,
            metric,
            unit,
            meas_value: Number(document.getElementById('qa-val').value),
            meas_weight: Number(document.getElementById('qa-weight').value || 0.0001),
            enabled: 1,
            note,
          });
        } else if (mode === 'weight') {
          await api('/api/se/weights', {
            scope: 'device',
            device_type,
            device_idx,
            device_name,
            metric,
            weight: Number(document.getElementById('qa-weight').value || 1),
            enabled: 1,
            note,
          });
        }
        qaDialog?.close();
        notify(t('qa.saved'));
      } catch (err) {
        notify(err.message, true);
      }
    });

    // 快捷键：'/' 聚焦搜索框，'Esc' 清空当前搜索框
    document.addEventListener('keydown', (e) => {
      const tag = (document.activeElement?.tagName || '').toLowerCase();
      if (e.key === '/' && tag !== 'input' && tag !== 'textarea' && tag !== 'select') {
        const box = (appState.meas.subTab === 'balance' ? document.getElementById('bal-search-input') : null)
          || document.getElementById('meas-search-input')
          || document.getElementById('dev-search-input')
          || document.getElementById('wt-search-input');
        if (box && !box.hidden) {
          e.preventDefault();
          box.focus();
          box.select();
        }
      } else if (e.key === 'Escape' && document.activeElement?.type === 'search' && document.activeElement.value) {
        document.activeElement.value = '';
        document.activeElement.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });

    // 通用高危模态确认框（统一承接参数重置与权重删除，默认聚焦取消按钮）
    const confirmDialog = document.getElementById('confirm-dialog');
    let pendingConfirmFn = null;
    const openConfirmModal = ({ title, desc, okText, onConfirm }) => {
      if (!confirmDialog) return;
      const tEl = document.getElementById('confirm-title');
      const dEl = document.getElementById('confirm-desc');
      const okEl = document.getElementById('btn-confirm-ok');
      if (tEl && title) tEl.textContent = title;
      if (dEl && desc) dEl.textContent = desc;
      if (okEl && okText) okEl.textContent = okText;
      pendingConfirmFn = onConfirm;
      confirmDialog.showModal();
      document.getElementById('btn-confirm-cancel')?.focus();
    };
    on('btn-confirm-cancel', 'click', () => {
      pendingConfirmFn = null;
      confirmDialog?.close();
    });
    on('btn-confirm-ok', 'click', async () => {
      const fn = pendingConfirmFn;
      pendingConfirmFn = null;
      confirmDialog?.close();
      if (typeof fn === 'function') await fn();
    });

    // 算法参数保存、试算对比、重置与量测权重子标签
    on('params-subtab-seg', 'click', (e) => {
      const btn = e.target.closest('.seg');
      if (!btn) return;
      appState.paramsSubTab = btn.dataset.psub || 'para';
      loadParamsTab();
    });
    on('btn-params-save', 'click', async () => {
      try { await saveParams(); } catch (err) { notify(err.message, true); }
    });
    on('btn-params-trial', 'click', saveAndTrialParams);
    on('btn-params-reset', 'click', () => {
      openConfirmModal({
        title: t('modal.reset_title'),
        desc: t('modal.reset_desc'),
        okText: t('action.confirm_reset'),
        onConfirm: async () => {
          try {
            await api('/api/se/params/reset', { action: 'reset' });
            notify(t('params.reset_done'));
            await loadParamsTab();
          } catch (err) {
            notify(err.message, true);
          }
        },
      });
    });

    // 量测权重工具栏、表格委派与编辑弹窗
    on('wt-type-filter', 'change', (e) => {
      appState.weights.type = e.target.value;
      loadWeightsTab();
    });
    let wtSearchTimer;
    on('wt-search-input', 'input', (e) => {
      appState.weights.q = e.target.value;
      clearTimeout(wtSearchTimer);
      wtSearchTimer = setTimeout(() => loadWeightsTab(), 200);
    });
    on('btn-add-weight', 'click', () => openWeightDialog(null));
    const wtDialog = document.getElementById('weight-dialog');
    on('btn-wt-cancel', 'click', () => wtDialog?.close());
    on('weight-form', 'submit', async (e) => {
      e.preventDefault();
      const id = document.getElementById('fw-id').value;
      const scope = document.getElementById('fw-scope').value;
      const devSel = document.getElementById('fw-dev-name');
      const opt = devSel?.selectedOptions?.[0];
      const payload = {
        scope,
        device_type: document.getElementById('fw-dev-type').value,
        device_name: scope === 'device' ? (devSel?.value || '') : '*',
        device_idx: scope === 'device' && opt?.dataset?.idx ? Number(opt.dataset.idx) : null,
        metric: document.getElementById('fw-metric').value,
        weight: Number(document.getElementById('fw-weight').value),
        enabled: Number(document.getElementById('fw-enabled').value),
        note: document.getElementById('fw-note').value.trim(),
      };
      try {
        if (id) {
          await api(`/api/se/weights/${id}`, payload, 'PUT');
        } else {
          await api('/api/se/weights', payload, 'POST');
        }
        wtDialog?.close();
        notify(t('wt.saved'));
        await loadWeightsTab();
      } catch (err) {
        notify(err.message, true);
      }
    });
    on('weights-table-wrap', 'click', async (e) => {
      const btn = e.target.closest('[data-wt-act]');
      if (!btn) return;
      const act = btn.dataset.wtAct;
      const wid = Number(btn.dataset.wtId);
      const row = appState.weights.rows.find((r) => Number(r.id) === wid);
      if (!row) return;
      if (act === 'edit') {
        await openWeightDialog(row);
      } else if (act === 'toggle') {
        try {
          await api(`/api/se/weights/${wid}`, { ...row, enabled: row.enabled ? 0 : 1 }, 'PUT');
          notify(t('wt.saved'));
          await loadWeightsTab();
        } catch (err) {
          notify(err.message, true);
        }
      } else if (act === 'del') {
        openConfirmModal({
          title: t('wt.dlg_title'),
          desc: `${t('wt.del_confirm')} (${row.device_type}.${row.device_name}.${row.metric})`,
          okText: t('action.delete'),
          onConfirm: async () => {
            try {
              await api(`/api/se/weights/${wid}`, null, 'DELETE');
              notify(t('wt.deleted'));
              await loadWeightsTab();
            } catch (err) {
              notify(err.message, true);
            }
          },
        });
      }
    });

    // 调度保存与启停（兼容）
    on('se-schedule-form', 'submit', async (e) => {
      e.preventDefault();
      try {
        const f = e.target;
        await api('/api/schedules/se', {
          period_seconds: Number(f.elements.period_seconds.value),
          enabled: Boolean(f.elements.enabled.checked),
        });
        notify(t('sched.saved'));
        await pollServiceStatus();
      } catch (err) {
        notify(err.message, true);
      }
    });
    on('btn-daemon-start', 'click', async () => {
      try { await api('/api/actions/daemon/start', {}); await pollServiceStatus(); } catch (err) { notify(err.message, true); }
    });
    on('btn-daemon-stop', 'click', async () => {
      try { await api('/api/actions/daemon/stop', {}); await pollServiceStatus(); } catch (err) { notify(err.message, true); }
    });

    // 全局委派点击（坏数据定位、就地处置、强合/强分、跨页曲线跳转、分页）
    document.addEventListener('click', async (e) => {
      const qaBtn = e.target.closest('[data-qa-mode]');
      if (qaBtn) {
        try {
          const item = JSON.parse(qaBtn.dataset.qa || '{}');
          openQuickActionDialog(qaBtn.dataset.qaMode, item);
        } catch (err) {
          notify(err.message, true);
        }
        return;
      }
      const statBtn = e.target.closest('[data-force-stat]');
      if (statBtn) {
        const [dt, idxStr, dn, valStr] = (statBtn.dataset.forceStat || '').split('|');
        if (dt && dn) {
          try {
            await api('/api/se/pseudo/stat', {
              device_type: dt,
              device_idx: idxStr !== '' ? Number(idxStr) : null,
              device_name: dn,
              stat_value: Number(valStr),
              enabled: 1,
              note: 'flow quick force',
            });
            notify(t('qa.saved'));
          } catch (err) {
            notify(err.message, true);
          }
        }
        return;
      }
      const focusBtn = e.target.closest('[data-focus-dev]');
      if (focusBtn) {
        const devId = focusBtn.dataset.focusDev;
        if (devId) focusSvgDevice(devId);
        return;
      }
      const locateBtn = e.target.closest('[data-locate-dev]');
      if (locateBtn) {
        const devId = locateBtn.dataset.locateDev;
        if (SINGLE_VIEW_PAGE && appState.view !== 'topology') {
          window.location.href = `/se-flow.html?dev_id=${encodeURIComponent(devId)}`;
          return;
        }
        await switchView('topology');
        focusSvgDevice(devId);
        return;
      }
      const curveEl = e.target.closest('[data-open-curve],[data-jump-curve]');
      if (curveEl) {
        const raw = curveEl.dataset.openCurve || curveEl.dataset.jumpCurve || '';
        const [dt, dn, mt] = raw.split('|');
        if (dt && dn && mt) await jumpToPointCurve(dt, dn, mt);
        return;
      }
      const sortTh = e.target.closest('th[data-meas-sort]');
      if (sortTh) {
        const col = sortTh.dataset.measSort;
        if (appState.meas.sort === col) {
          appState.meas.direction = appState.meas.direction === 'asc' ? 'desc' : 'asc';
        } else {
          appState.meas.sort = col;
          appState.meas.direction = (col === 'meas_id' || col === 'device_name') ? 'asc' : 'desc';
        }
        appState.meas.page = 0;
        await loadMeasurementsTab();
        return;
      }
      if (e.target.id === 'btn-meas-prev' && appState.meas.page > 0) {
        appState.meas.page -= 1;
        await loadMeasurementsTab();
      } else if (e.target.id === 'btn-meas-next') {
        appState.meas.page += 1;
        await loadMeasurementsTab();
      }
    });

    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (appState.view === 'curves') {
          renderGlobalCurve();
          renderPointCurve();
        }
      }, 150);
    });
  }

  /* ==================== 侧边栏可拖拽分割条与折叠隐藏 ==================== */
  function initSidebarSplitter() {
    if (typeof window.initSidebarSplitter === 'function') {
      window.initSidebarSplitter();
      return;
    }
    const shell = document.querySelector('.app-shell');
    const sidebar = shell?.querySelector('.sidebar');
    if (!shell || !sidebar || shell.querySelector('.sidebar-resizer')) return;
    const W_KEY = 'pas_sidebar_width';
    const C_KEY = 'pas_sidebar_collapsed';
    const MIN_W = 160;
    const MAX_W = 340;
    const COLLAPSE_THRESHOLD = 100;
    let savedWidth = Math.min(MAX_W, Math.max(MIN_W, Number(localStorage.getItem(W_KEY)) || 214));
    let collapsed = localStorage.getItem(C_KEY) === '1';
    const resizer = document.createElement('div');
    resizer.className = 'sidebar-resizer';
    resizer.setAttribute('role', 'separator');
    resizer.setAttribute('aria-orientation', 'vertical');
    resizer.title = '拖动调整宽度 / 双击隐藏或展开';
    const toggleBtn = document.createElement('button');
    toggleBtn.type = 'button';
    toggleBtn.className = 'sidebar-toggle-btn';
    resizer.appendChild(toggleBtn);
    sidebar.insertAdjacentElement('afterend', resizer);
    const emitResize = () => {
      window.dispatchEvent(new Event('resize'));
      setTimeout(() => window.dispatchEvent(new Event('resize')), 180);
    };
    const applyState = (notifyResize = false) => {
      sidebar.classList.toggle('is-collapsed', collapsed);
      resizer.classList.toggle('is-collapsed', collapsed);
      if (!collapsed) {
        sidebar.style.width = `${savedWidth}px`;
        sidebar.style.flexBasis = `${savedWidth}px`;
      }
      toggleBtn.textContent = collapsed ? '›' : '‹';
      toggleBtn.title = collapsed ? '展开左侧目录树' : '隐藏左侧目录树';
      toggleBtn.setAttribute('aria-label', toggleBtn.title);
      localStorage.setItem(C_KEY, collapsed ? '1' : '0');
      localStorage.setItem(W_KEY, String(Math.round(savedWidth)));
      if (notifyResize) emitResize();
    };
    toggleBtn.addEventListener('pointerdown', (e) => e.stopPropagation());
    toggleBtn.addEventListener('click', (e) => { e.stopPropagation(); collapsed = !collapsed; applyState(true); });
    resizer.addEventListener('dblclick', () => { collapsed = !collapsed; applyState(true); });
    let dragging = false; let moved = false; let startX = 0;
    resizer.addEventListener('pointerdown', (e) => {
      if (e.button !== 0 || e.target === toggleBtn) return;
      dragging = true; moved = false; startX = e.clientX;
      resizer.setPointerCapture(e.pointerId);
      sidebar.classList.add('is-resizing'); resizer.classList.add('is-active');
      document.body.classList.add('sidebar-resizing');
    });
    resizer.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      if (Math.abs(e.clientX - startX) > 3) moved = true;
      if (e.clientX < COLLAPSE_THRESHOLD) {
        collapsed = true; sidebar.classList.add('is-collapsed'); resizer.classList.add('is-collapsed'); toggleBtn.textContent = '›';
      } else {
        collapsed = false; savedWidth = Math.min(MAX_W, Math.max(MIN_W, e.clientX));
        sidebar.classList.remove('is-collapsed'); resizer.classList.remove('is-collapsed');
        sidebar.style.width = `${savedWidth}px`; sidebar.style.flexBasis = `${savedWidth}px`; toggleBtn.textContent = '‹';
      }
    });
    const finishDrag = (e) => {
      if (!dragging) return;
      dragging = false;
      if (e && resizer.hasPointerCapture?.(e.pointerId)) resizer.releasePointerCapture(e.pointerId);
      sidebar.classList.remove('is-resizing'); resizer.classList.remove('is-active');
      document.body.classList.remove('sidebar-resizing');
      if (!moved && collapsed) collapsed = false;
      applyState(true);
    };
    resizer.addEventListener('pointerup', finishDrag);
    resizer.addEventListener('pointercancel', finishDrag);
    applyState(false);
  }

  /* ==================== 启动初始化 ==================== */
  initSidebarSplitter();
  applyTheme();
  applyI18n();
  initSvgInteractions();
  bindEvents();
  refreshAll();
  pollServiceStatus();
  setInterval(() => {
    if (!document.hidden) pollServiceStatus();
  }, 3000);
})();
