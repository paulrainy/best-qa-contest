'use strict';

const app=document.getElementById('app');
const state={user:null,today:'',clients:[],client:null};
const roles={OPER:'Менеджер-операционист ТП',FK:'Финансовый консультант ТП',MANAGER:'Клиентский менеджер ТП',CONTROLLER:'Контролёр ТП'};
const kinds=['Надёжный','Пополняемый','До востребования'];
const funding=['Со счёта или карты в Банке','Наличными через кассу','Из другого банка'];
const lists=['Решения межведомственной комиссии','Перечень организаций и физических лиц, причастных к экстремизму или терроризму'];
let fieldNumber=0;
let session; try{session=JSON.parse(sessionStorage.getItem('manual.session'));}catch{session=null;}

function h(tag,attrs={},...children){
    const node=document.createElement(tag);
    for(const [key,value] of Object.entries(attrs)){
        if(value===false||value===null||value===undefined)continue;
        if(key.startsWith('on'))node.addEventListener(key.slice(2),async event=>{try{await value(event);}catch(error){showError(error);}});
        else if(key==='className')node.className=value;
        else node.setAttribute(key,value===true?'':value);
    }
    for(const child of children.flat(Infinity))if(child!==null&&child!==undefined&&child!==false)node.append(child instanceof Node?child:document.createTextNode(String(child)));
    return node;
}
function showError(error){const target=document.querySelector('.modal .error')||document.querySelector('#app .error');if(target)target.textContent=error.message;else notice(error.message);}
function notice(text){document.getElementById('notice').textContent=text;}
function button(text,action,cls='',disabled=false){return h('button',{type:'button',className:cls,disabled,onclick:action},text);}
function link(text,hash){return h('a',{href:hash},text);}
function panel(title,...children){return h('section',{className:'panel'},h('h1',{},title),...children);}
function errorBox(){return h('div',{className:'error',role:'alert'});}
function money(value){return Number(value).toLocaleString('ru-RU',{minimumFractionDigits:2,maximumFractionDigits:2})+' ₽';}
function status(value){return h('span',{className:'status '+(value==='На подтверждении'?'pending':value==='Открыт'||value==='Активен'?'':'closed')},value);}
function input(label,name,value='',type='text',attrs={}){const id='field-'+(++fieldNumber);return h('div',{className:'field'},h('label',{for:id},label),h('input',{id,name,type,value,...attrs}));}
function select(label,name,options,value=''){const id='field-'+(++fieldNumber);return h('div',{className:'field'},h('label',{for:id},label),h('select',{id,name},options.map(option=>{const [v,t]=Array.isArray(option)?option:[option,option];return h('option',{value:v,selected:String(v)===String(value)},t);})));}
function values(form){return Object.fromEntries(new FormData(form));}
function modal(title,...children){const overlay=document.getElementById('overlay');overlay.replaceChildren(h('div',{className:'modal-backdrop'},h('section',{className:'modal',role:'dialog','aria-label':title},h('h2',{},title),...children,errorBox())));}
function closeModal(){document.getElementById('overlay').replaceChildren();}
async function request(path,body){
    const response=await fetch('api/'+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json',...(session?{Authorization:'Bearer '+session.token}:{})},body:body===undefined?undefined:JSON.stringify(body)});
    const data=await response.json();
    if(response.status===401){session=null;for(const key of Object.keys(sessionStorage))if(key.startsWith('manual.'))sessionStorage.removeItem(key);await route();}
    if(!response.ok)throw new Error(data.error||'Ошибка '+response.status);
    return data;
}
const api=(action,data={})=>request('action',{action,...data});
function navigate(hash){closeModal();if(location.hash===hash)route().catch(showError);else location.hash=hash;}
window.addEventListener('hashchange',()=>route().catch(showError));
function header(){
    const nav=document.getElementById('navigation');nav.replaceChildren();
    if(!session)return;
    nav.append(h('span',{},session.fullName+' · '+roles[session.role]),link('Поиск клиента','#/search'));
    if(session.role==='CONTROLLER')nav.append(link('Задачи','#/tasks'));
    nav.append(link('Тестовые данные','#/data'),link('СМС','#/sms'),h('a',{href:'#/login',onclick:async event=>{event.preventDefault();await request('logout',{});session=null;sessionStorage.removeItem('manual.session');navigate('#/login');}},'Выход'));
}
async function route(){
    closeModal();header();
    if(!session){renderLogin();return;}
    const boot=await api('bootstrap');state.today=boot.today;state.clients=boot.clients;state.user=boot.user;
    const [page,id,sub,productId]=location.hash.replace(/^#\//,'').split('/');
    if(page==='client'){state.client=await api('client',{id});renderClient(state.client);if(sub==='product'){const p=[...state.client.accounts,...state.client.deposits].find(p=>p.id===productId);if(p)detail(p,state.client);}}
    else if(page==='open'){state.client=await api('client',{id});renderOpen(state.client);}
    else if(page==='operation')await renderOperation(await api('operation',{id}));
    else if(page==='tasks')await renderTasks();
    else if(page==='create')renderCreate();
    else if(page==='data')renderData();
    else if(page==='sms')await renderSms();
    else renderSearch();
}
function renderLogin(){
    const form=h('form',{className:'panel login',onsubmit:async event=>{event.preventDefault();session=await request('login',values(form));sessionStorage.setItem('manual.session',JSON.stringify(session));notice('');navigate(session.role==='CONTROLLER'?'#/tasks':'#/search');}},
        h('h1',{},'Вход в ЕФР'),input('Логин','login','tst_oper01','text',{required:true,autocomplete:'username'}),input('Пароль','password','','password',{required:true,autocomplete:'current-password'}),errorBox(),h('button',{className:'primary',type:'submit'},'Войти'),h('p',{className:'muted'},'Учётные записи и пароль — в README песочницы.'));
    app.replaceChildren(form);
}
function renderSearch(){
    const form=h('form',{className:'search',onsubmit:async event=>{event.preventDefault();const c=await api('search',{passport:values(form).passport});navigate('#/client/'+c.id);}},input('Серия и номер паспорта','passport','','text',{placeholder:'4511 220345',required:true}),h('button',{type:'submit',className:'primary'},'Найти'));
    app.replaceChildren(panel('Поиск клиента',h('p',{className:'muted'},'Дата операции: '+state.today),form,errorBox(),['OPER','MANAGER'].includes(session.role)?h('div',{className:'actions'},button('Создать клиента',()=>navigate('#/create'))):null));
}
function renderClient(c){
    const meta=h('dl',{},h('dt',{},'ФИО'),h('dd',{},c.fullName),h('dt',{},'Паспорт'),h('dd',{},c.passport.slice(0,4)+' '+c.passport.slice(4)),h('dt',{},'Дата рождения'),h('dd',{},c.birthDate),h('dt',{},'Статус'),h('dd',{},status(c.status)),h('dt',{},'FATCA'),h('dd',{},({NONE:'Не присвоен',NON_US:'Не является налоговым резидентом США',US:'Налоговый резидент США'})[c.fatca]),h('dt',{},'ДБО'),h('dd',{},({FULL:'Полный',LIMITED:'Ограниченный',NONE:'Не подключено'})[c.dbo]));
    const right=h('div',{});
    right.append(h('section',{className:'panel'},h('h2',{},'Счета'),productTable(c.accounts,c)));
    const deposits=h('section',{className:'panel'},h('h2',{},'Вклады'),productTable(c.deposits,c));
    if(['OPER','FK'].includes(session.role)&&c.birthDate<=shiftYears(state.today,-18))deposits.append(h('div',{className:'actions'},button('Открыть вклад',()=>{
        if(c.fatca==='NONE'){modal('Обратите внимание',h('p',{},'Операция недоступна: у клиента не определён FATCA-статус. Заполните форму самосертификации.'),h('div',{className:'actions'},button('Отмена',closeModal),button('Заполнить форму',()=>fatca(c),'primary')));}
        else navigate('#/open/'+c.id);
    },'primary')));
    right.append(deposits,h('section',{className:'panel'},h('h2',{},'История операций'),c.history.length?h('ul',{className:'history'},c.history.map(t=>h('li',{},t))):h('p',{className:'muted'},'Записей нет')));
    app.replaceChildren(h('h1',{},'Продуктовый профиль клиента'),errorBox(),h('div',{className:'layout'},h('aside',{className:'panel'},meta),right));
}
function shiftYears(date,years){const [y,m,d]=date.split('-');return (Number(y)+years)+'-'+m+'-'+d;}
function productTable(items,c){
    if(!items.length)return h('p',{className:'muted'},'Продуктов нет');
    return h('div',{className:'overflow'},h('table',{},h('thead',{},h('tr',{},['Продукт','Номер','Сумма / остаток','Статус',''].map(t=>h('th',{},t)))),h('tbody',{},items.map(p=>h('tr',{},h('td',{},p.kind),h('td',{},p.number),h('td',{},money(p.amount)+' '+(p.currency==='RUB'?'':p.currency)),h('td',{},status(p.status)),h('td',{},button('Показать',()=>detail(p,c))))))));
}
function detail(p,c){
    const canClose=p.status==='Открыт'&&(session.role==='OPER'||session.role==='FK'&&p.type==='deposit')&&(p.type==='deposit'||p.kind==='Текущий');
    const content=h('div',{},h('p',{},p.kind+' · '+p.number),h('p',{},'Остаток: '+money(p.amount)+' · '+p.currency),h('p',{},'Статус: '+p.status));
    if(p.type==='deposit')content.append(h('p',{},'Дата открытия: '+p.opened),h('p',{},'Срок: '+(p.term?p.term+' дней':'без срока')));
    if(canClose)content.append(h('details',{},h('summary',{},'Операции'),button(p.type==='deposit'?'Закрыть вклад':'Закрыть счёт',async()=>{
        try{const op=await api('begin-close',{productId:p.id});navigate('#/operation/'+op.id);}catch(error){
            closeModal();modal('Обратите внимание',h('p',{},error.message),h('div',{className:'actions'},error.message.startsWith('У клиента нет открытого')?button('Открыть счёт',()=>navigate('#/data')):null,button('Отмена',()=>detail(p,c))));
        }
    })));
    modal('Детальная информация',content,h('div',{className:'actions'},button('Закрыть',closeModal)));
}
function fatca(c){
    const form=h('form',{onsubmit:async event=>{event.preventDefault();await api('set-fatca',{clientId:c.id,...values(form)});navigate('#/client/'+c.id);}},select('FATCA-статус','fatca',[['NON_US','Не является налоговым резидентом США'],['US','Налоговый резидент США']]),h('div',{className:'actions'},h('button',{type:'submit',className:'primary'},'Сохранить'),button('Отмена',closeModal)));
    modal('Самосертификация FATCA',form);
}
function renderOpen(c,step=1,saved){
    let stored={};try{stored=JSON.parse(sessionStorage.getItem('manual.open.'+c.id))||{};}catch{}
    const data=saved||stored;
    const steps=h('div',{className:'stepper'},['Выбор вклада','Параметры вклада','Печать и подписание'].map((t,i)=>h('span',{className:step===i+1?'active':''},(i+1)+'. '+t)));
    if(step===1){
        const form=h('form',{onsubmit:event=>{event.preventDefault();renderOpen(c,2,{...data,...values(form)});}},select('Вид вклада','kind',kinds,data.kind||'Надёжный'),h('div',{className:'actions'},h('button',{className:'primary',type:'submit'},'Далее'),button('Отмена',()=>navigate('#/client/'+c.id))));
        app.replaceChildren(panel('Открытие вклада',steps,form,errorBox()));return;
    }
    const kind=data.kind||'Надёжный',minimum=kind==='Надёжный'?10000:kind==='Пополняемый'?1000:10;
    const form=h('form',{className:'form',onsubmit:async event=>{event.preventDefault();const params={...data,...values(form)};sessionStorage.setItem('manual.open.'+c.id,JSON.stringify(params));const op=await api('open-deposit',{clientId:c.id,...params});navigate('#/operation/'+op.id);}});
    form.append(input('Сумма','amount',data.amount||'','text',{required:true,inputmode:'decimal'}));
    const minimumMessage=h('div',{className:'error'});form.append(minimumMessage);
    if(kind!=='До востребования')form.append(select('Срок, дней','term',['181','367'],data.term||'181'));
    if(kind!=='Надёжный')form.append(input('Неснижаемый остаток','minimum',money(minimum),'text',{readonly:true}));
    form.append(select('Способ внесения средств','funding',funding,data.funding||funding[0]));
    const source=select('Счёт списания','sourceId',[['','Выберите счёт'],...c.accounts.filter(p=>p.status==='Открыт'&&p.currency==='RUB').map(p=>[p.id,p.kind+' '+p.number])],data.sourceId||'');
    form.append(source,input('Ставка, % годовых','rate','','text',{readonly:true}),select('Выплата процентов','interestPayment',['Капитализация','На счёт'],data.interestPayment||'Капитализация'));
    const next=h('button',{type:'submit',className:'primary'},'Далее');
    function update(){
        const v=values(form),index=funding.indexOf(v.funding);form.elements.rate.value=(kind==='Надёжный'?['16,0','15,5','16,5']:kind==='Пополняемый'?['14,0','13,5','14,5']:['0,01','0,01','0,01'])[index];
        source.hidden=index!==0;form.elements.sourceId.required=index===0;
        const n=Number(v.amount.replaceAll(' ','').replace(',','.'));const invalid=!Number.isFinite(n)||n<minimum;
        minimumMessage.textContent=v.amount&&invalid?'Минимальная сумма для вклада «'+kind+'» — '+money(minimum):'';
        next.disabled=invalid;
    }
    form.addEventListener('input',update);form.addEventListener('change',update);
    form.append(errorBox(),h('div',{className:'actions'},button('Назад',()=>renderOpen(c,1,{...data,...values(form)})),next,button('Отмена',()=>navigate('#/client/'+c.id))));
    update();app.replaceChildren(panel('Параметры вклада «'+kind+'»',steps,c.fatca==='US'?h('p',{className:'message'},'Клиент является налоговым резидентом США. Заявка будет направлена на подтверждение контролёру.'):null,form));
}

async function renderOperation(op){
    if(op.type==='CREATE_CLIENT'){renderRegistration(op);return;}
    const c=await api('client',{id:op.clientId}),fields=op.fields,opening=op.type==='OPEN_DEPOSIT';
    if(op.status!=='Черновик'){
        app.replaceChildren(panel('Заявка '+op.id,h('p',{},op.clientName),status(op.status),op.message?h('p',{className:'message'},op.message):null,h('div',{className:'actions'},button('В продуктовый профиль',()=>navigate('#/client/'+c.id)))));return;
    }
    if(op.stage==='DBO'){
        app.replaceChildren(panel('Обратите внимание',h('p',{className:'message'},op.message),errorBox(),h('div',{className:'actions'},button('Продолжить с бумажным подписанием',async()=>renderOperation(await api('update-operation',{id:op.id,continuePaper:true})),'primary'),button('Отмена',()=>cancelClosure(op))))) ;return;
    }
    const form=h('form',{className:'form'});
    form.append(h('p',{},op.clientName),h('p',{},opening?'Вклад «'+fields.kind+'» · '+money(fields.amount)+' · '+fields.rate+'%':fields.kind+' · '+fields.number));
    if(op.type==='CLOSE_ACCOUNT')form.append(input('Остаток','balance',money(fields.originalAmount),'text',{readonly:true}));
    if(!opening&&fields.earlyMessage)form.append(h('p',{className:'message'},fields.earlyMessage));
    const isDeposit=op.type==='CLOSE_DEPOSIT',signingPage=sessionStorage.getItem('manual.step.'+op.id)==='signing';
    if(!opening&&isDeposit){
        const p=c.deposits.find(p=>p.id===op.productId);const end=new Date(p.opened+'T00:00:00Z');end.setUTCDate(end.getUTCDate()+p.term);
        form.append(input('Номер вклада','depositNumber',p.number,'text',{readonly:true}),input('Вид вклада','depositKind',p.kind,'text',{readonly:true}),input('Дата окончания срока','endDate',p.term?end.toISOString().slice(0,10):'Без срока','text',{readonly:true}),input('Сумма к выплате','payout',money(fields.payout),'text',{readonly:true}),select('Счёт для перечисления','targetId',[['','Выберите счёт'],...c.accounts.filter(p=>p.status==='Открыт'&&p.currency==='RUB'&&p.kind==='Текущий').map(p=>[p.id,p.number])],fields.targetId||''));
    }
    let nextButton;
    if(fields.minor){
        form.append(h('p',{className:'message'},'Клиенту меньше 18 лет. Операция проводится с участием законного представителя.'));
        const representative=h('div',{},h('h3',{},'Законный представитель'),input('Паспорт представителя','representativePassport',''),input('Выбранный представитель','representativeName',fields.representativeId?(state.clients.find(x=>x.id===fields.representativeId)||{}).fullName||'':'','text',{readonly:true}),h('input',{type:'hidden',name:'representativeId',value:fields.representativeId||''}),button('Найти представителя',async()=>{
            const found=await api('search',{passport:form.elements.representativePassport.value});await api('update-operation',{id:op.id,representativeId:found.id});form.elements.representativeId.value=found.id;form.elements.representativeName.value=found.fullName;if(nextButton)nextButton.disabled=!form.elements.targetId.value;
        }));form.append(representative);
    }
    if(!opening){const choices=c.dbo==='FULL'&&!fields.minor?['Электронное','Бумажное']:['Бумажное'];form.append(select('Способ подписания','signing',choices,op.signing));}
    const signing=h('div',{});form.append(signing,errorBox());
    async function save(){const v=values(form);const update={id:op.id};for(const key of ['targetId','representativeId','signing','bankOfficer'])if(Object.hasOwn(v,key))update[key]=v[key];return api('update-operation',update);}
    if(isDeposit&&!signingPage){
        form.elements.signing.closest('.field').hidden=true;
        nextButton=button('Далее',async()=>{const updated=await save();sessionStorage.setItem('manual.step.'+op.id,'signing');await renderOperation(updated);},'primary',!fields.targetId||fields.minor&&!fields.representativeId);
        form.addEventListener('change',()=>{nextButton.disabled=!form.elements.targetId.value||fields.minor&&!form.elements.representativeId.value;});
        form.append(h('div',{className:'actions'},nextButton,button('Отмена',()=>cancelClosure(op))));
        app.replaceChildren(panel('Параметры закрытия',form));return;
    }
    if(isDeposit){form.elements.targetId.closest('.field').hidden=true;form.elements.payout.closest('.field').hidden=true;if(fields.minor){form.elements.representativePassport.parentElement.parentElement.hidden=true;}}
    const back=button('Назад',async()=>{if(isDeposit){sessionStorage.removeItem('manual.step.'+op.id);await renderOperation(await api('operation',{id:op.id}));}else if(opening){await api('cancel',{id:op.id});renderOpen(c,2,{...fields});}else await cancelClosure(op);});
    const cancel=button('Отмена',async()=>{if(opening){await api('cancel',{id:op.id});navigate('#/client/'+c.id);}else await cancelClosure(op);});
    function signingControls(){
        signing.replaceChildren();const mode=opening?'Бумажное':form.elements.signing.value;
        if(mode==='Бумажное'){
            const signed=button('Документы подписаны',async()=>renderOperation(await api('sign',{id:op.id})),'primary',!op.printed);
            signing.append(input('Уполномоченное лицо банка','bankOfficer',fields.bankOfficer||session.fullName,'text',{required:true}),h('div',{className:'actions'},button('Печать',async()=>{
                const tab=window.open('about:blank','_blank');
                try{await save();const printed=await api('print',{id:op.id});if(tab){tab.document.title='Заявление';tab.document.body.replaceChildren(h('h1',{},'Заявление: '+(opening?'открытие вклада':op.type==='CLOSE_DEPOSIT'?'закрытие вклада':'закрытие счёта')),h('p',{},op.clientName),h('p',{},'Заявка '+op.id),h('p',{},opening?'Сумма '+money(fields.amount):'Продукт '+fields.number),h('p',{},'Уполномоченное лицо банка: '+form.elements.bankOfficer.value));}op.printed=printed.printed;signed.disabled=false;}catch(error){if(tab)tab.close();throw error;}
            }),signed,back,cancel));
            form.addEventListener('input',()=>{signed.disabled=true;});
        }else{
            const message=h('p',{className:'muted'},'Отправленный код доступен в разделе «СМС» в верхнем меню.');
            signing.append(input('Код из СМС','code','','text',{pattern:'[0-9]{6}',maxlength:6,inputmode:'numeric'}),message,h('div',{className:'actions'},button('Отправить код',async()=>{await save();const sent=await api('send-sms',{id:op.id});notice(sent.message);}),button('Подписать',async()=>{
                await save();const result=await api('sign',{id:op.id,code:form.elements.code.value});await renderOperation(result);
            },'primary'),back,cancel));
        }
    }
    if(!opening)form.elements.signing.addEventListener('change',signingControls);
    signingControls();if(op.message&&!fields.minor)form.prepend(h('p',{className:'message'},op.message));
    app.replaceChildren(panel(opening?'Печать и подписание':isDeposit?'Подписание':'Закрытие счёта',form));
}
async function cancelClosure(op){await api('cancel',{id:op.id});sessionStorage.removeItem('manual.step.'+op.id);navigate('#/client/'+op.clientId+'/product/'+op.productId);}
async function renderTasks(){
    const result=await api('tasks');
    app.replaceChildren(panel('Все задачи',errorBox(),result.tasks.length?h('table',{},h('thead',{},h('tr',{},['Заявка','Клиент','Операция','Статус',''].map(t=>h('th',{},t)))),h('tbody',{},result.tasks.map(op=>h('tr',{},h('td',{},op.id),h('td',{},op.clientName),h('td',{},({OPEN_DEPOSIT:'Открытие вклада',CLOSE_DEPOSIT:'Закрытие вклада',CREATE_CLIENT:'Создание клиента'})[op.type]),h('td',{},status(op.status)),h('td',{},button('Взять и исполнить',async()=>renderTask(await api('take',{id:op.id})))))))):h('p',{className:'muted'},'Заявок на подтверждение нет')));
}
function renderTask(op){
    const comment=input('Комментарий','comment','');
    const warning=op.type==='CREATE_CLIENT'?h('section',{className:'message warning'},h('h2',{},'Внимание'),h('p',{},'Возможен дубль клиента. Проверьте данные в АБС перед подтверждением.'),h('p',{},op.duplicate.fullName+' · '+op.duplicate.birthDate+' · '+op.duplicate.passport)):null;
    const approve=op.type==='CREATE_CLIENT'?'Подтвердить операцию':'Подтвердить',reject=op.type==='CREATE_CLIENT'?'Отменить операцию':'Отклонить';
    app.replaceChildren(panel('Заявка '+op.id,h('p',{},op.clientName),status(op.status),warning,h('dl',{},Object.entries(op.fields).filter(([k])=>['kind','amount','payout','number','funding','rate','term'].includes(k)).map(([k,v])=>[h('dt',{},({kind:'Вид вклада',amount:'Сумма',payout:'Сумма к выплате',number:'Продукт',funding:'Способ внесения',rate:'Ставка',term:'Срок'})[k]),h('dd',{},v)])),comment,errorBox(),h('div',{className:'actions'},button(approve,async()=>{const result=await api('decide',{id:op.id,approve:true});notice(result.message||'Заявка '+result.status);await renderTasks();},'primary'),button(reject,async()=>{const result=await api('decide',{id:op.id,approve:false,comment:comment.querySelector('input').value});notice('Заявка '+result.status);await renderTasks();},'danger'),button('К списку задач',renderTasks))));
}
function renderCreate(saved={}){
    const defaults={surname:'',name:'',patronymic:'',birthDate:'',gender:'Мужской',passport:'',issued:'',division:'',issuer:'',phone:'',address:'',...saved};
    const form=h('form',{className:'form',onsubmit:async event=>{event.preventDefault();const op=await api('create-client',values(form));navigate('#/operation/'+op.id);}});
    const grid=h('div',{className:'grid'});
    for(const [key,label,type] of [['surname','Фамилия','text'],['name','Имя','text'],['patronymic','Отчество','text'],['birthDate','Дата рождения','date']])grid.append(input(label,key,defaults[key],type,{required:key!=='patronymic'}));
    grid.append(select('Пол','gender',['Мужской','Женский'],defaults.gender),input('Гражданство','citizenship','РФ','text',{readonly:true}),input('Паспорт РФ — серия и номер','passport',defaults.passport,'text',{required:true}),input('Дата выдачи','issued',defaults.issued,'date',{required:true}),input('Код подразделения','division',defaults.division,'text',{placeholder:'770-001',required:true}),input('Кем выдан','issuer',defaults.issuer,'text',{required:true}),input('Мобильный телефон','phone',defaults.phone,'tel',{required:true}),input('Адрес регистрации','address',defaults.address,'text',{required:true}));
    form.append(grid,errorBox(),h('div',{className:'actions'},h('button',{type:'submit',className:'primary'},'Сохранить'),button('Отмена',()=>navigate('#/search'))));
    app.replaceChildren(panel('Создание клиента',form));
}
function renderRegistration(op){
    const buttons=h('div',{className:'actions'}),content=h('div',{},h('p',{className:'message'},op.message),status(op.status));
    if(op.stage==='DUPLICATE'){
        buttons.append(button('Ввести данные предыдущего паспорта',()=>{
            const form=h('form',{onsubmit:async event=>{event.preventDefault();const p=values(form);const next=await api('continue-client',{id:op.id,choice:'previous',passport:p.series+p.number});closeModal();renderRegistration(next);}},h('div',{className:'grid'},input('Серия','series','','text',{pattern:'[0-9]{4}',required:true,maxlength:4}),input('Номер','number','','text',{pattern:'[0-9]{6}',required:true,maxlength:6})),h('div',{className:'actions'},h('button',{type:'submit',className:'primary'},'Проверить'),button('Отмена',closeModal)));
            modal('Предыдущий паспорт РФ',form);
        }),button('Нет предыдущего паспорта',async()=>renderRegistration(await api('continue-client',{id:op.id,choice:'noPrevious'}))));
    }else if(op.stage==='FINMON')buttons.append(button('Продолжить',async()=>renderRegistration(await api('continue-client',{id:op.id,choice:'continue'})),'primary'));
    else if(op.stage==='EXISTING')buttons.append(button('Открыть карточку',()=>navigate('#/client/'+op.existingId),'primary'));
    else if(op.status==='Исполнена')buttons.append(button('Открыть карточку',()=>navigate('#/client/'+op.clientId),'primary'));
    else if(op.status==='На подтверждении')buttons.append(h('p',{className:'muted'},'Карточка в статусе «Черновик» и не находится в поиске. Решение доступно контролёру.'));
    if(op.status==='Черновик')buttons.append(button('Отмена',async()=>{await api('cancel',{id:op.id});navigate('#/search');}));
    else buttons.append(button('К поиску',()=>navigate('#/search')));
    app.replaceChildren(panel(op.stage==='DUPLICATE'||op.stage==='FINMON'?'Обратите внимание':'Создание клиента',content,errorBox(),buttons));
}
async function renderSms(){
    const messages=(await api('sms')).messages;
    app.replaceChildren(panel('Учебный телефон — СМС',h('p',{className:'muted'},'Здесь показаны сообщения, действительно отправленные кнопкой «Отправить код».'),messages.length?h('table',{},h('thead',{},h('tr',{},['Клиент','Телефон','Заявка','Сообщение'].map(t=>h('th',{},t)))),h('tbody',{},messages.map(m=>h('tr',{},h('td',{},m.clientName),h('td',{},m.phone),h('td',{},link(m.operationId,'#/operation/'+m.operationId)),h('td',{},m.text))))):h('p',{},'СМС ещё не отправлялись'),h('div',{className:'actions'},button('Обновить',renderSms))));
}
function renderData(){
    const picker=select('Существующий клиент','id',[['','Новый клиент'],...state.clients.map(c=>[c.id,c.fullName+' · '+c.passport])]);
    const form=h('form',{className:'form',onsubmit:async event=>{event.preventDefault();const saved=await api('prepare',{entity:'client',...values(form)});notice('Учебные данные клиента сохранены');navigate('#/client/'+saved.id);}});
    const fields=h('div',{className:'grid'});
    const names=[['surname','Фамилия'],['name','Имя'],['patronymic','Отчество'],['passport','Паспорт — 10 цифр'],['birthDate','Дата рождения','date'],['phone','Мобильный телефон'],['previousPassports','Предыдущие паспорта через запятую']];
    for(const [key,label,type]of names)fields.append(input(label,key,key==='birthDate'?'1990-01-01':'',type||'text',{required:['surname','name','passport','birthDate'].includes(key)}));
    fields.append(select('FATCA','fatca',[['NON_US','Не резидент США'],['US','Резидент США'],['NONE','Не присвоен']]),select('ДБО','dbo',[['FULL','Полный'],['LIMITED','Ограниченный'],['NONE','Не подключено']]));
    form.append(picker,fields,errorBox(),h('button',{className:'primary',type:'submit'},'Сохранить клиента'));
    picker.querySelector('select').addEventListener('change',()=>{const c=state.clients.find(x=>x.id===form.elements.id.value);for(const [key]of names)form.elements[key].value=c?(key==='previousPassports'?c.previousPassports.join(','):c[key]||c.fields[key]||''):key==='birthDate'?'1990-01-01':'';form.elements.fatca.value=c?.fatca||'NON_US';form.elements.dbo.value=c?.dbo||'FULL';});
    const products=h('form',{className:'form',onsubmit:async event=>{event.preventDefault();const result=await api('prepare',{entity:'product',...values(products)});notice('Учебный продукт '+result.number+' сохранён');navigate('#/client/'+result.clientId);}});
    products.append(select('Клиент','clientId',state.clients.map(c=>[c.id,c.fullName+' · '+c.passport])),select('Тип продукта','type',[['account','Счёт'],['deposit','Вклад']]),select('Вид продукта','kind',['Текущий','Карточный',...kinds]),input('Номер — 20 цифр, пустой для автоматического','number',''),input('Сумма / остаток','amount','0'),select('Валюта','currency',['RUB','USD','EUR']),select('Статус','status',['Открыт','Закрыт']),input('Дата открытия','opened',state.today,'date'),select('Срок, дней','term',['181','367','0']),errorBox(),h('button',{className:'primary',type:'submit'},'Добавить продукт'));
    const editor=h('div',{}),productPicker=select('Изменить существующий продукт','productId',[['','Выберите продукт'],...state.clients.flatMap(c=>[...c.accounts,...c.deposits].map(p=>[p.id,c.fullName+' · '+p.number]))]);
    productPicker.querySelector('select').addEventListener('change',()=>{const p=state.clients.flatMap(c=>[...c.accounts,...c.deposits]).find(p=>p.id===productPicker.querySelector('select').value);editor.replaceChildren();if(!p)return;const f=h('form',{onsubmit:async event=>{event.preventDefault();await api('prepare',{entity:'product',...p,...values(f)});notice('Продукт обновлён');navigate('#/client/'+p.clientId);}},input('Сумма / остаток','amount',p.amount),select('Статус','status',['Открыт','Закрыт'],p.status),input('Дата открытия','opened',p.opened,'date'),errorBox(),h('button',{type:'submit'},'Обновить продукт'));editor.append(f);});
    const fm=h('form',{className:'form',onsubmit:async event=>{event.preventDefault();await api('prepare',{entity:'finmon',...values(fm)});notice('Учебный список обновлён');}},input('Паспорт проверяемого человека','passport',''),select('Принадлежность к списку','list',[['','Нет в списках'],...lists]),errorBox(),h('button',{type:'submit'},'Сохранить запись списка'));
    app.replaceChildren(panel('Подготовка тестовых данных',h('p',{className:'message warning'},'Эти действия меняют условия учебного стенда. Подготовьте их явно перед проверкой; бизнес-операции выполняются в продуктовом профиле. Дата операции: '+state.today),h('details',{},h('summary',{},'Создать или изменить клиента'),form),h('details',{},h('summary',{},'Добавить счёт или вклад'),products),h('details',{},h('summary',{},'Изменить продукт'),productPicker,editor),h('details',{},h('summary',{},'Подготовить списки финмониторинга'),fm),h('details',{},h('summary',{},'Исходные клиенты'),h('table',{},h('tbody',{},state.clients.map(c=>h('tr',{},h('td',{},link(c.fullName,'#/client/'+c.id)),h('td',{},c.passport),h('td',{},c.birthDate)))))),h('p',{className:'muted'},'Расчёт выплаты срочного вклада в день окончания срока и позже не задан BIQ и не поддерживается. Для досрочного закрытия задайте соответствующие дату открытия и срок.'),h('div',{className:'actions'},button('Сбросить данные',()=>modal('Сбросить данные?',h('p',{},'Все учебные изменения, заявки, СМС и сессии будут удалены. Вернутся исходные данные.'),h('div',{className:'actions'},button('Отмена',closeModal),button('Сбросить',async()=>{await request('reset',{});session=null;sessionStorage.clear();notice('Исходные данные восстановлены');navigate('#/login');},'danger'))),'danger'))));
}
route().catch(showError);
