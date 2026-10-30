// Только жюри. Функция для Playwright browser_run_code, не для архива участника.
// Требуется запущенная песочница. Изменяет её учебные данные.
async (page) => {
    const base='http://localhost:18081/efr/';
    const results=[];
    const check=(condition,message)=>{if(!condition)throw new Error(message);};
    async function login(user='tst_oper01'){
        await page.goto(base);
        if(await page.getByRole('link',{name:'Выход',exact:true}).count())await page.getByRole('link',{name:'Выход',exact:true}).click();
        await page.getByRole('heading',{name:'Вход в ЕФР',exact:true}).waitFor();
        await page.getByLabel('Логин',{exact:true}).fill(user);
        await page.getByLabel('Пароль',{exact:true}).fill('Test123!');
        await page.getByRole('button',{name:'Войти',exact:true}).click();
        await page.getByRole('link',{name:'Тестовые данные',exact:true}).waitFor();
    }
    async function search(passport){
        await page.getByRole('link',{name:'Поиск клиента',exact:true}).click();
        await page.getByLabel('Серия и номер паспорта').fill(passport);
        await page.getByRole('button',{name:'Найти',exact:true}).click();
        await page.getByRole('heading',{name:'Продуктовый профиль клиента',exact:true}).waitFor();
    }
    async function opening(){
        await search('4511 220345');
        await page.getByRole('button',{name:'Открыть вклад',exact:true}).click();
        await page.getByRole('button',{name:'Далее',exact:true}).click();
        await page.getByLabel('Сумма',{exact:true}).fill('10000');
        await page.getByLabel('Счёт списания',{exact:true}).selectOption({label:'Текущий 40817810500000012345'});
        await page.getByRole('button',{name:'Далее',exact:true}).click();
        await page.getByRole('heading',{name:'Печать и подписание',exact:true}).waitFor();
    }
    async function closeProduct(passport,number){
        await search(passport);
        await page.getByRole('row').filter({hasText:number}).getByRole('button',{name:'Показать'}).click();
        await page.getByText('Операции',{exact:true}).click();
        await page.getByRole('button',{name:'Закрыть вклад',exact:true}).click();
    }
    async function run(name,fn){try{await fn();results.push({name,pass:true});}catch(error){results.push({name,pass:false,error:error.message});}}
    await login();
    await run('empty officer invalidates print',async()=>{
        await opening();
        let popup=page.waitForEvent('popup');await page.getByRole('button',{name:'Печать',exact:true}).click();await(await popup).close();
        const sign=page.getByRole('button',{name:'Документы подписаны',exact:true});
        await sign.waitFor();await page.waitForFunction(()=>!Array.from(document.querySelectorAll('button')).find(x=>x.textContent==='Документы подписаны').disabled);
        await page.getByLabel('Уполномоченное лицо банка',{exact:true}).fill('');
        const response=page.waitForResponse(r=>r.url().endsWith('/api/action')&&r.request().postDataJSON().action==='print');
        await page.getByRole('button',{name:'Печать',exact:true}).click();
        const printed=await response;
        check(printed.status()===400,'Print accepted an empty bank officer');
        check(await sign.isDisabled(),'Signing still enabled after clearing officer');
    });
    await run('closure cancellation restores product detail',async()=>{
        await closeProduct('4520 112334','42301810800000056781');
        await page.getByRole('heading',{name:'Параметры закрытия',exact:true}).waitFor();
        await page.getByRole('button',{name:'Отмена',exact:true}).click();
        await page.getByRole('dialog',{name:'Детальная информация',exact:true}).waitFor({timeout:3000});
        check((await page.getByRole('dialog').innerText()).includes('42301810800000056781'),'Wrong originating product');
        await page.getByRole('button',{name:'Закрыть',exact:true}).click();
    });
    await run('term deposit end date visible and readonly',async()=>{
        await closeProduct('4521 223445','42305810400000067891');
        await page.getByRole('button',{name:'Продолжить с бумажным подписанием',exact:true}).click();
        await page.getByRole('heading',{name:'Параметры закрытия',exact:true}).waitFor();
        const end=page.getByLabel('Дата окончания срока',{exact:true});
        check(await end.count()===1,'End date required by BIQ is absent');
        check(await end.getAttribute('readonly')!==null,'End date is editable');
        check(await end.inputValue()!=='','End date is empty');
    });
    await run('fixture labels focus the correct input',async()=>{
        await page.getByRole('link',{name:'Тестовые данные',exact:true}).click();
        await page.getByText('Подготовить списки финмониторинга',{exact:true}).click();
        await page.getByText('Паспорт проверяемого человека',{exact:true}).click();
        check(await page.getByLabel('Паспорт проверяемого человека',{exact:true}).evaluate(el=>el===document.activeElement),'Label does not focus finmon passport input');
    });
    await run('account closure shows readonly balance',async()=>{
        await search('4522 334556');
        await page.getByRole('row').filter({hasText:'40817810500000089012'}).getByRole('button',{name:'Показать'}).click();
        await page.getByText('Операции',{exact:true}).click();
        await page.getByRole('button',{name:'Закрыть счёт',exact:true}).click();
        await page.getByRole('heading',{name:'Закрытие счёта',exact:true}).waitFor();
        const balance=page.getByLabel('Остаток',{exact:true});
        check(await balance.count()===1,'Account balance required by BIQ is absent');
        check(await balance.getAttribute('readonly')!==null,'Account balance is editable');
    });
    await run('controller receives required saved message',async()=>{
        await page.getByRole('link',{name:'Поиск клиента',exact:true}).click();
        await page.getByRole('button',{name:'Создать клиента',exact:true}).click();
        for(const [label,value]of Object.entries({'Фамилия':'СЕМЕНОВА','Имя':'АЛЕНА','Отчество':'','Дата рождения':'1990-03-12','Паспорт РФ — серия и номер':'4525999988','Дата выдачи':'2025-01-01','Код подразделения':'770-001','Кем выдан':'МВД','Мобильный телефон':'+79000000001','Адрес регистрации':'Москва'}))await page.getByLabel(label,{exact:true}).fill(value);
        await page.getByRole('button',{name:'Сохранить',exact:true}).click();
        await page.getByRole('button',{name:'Нет предыдущего паспорта',exact:true}).click();
        await page.getByText('На подтверждении',{exact:true}).waitFor();
        const op=new URL(page.url()).hash.split('/').pop();
        await login('tst_contr01');
        await page.getByRole('row').filter({hasText:op}).getByRole('button',{name:'Взять и исполнить'}).click();
        await page.getByRole('button',{name:'Подтвердить операцию',exact:true}).click();
        await page.getByRole('status').filter({hasText:'Карточка клиента сохранена'}).waitFor({timeout:3000});
    });
    return results;
}
