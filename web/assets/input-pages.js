/* Dedicated measurement and limit pages share the PAS API and page shell. */
const inputState={kind:'',tab:'live',q:'',view:'all',page:0,rows:[],total:0,options:[]};
const inputReasons={point_definition_changed:'测点定义已变更',semantic_mismatch:'量测类型不匹配',bad_quality:'质量无效',stale:'数据过期',no_timestamp:'未采集',future_timestamp:'时间异常',mapping_disabled:'关联停用',device_mismatch:'设备不匹配',source_unavailable:'采集库不可用',point_missing:'测点不存在',invalid_value:'数值无效',configuration_changed:'配置已变更',device_inactive:'设备已移除',source_mismatch:'源库不匹配'};
const inputSize=()=>Math.max(1,Math.min(7,Math.floor((innerHeight-(innerWidth<700?620:520))/52)));
const inputMetric=(label,value)=>`<span>${esc(label)}<strong>${esc(value)}</strong></span>`;
async function inputPage(kind){
  inputState.kind=kind;
  const query=new URLSearchParams({q:inputState.q,view:inputState.view,page:inputState.page,size:inputSize()});
  const data=(await api(`/api/inputs/${kind}?${query}`)).data;
  inputState.rows=data.rows;inputState.total=data.total;
  const measurements=kind==='measurements';
  const stats=measurements?inputMetric('量测总数',data.stats.total)+inputMetric('有效量测',data.stats.valid)+inputMetric('SE配置',data.stats.se_enabled)+inputMetric('SE有效',data.stats.se_valid):inputMetric('限值总数',data.stats.total)+inputMetric('已启用',data.stats.enabled);
  const filters=measurements?[['all','全部量测'],['se','SE量测'],['valid','有效'],['invalid','无效']]:[['all','全部限值'],['enabled','启用'],['disabled','停用']];
  const buttons=measurements?'<button class="mini" data-input-action="sync">同步目录</button><button class="primary" data-input-action="refresh">立即采集</button>':'<button class="mini" data-input-action="seed-limits">补充模型限值</button><button class="primary" data-input-action="new-limit">新增限值</button>';
  const tabHtml=measurements?`<div class="tabs">${[['live','实时量测'],['mapping','SCADA关联'],['se','SE参数']].map(([key,label])=>`<button class="tab ${inputState.tab===key?'active':''}" data-input-tab="${key}">${label}</button>`).join('')}</div>`:'';
  const rows=data.rows.map(row=>{
    const identity=measurements?row.measurement_id:row.limit_id;
    const device=`${row.device_name} · ${row.model_table}:${row.model_idx}`;
    let value,action;
    if(!measurements){
      value=`${row.lower_value==null?'不限':number(row.lower_value)} ～ ${row.upper_value==null?'不限':number(row.upper_value)} ${esc(row.unit)}<small>${row.enabled?'启用':'停用'} · ${esc(row.field)}</small>`;
      action=`<button class="mini" data-input-edit="limit" data-id="${identity}">编辑</button><button class="mini" data-input-toggle="${identity}">${row.enabled?'停用':'启用'}</button>`;
    }else if(inputState.tab==='mapping'){
      value=`RTU ${row.rtu_id} / ${row.kind.toUpperCase()} ${row.pnt_no}<small>${row.mapping_enabled?'启用':'停用'} · ×${row.scale} + ${row.offset}</small>`;
      action=`<button class="mini" data-input-edit="mapping" data-id="${identity}">关联</button>`;
    }else if(inputState.tab==='se'){
      value=`${esc(row.se_type||'不参与SE')}<small>${row.se_enabled?'启用':'停用'} · 权重 ${row.weight}</small>`;
      action=row.se_type?`<button class="mini" data-input-edit="measurement" data-id="${identity}">参数</button>`:'—';
    }else{
      value=`${number(row.value)} ${esc(row.unit)}<small class="${row.valid?'':'input-invalid'}">${row.valid?'有效':esc(inputReasons[row.reason]||'未采集')}</small>`;
      action=`<button class="mini" data-input-detail="${identity}">详情</button>`;
    }
    return `<tr><td tabindex="0" data-value="${esc(device+'\n'+(row.name||row.source||''))}">${esc(row.device_name)}<small>${esc(measurements?row.metric:row.model_table)}</small></td><td>${value}</td><td class="input-row-actions">${action}</td></tr>`;
  }).join('');
  return `${tabHtml}<div class="analysis-body"><section class="card full-panel input-panel"><div class="diagnostic-metrics input-stats">${stats}</div><div class="btn-row input-toolbar">${buttons}<button class="ghost" data-input-action="reload">刷新</button></div><form id="input-search" class="filter-row"><input aria-label="输入配置搜索" name="q" placeholder="设备、类型、点号" value="${esc(inputState.q)}"><select aria-label="输入配置筛选" name="view">${filters.map(([v,label])=>`<option value="${v}" ${inputState.view===v?'selected':''}>${label}</option>`).join('')}</select><button class="mini">查询</button></form><div class="table-wrap"><table><thead><tr><th>设备 / ${measurements?'量测':'类型'}</th><th>${measurements?'数据 / 配置':'限值范围'}</th><th>操作</th></tr></thead><tbody>${rows||'<tr><td colspan="3">暂无记录</td></tr>'}</tbody></table></div><div class="pagination"><button class="mini" data-input-page="-1" ${inputState.page===0?'disabled':''}>上一页</button><span>${inputState.page+1} / ${Math.max(1,Math.ceil(data.total/inputSize()))} · ${data.total} 条</span><button class="mini" data-input-page="1" ${(inputState.page+1)*inputSize()>=data.total?'disabled':''}>下一页</button></div></section></div>`;
}
const inputField=(label,key,value,type='number')=>`<label>${label}<input name="${key}" type="${type}" step="any" value="${esc(value??'')}"></label>`;
const inputFlag=(label,key,value)=>`<label>${label}<select name="${key}"><option value="1" ${value?'selected':''}>启用</option><option value="0" ${value?'':'selected'}>停用</option></select></label>`;
async function editInput(entity,row){
  const dialog=document.querySelector('#input-dialog');
  let body,title;
  if(entity==='limit'){
    inputState.options=(await api('/api/inputs/limit-options')).data;
    const current=row||{};
    const selected=inputState.options.find(d=>d.model_table===current.model_table&&d.model_idx===current.model_idx)||inputState.options[0];
    if(!selected)throw new Error('模型没有可配置的设备');
    title=row?'编辑安全限值':'新增安全限值';
    body=`<label class="input-wide">模型设备<select name="device">${inputState.options.map((d,i)=>`<option value="${i}" ${d===selected?'selected':''}>${esc(d.model_table+':'+d.model_idx+' '+d.device_name)}</option>`).join('')}</select></label><label>指标<select name="field">${selected.fields.map(f=>`<option ${f===current.field?'selected':''}>${f}</option>`).join('')}</select></label><label>单位<select name="unit">${['V','kV','kW','MW','A','kA'].map(u=>`<option ${u===(current.unit||'V')?'selected':''}>${u}</option>`).join('')}</select></label>${inputField('下限（可留空）','lower_value',current.lower_value)}${inputField('上限（可留空）','upper_value',current.upper_value)}${inputFlag('状态','enabled',current.enabled??1)}`;
  }else if(entity==='mapping'){
    title='编辑 SCADA 点关联';
    body=inputField('RTU编号','rtu_id',row.rtu_id)+inputField('点号','pnt_no',row.pnt_no)+inputField('倍率','scale',row.scale)+inputField('偏移','offset',row.offset)+inputFlag('关联状态','enabled',row.mapping_enabled);
  }else{
    title='SE 量测参数';
    body=inputField('权重','weight',row.weight)+inputField('有效期（秒）','max_age_seconds',row.max_age_seconds)+inputFlag('参与SE','se_enabled',row.se_enabled);
  }
  inputState.edit={entity,row};
  dialog.innerHTML=`<form id="input-edit"><h2>${title}</h2><div class="input-edit-grid">${body}</div><p id="input-form-error" role="alert"></p><div class="btn-row"><button class="primary" type="submit">保存</button><button class="ghost" type="button" data-input-close>取消</button></div></form>`;
  dialog.showModal();
}
document.addEventListener('click',async event=>{
  const el=event.target.closest('[data-input-action],[data-input-tab],[data-input-page],[data-input-edit],[data-input-toggle],[data-input-detail],[data-input-close]');
  if(!el)return;
  try{
    if(el.hasAttribute('data-input-close'))return document.querySelector('#input-dialog').close();
    if(el.dataset.inputTab){inputState.tab=el.dataset.inputTab;inputState.page=0;return render();}
    if(el.dataset.inputPage){inputState.page+=Number(el.dataset.inputPage);return render();}
    const row=inputState.rows.find(r=>(r.measurement_id||r.limit_id)===Number(el.dataset.id||el.dataset.inputToggle||el.dataset.inputDetail));
    if(el.dataset.inputEdit)return await editInput(el.dataset.inputEdit,row);
    if(el.dataset.inputDetail)return showValue(JSON.stringify(row,null,2));
    if(el.dataset.inputToggle){await api('/api/inputs/limits',{limit_id:row.limit_id,version:row.version,enabled:row.enabled?0:1});return render();}
    const action=el.dataset.inputAction;
    if(action==='new-limit')return await editInput('limit');
    if(action==='reload')return render();
    el.disabled=true;
    const result=(await api('/api/inputs/'+action,{})).data;
    notify(action==='refresh'?`采集 ${result.total} 点，有效 ${result.valid} 点，SE有效 ${result.se_valid} 点`:'配置已同步，保留已有人工修改');
    inputState.page=0;await render();
  }catch(error){notify(error.message,true);}finally{el.disabled=false;}
});
document.addEventListener('change',event=>{
  if(event.target.matches('#input-edit [name=device]')){
    const fields=inputState.options[Number(event.target.value)].fields;
    document.querySelector('#input-edit [name=field]').innerHTML=fields.map(f=>`<option>${f}</option>`).join('');
  }
});
document.addEventListener('submit',async event=>{
  if(!['input-search','input-edit'].includes(event.target.id))return;
  event.preventDefault();
  const form=new FormData(event.target);
  if(event.target.id==='input-search'){inputState.q=form.get('q');inputState.view=form.get('view');inputState.page=0;return render();}
  const {entity,row}=inputState.edit;
  const payload={};
  for(const [key,value] of form)payload[key]=['unit','field'].includes(key)?value:value===''?null:Number(value);
  let url;
  if(entity==='limit'){
    const device=inputState.options[payload.device];delete payload.device;
    Object.assign(payload,{model_table:device.model_table,model_idx:device.model_idx});
    if(row)Object.assign(payload,{limit_id:row.limit_id,version:row.version});
    url='/api/inputs/limits';
  }else{
    payload.version=entity==='mapping'?row.mapping_version:row.version;
    url=`/api/inputs/${entity}/${row.measurement_id}`;
  }
  const submit=event.target.querySelector('[type=submit]');submit.disabled=true;
  try{await api(url,payload);document.querySelector('#input-dialog').close();notify('已保存；下次计算读取新配置');await render();}
  catch(error){document.querySelector('#input-form-error').textContent=error.message;}
  finally{submit.disabled=false;}
});
