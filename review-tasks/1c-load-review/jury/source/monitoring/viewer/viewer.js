/* Автономная навигация. Исходники уже встроены, сеть и хранилища не используются. */
(() => {
    "use strict";
    const sources = JSON.parse(document.getElementById("sources").textContent);
    const tasks = Array.from(document.querySelectorAll(".task"));
    const selectedViews = {};
    let current = "16";
    let copyTrigger;
    let toastTimer;
    const getTask = number => tasks.find(task => task.dataset.number === number);

    function show(number, view, focus = false) {
        const task = getTask(number);
        if (!task) return;
        current = number;
        const views = Array.from(task.querySelectorAll("[data-view]"));
        const requested = view || selectedViews[number];
        const active = views.find(item => item.dataset.view === requested) || views[0];
        selectedViews[number] = active.dataset.view;
        tasks.forEach(item => { item.hidden = item !== task; });
        views.forEach(item => { item.hidden = item !== active; });
        task.querySelectorAll("[data-tab]").forEach(button => {
            button.setAttribute("aria-pressed", String(button.dataset.tab === active.dataset.view));
        });
        document.querySelectorAll("nav [data-task]").forEach(link => {
            if (link.dataset.task === number) link.setAttribute("aria-current", "page");
            else link.removeAttribute("aria-current");
        });
        if (focus) task.querySelector("h1").focus();
    }

    function followHash() {
        const line = /^#line-(\d+)-(\d+)$/.exec(location.hash);
        const task = /^#task-(\d+)$/.exec(location.hash);
        if (line && getTask(line[1])) {
            show(line[1], "source");
            const target = document.getElementById(location.hash.slice(1));
            if (target) {
                target.querySelector("a").focus({preventScroll: true});
                target.scrollIntoView({block: "center"});
            }
        } else if (task) show(task[1], null, true);
    }

    document.addEventListener("click", event => {
        const tab = event.target.closest("[data-tab]");
        if (tab) show(current, tab.dataset.tab);
        const expand = event.target.closest("[data-expand]");
        if (expand) getTask(current).querySelectorAll("details.panel").forEach(panel => {
            panel.open = expand.dataset.expand === "true";
        });
        const link = event.target.closest('a[href^="#line-"], a[data-task]');
        // Повторный переход по тому же якорю тоже открывает нужное представление.
        if (link && link.hash === location.hash) followHash();
    });
    window.addEventListener("hashchange", followHash);

    const search = document.getElementById("search");
    const results = document.getElementById("search-results");
    const searchStatus = document.getElementById("search-status");
    function find() {
        results.replaceChildren();
        const query = search.value.trim().toLocaleLowerCase();
        results.hidden = !query;
        searchStatus.textContent = "";
        if (!query) return;
        let count = 0;
        for (const source of sources) {
            source.source.split(/\r\n|\n|\r/).forEach((line, index) => {
                const position = line.toLocaleLowerCase().indexOf(query);
                if (position < 0) return;
                count++;
                const link = document.createElement("a");
                link.className = "search-hit";
                link.href = `#line-${source.name.slice(0, 2)}-${index + 1}`;
                const label = document.createElement("small");
                label.textContent = `${source.name} · строка ${index + 1}`;
                const code = document.createElement("code");
                const mark = document.createElement("mark");
                mark.textContent = line.slice(position, position + query.length);
                code.append(document.createTextNode(line.slice(0, position)), mark,
                    document.createTextNode(line.slice(position + query.length)));
                link.append(label, code);
                results.append(link);
            });
        }
        searchStatus.textContent = count ? `Найдено строк: ${count}. Выберите строку, чтобы открыть исходник.` : "Совпадений нет.";
        results.hidden = count === 0;
    }
    document.getElementById("search-form").addEventListener("submit", event => {
        event.preventDefault();
        find();
    });
    search.addEventListener("input", find);
    document.getElementById("clear-search").addEventListener("click", () => {
        search.value = "";
        find();
        search.focus();
    });

    const fallback = document.getElementById("copy-fallback");
    const copyText = document.getElementById("copy-text");
    document.querySelectorAll("[data-copy]").forEach(button => {
        button.addEventListener("click", async () => {
            const text = sources.find(source => source.name.startsWith(button.dataset.copy)).source;
            copyTrigger = button;
            try {
                await navigator.clipboard.writeText(text);
                const status = document.getElementById("copy-status");
                status.textContent = "Исходный файл скопирован";
                status.hidden = false;
                clearTimeout(toastTimer);
                toastTimer = setTimeout(() => { status.hidden = true; }, 2500);
            } catch (_) {
                fallback.hidden = false;
                copyText.value = text;
                copyText.focus();
                copyText.select();
            }
        });
    });
    function closeCopy() {
        fallback.hidden = true;
        if (copyTrigger) copyTrigger.focus();
    }
    document.getElementById("close-copy").addEventListener("click", closeCopy);
    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && !fallback.hidden) closeCopy();
    });

    document.documentElement.classList.add("js");
    show(current);
    followHash();
})();
