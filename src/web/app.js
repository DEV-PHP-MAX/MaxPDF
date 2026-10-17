/* Max PDF — interface (GSAP + Flip + SplitText + Lucide, tudo local). */
(() => {
  "use strict";

  gsap.registerPlugin(Flip, SplitText);

  // `?motion` força as animações mesmo com "reduzir movimento" (para testes).
  const RM = matchMedia("(prefers-reduced-motion: reduce)").matches && !location.search.includes("motion");
  // Reduzir movimento: tudo chega ao estado final quase na hora.
  if (RM) gsap.globalTimeline.timeScale(25);
  const FINE = matchMedia("(hover: hover) and (pointer: fine)").matches;
  const MAX_ROWS = 400;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];

  /* ---------- Ícones ---------- */
  const pascal = (n) => n.replace(/(^|-)(\w)/g, (_, __, c) => c.toUpperCase());
  function ic(name) {
    const node = lucide.icons[pascal(name)];
    if (!node) return "";
    const el = lucide.createElement(node);
    el.setAttribute("class", `lucide lucide-${name}`);
    el.setAttribute("aria-hidden", "true");
    return el.outerHTML;
  }
  function hydrateIcons(root = document) {
    $$("i[data-icon]", root).forEach((i) => {
      const tpl = document.createElement("template");
      tpl.innerHTML = ic(i.dataset.icon);
      i.replaceWith(tpl.content.firstChild || document.createTextNode(""));
    });
  }
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const plural = (n, one, many) => `${n.toLocaleString("pt-BR")} ${n === 1 ? one : many}`;

  /* ---------- Ferramentas ---------- */
  const TOOLS = {
    reverse: {
      label: "Inverter páginas", icon: "arrow-down-up", eyebrow: "Lote",
      desc: "Coloca as páginas de trás para frente em quantos PDFs você quiser. O conteúdo não é recomprimido.",
      action: "Inverter páginas", folder: true, kind: "pdf",
    },
    merge: {
      label: "Juntar PDFs", icon: "layers", eyebrow: "Um arquivo final",
      desc: "Une vários PDFs em um só, na ordem da lista. Arraste as linhas para mudar a ordem.",
      action: "Juntar PDFs", folder: true, kind: "pdf", reorder: true,
    },
    split: {
      label: "Separar PDF", icon: "scissors", eyebrow: "Um documento",
      desc: "Gera um arquivo por página ou extrai só as páginas que você indicar.",
      action: "Separar PDF", folder: false, kind: "pdf", single: true,
    },
    rotate: {
      label: "Girar páginas", icon: "rotate-cw", eyebrow: "Lote",
      desc: "Gira todas as páginas, ou só algumas, em 90°, 180° ou 270°. Sem perder qualidade.",
      action: "Girar páginas", folder: true, kind: "pdf",
    },
    images: {
      label: "Imagens → PDF", icon: "image-plus", eyebrow: "JPG, PNG, WEBP, BMP, TIFF",
      desc: "Junta imagens em um único PDF, na ordem da lista. Transparências viram fundo branco.",
      action: "Gerar PDF", folder: false, kind: "img", reorder: true,
    },
  };
  const ORDER = ["reverse", "merge", "split", "rotate", "images"];
  const SORTS = [
    ["name_asc", "A → Z"], ["name_desc", "Z → A"], ["path", "Pasta"], ["modified", "Data"], ["custom", "Manual"],
  ];

  const state = {
    active: "reverse",
    running: null,
    t: {
      reverse: { items: [], opts: { keepStructure: true } },
      merge: { items: [], sort: "name_asc", opts: {} },
      split: { file: null, opts: { pagesMode: "all", pages: "" } },
      rotate: { items: [], opts: { angle: 90, pagesMode: "all", pages: "", keepStructure: true } },
      images: { items: [], opts: {} },
    },
  };

  /* ---------- API (pywebview ou simulação no navegador) ---------- */
  let api = null;
  const whenApi = new Promise((resolve) => {
    if (window.pywebview && window.pywebview.api) return resolve(window.pywebview.api);
    window.addEventListener("pywebviewready", () => resolve(window.pywebview.api));
    // Fora do app (preview no navegador) usa a simulação.
    setTimeout(() => { if (!window.pywebview) resolve(createMockApi()); }, 600);
  });

  /* ---------- Eventos vindos do Python ---------- */
  window.maxpdf = {
    receive({ event, payload }) {
      const fn = handlers[event];
      if (fn) fn(payload);
    },
  };
  const handlers = {
    state(p) { applyState(p, { enterNew: true }); },
    scan(p) {
      const el = $(`.scan[data-tool="${p.tool}"]`);
      if (!p.done) {
        if (el) { el.hidden = false; $(".scan-text", el).textContent = p.count ? `Procurando PDFs… ${p.count.toLocaleString("pt-BR")} encontrados` : "Procurando PDFs…"; }
        return;
      }
      if (el) el.hidden = true;
      if (p.error) return toast(`Erro ao procurar PDFs: ${p.error}`, "error");
      const dup = (p.count || 0) - (p.added || 0);
      if (!p.count) toast("Nenhum PDF encontrado nessa pasta.", "warn");
      else toast(`${plural(p.added, "PDF adicionado", "PDFs adicionados")}${dup ? ` · ${dup} já estava${dup > 1 ? "m" : ""} na lista` : ""}.`, "success");
    },
    dropped(p) { reportAdded(p); },
    progress(p) { updateProgress(p); },
    done(p) { finishRun(p); },
  };

  function reportAdded(p) {
    const parts = [];
    if (p.added) parts.push(plural(p.added, "arquivo adicionado", "arquivos adicionados"));
    if (p.duplicates) parts.push(`${p.duplicates} repetido${p.duplicates > 1 ? "s" : ""} ignorado${p.duplicates > 1 ? "s" : ""}`);
    if (p.skipped) parts.push(`${p.skipped} incompatíve${p.skipped > 1 ? "is" : "l"} ignorado${p.skipped > 1 ? "s" : ""}`);
    if (!parts.length) return;
    toast(parts.join(" · "), p.added ? (p.skipped || p.duplicates ? "warn" : "success") : "warn");
  }

  function applyState(p, { enterNew = false, flip = false } = {}) {
    const t = state.t[p.tool];
    if (p.tool === "split") {
      const changed = (t.file && t.file.full) !== (p.file && p.file.full);
      t.file = p.file;
      if (state.active === "split" && changed) renderSingle(true);
    } else {
      const before = new Set(t.items.map((i) => i.full));
      t.items = p.items;
      if (p.sort) t.sort = p.sort;
      if (state.active === p.tool) {
        const enter = enterNew ? new Set(p.items.filter((i) => !before.has(i.full)).map((i) => i.full)) : null;
        renderList({ enter, flip });
        if (p.tool === "merge") moveSeg($(".seg[data-opt=sort]"), t.sort);
      }
    }
    updateActionbar();
  }

  /* ---------- Navegação ---------- */
  const nav = $(".nav");
  const pill = $(".nav-pill");
  function buildNav() {
    nav.insertAdjacentHTML("afterbegin", `<div class="nav-label">Ferramentas</div>`);
    ORDER.forEach((key) => {
      const t = TOOLS[key];
      nav.insertAdjacentHTML("beforeend",
        `<button class="nav-item" data-tool="${key}" type="button" title="${esc(t.label)}">
          <span class="nav-ico">${ic(t.icon)}</span><span class="nav-text">${esc(t.label)}</span>
        </button>`);
    });
    nav.addEventListener("click", (e) => {
      const b = e.target.closest(".nav-item");
      if (b) switchTool(b.dataset.tool);
    });
  }
  function movePill(animate = true) {
    const item = $(`.nav-item[data-tool="${state.active}"]`);
    if (!item) return;
    $$(".nav-item").forEach((b) => b.classList.toggle("active", b === item));
    gsap.to(pill, { y: item.offsetTop, opacity: 1, duration: animate ? 0.55 : 0, ease: "back.out(1.5)" });
    if (animate) gsap.fromTo($(".nav-ico", item), { scale: 0.7, rotate: -12 }, { scale: 1, rotate: 0, duration: 0.6, ease: "elastic.out(1, 0.45)" });
  }

  let split = null;
  let switching = false;
  function switchTool(key, first = false) {
    if (!TOOLS[key] || (key === state.active && !first) || switching) return;
    state.active = key;
    whenApi.then((a) => a.set_active(key));
    movePill(!first);
    const view = $("#view");
    const inner = $(".view-inner", view);
    const go = () => {
      renderView();
      view.scrollTop = 0;
      animateViewIn();
      switching = false;
    };
    if (inner && !first) {
      switching = true;
      gsap.to(inner.children, { y: -12, autoAlpha: 0, duration: 0.22, stagger: 0.03, ease: "power2.in", onComplete: go });
    } else go();
  }

  function animateViewIn() {
    if (split) split.revert();
    const title = $(".title");
    split = SplitText.create(title, { type: "words,chars", mask: "words" });
    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
    tl.from(".eyebrow", { y: 10, autoAlpha: 0, duration: 0.45 })
      .from(split.chars, { yPercent: 110, duration: 0.7, stagger: 0.016, ease: "expo.out" }, "<0.05")
      .from(".desc", { y: 14, autoAlpha: 0, duration: 0.6 }, "<0.15")
      .from(".view-inner > .card", { y: 28, autoAlpha: 0, duration: 0.7, stagger: 0.08 }, "<0.1")
      .from(".row", { x: -14, autoAlpha: 0, duration: 0.45, stagger: { each: 0.025, amount: 0.4 } }, "<0.25");
  }

  /* ---------- Renderização da ferramenta ---------- */
  function renderView() {
    const key = state.active;
    const t = TOOLS[key];
    const html = `
      <div class="view-inner">
        <header class="head">
          <div>
            <span class="eyebrow"><span class="eyebrow-ico">${ic(t.icon)}</span>${esc(t.eyebrow)}</span>
            <h1 class="title">${esc(t.label)}</h1>
            <p class="desc">${esc(t.desc)}</p>
          </div>
        </header>
        ${t.single ? singleCard() : dropzoneCard(key)}
        ${optionsCard(key)}
        ${t.single ? "" : listCard(key)}
      </div>`;
    $("#view").innerHTML = html;
    bindView(key);
    if (!t.single) renderList({ instant: true });
    else renderSingle(false);
    updateActionbar();
  }

  function dropzoneCard(key) {
    const t = TOOLS[key];
    const img = t.kind === "img";
    return `
      <section class="card dropzone" data-zone>
        <div class="dz-art" aria-hidden="true">
          <span class="dz-sheet s1"></span><span class="dz-sheet s2"></span>
          <span class="dz-sheet s3"><b>${img ? "IMG" : "PDF"}</b></span>
        </div>
        <div class="dz-body">
          <h3>Arraste ${img ? "imagens" : "PDFs ou pastas"} para cá</h3>
          <p>${img ? "Ou escolha os arquivos no computador." : "Ou escolha no computador. Pastas são lidas com todas as subpastas."}</p>
          <div class="dz-actions">
            <button class="btn btn-primary" data-act="pick" type="button"><span class="btn-label">${ic("file-plus-2")}Selecionar ${img ? "imagens" : "PDFs"}</span></button>
            ${t.folder ? `<button class="btn" data-act="folder" type="button"><span class="btn-label">${ic("folder-open")}Selecionar pasta</span></button>` : ""}
          </div>
          <div class="scan" data-tool="${key}" hidden><span class="spinner"></span><span class="scan-text">Procurando PDFs…</span></div>
        </div>
      </section>`;
  }

  function singleCard() {
    return `
      <section class="card dropzone" data-zone>
        <div class="dz-art" aria-hidden="true">
          <span class="dz-sheet s1"></span><span class="dz-sheet s2"></span>
          <span class="dz-sheet s3"><b>PDF</b></span>
        </div>
        <div class="dz-body">
          <h3>Escolha o PDF que vai ser separado</h3>
          <p>Arraste o arquivo para cá ou selecione no computador.</p>
          <div class="dz-actions">
            <button class="btn btn-primary" data-act="pick" type="button"><span class="btn-label">${ic("file-plus-2")}Selecionar PDF</span></button>
          </div>
        </div>
      </section>
      <section class="card single-card"><div class="single-slot"></div></section>`;
  }

  function seg(name, options, value) {
    return `<div class="seg" data-opt="${name}" role="radiogroup">
      <span class="seg-thumb"></span>
      ${options.map(([v, label, icon]) => `<button type="button" role="radio" data-v="${v}" class="${String(v) === String(value) ? "on" : ""}" aria-checked="${String(v) === String(value)}">${icon ? ic(icon) : ""}${esc(label)}</button>`).join("")}
    </div>`;
  }
  function switchCtl(name, checked) {
    return `<label class="switch"><input type="checkbox" data-opt="${name}" ${checked ? "checked" : ""}><span class="switch-track"></span><span class="switch-knob"></span></label>`;
  }
  function pagesField(o, placeholder) {
    return `<div class="collapse" data-collapse style="${o.pagesMode === "specific" ? "" : "height:0"}">
      <div class="opt-row" style="padding-top:2px">
        <div class="opt-label"><strong>Quais páginas?</strong><span>Separe por vírgula. Use hífen para intervalos.</span></div>
        <div class="field-wrap">
          <input class="field" data-opt="pages" value="${esc(o.pages)}" placeholder="${placeholder}" spellcheck="false" autocomplete="off">
          <span class="field-hint" data-hint></span>
        </div>
      </div>
    </div>`;
  }

  function optionsCard(key) {
    const o = state.t[key].opts;
    const keep = `
      <div class="opt-row">
        <div class="opt-label"><strong>Manter estrutura de pastas</strong><span>Recria as subpastas de origem dentro do destino.</span></div>
        ${switchCtl("keepStructure", o.keepStructure)}
      </div>`;
    if (key === "reverse") return `<section class="card options">${keep}</section>`;
    if (key === "merge") {
      return `<section class="card options">
        <div class="opt-row">
          <div class="opt-label"><strong>Ordem dos arquivos</strong><span>Arrastar uma linha muda para “Manual”.</span></div>
          ${seg("sort", SORTS, state.t.merge.sort)}
        </div></section>`;
    }
    if (key === "split") {
      return `<section class="card options">
        <div class="opt-row">
          <div class="opt-label"><strong>Como separar</strong><span>O arquivo original não é alterado.</span></div>
          ${seg("pagesMode", [["all", "Uma página por arquivo", "files"], ["specific", "Páginas específicas", "list-checks"]], o.pagesMode)}
        </div>
        ${pagesField(o, "ex.: 1-3, 5, 8-10")}
      </section>`;
    }
    if (key === "rotate") {
      return `<section class="card options">
        <div class="opt-row">
          <div class="opt-label"><strong>Ângulo</strong><span>No sentido horário.</span></div>
          <div style="display:flex;align-items:center;gap:14px">
            ${seg("angle", [[90, "90°"], [180, "180°"], [270, "270°"]], o.angle)}
            <div class="angle-preview" aria-hidden="true"><div class="angle-page"></div></div>
          </div>
        </div>
        <div class="divider"></div>
        <div class="opt-row">
          <div class="opt-label"><strong>Páginas</strong><span>Escolha se gira o documento inteiro.</span></div>
          ${seg("pagesMode", [["all", "Todas"], ["specific", "Específicas"]], o.pagesMode)}
        </div>
        ${pagesField(o, "ex.: 1-3, 5, 8")}
        <div class="divider"></div>
        ${keep}
      </section>`;
    }
    return "";
  }

  function listCard(key) {
    const t = TOOLS[key];
    return `
      <section class="card list-card">
        <div class="card-head">
          <div class="card-title">${ic(t.kind === "img" ? "images" : "files")}${t.kind === "img" ? "Imagens" : "Arquivos"} <span class="count" data-count>0</span></div>
          <div class="list-tools">
            <button class="btn btn-ghost btn-sm" data-act="clear" type="button"><span class="btn-label">${ic("trash-2")}Limpar lista</span></button>
          </div>
        </div>
        <ul class="list" data-list></ul>
      </section>`;
  }

  /* ---------- Lista ---------- */
  function rowHtml(item, i, key) {
    const t = TOOLS[key];
    return `<li class="row" data-full="${esc(item.full)}" data-i="${i}">
      ${t.reorder ? `<span class="row-handle" title="Arraste para reordenar">${ic("grip-vertical")}</span>` : ""}
      <span class="row-idx">${i + 1}</span>
      <span class="file-ico ${t.kind === "img" ? "img" : ""}">${ic(t.kind === "img" ? "image" : "file-text")}</span>
      <div class="row-main">
        <div class="row-name" title="${esc(item.name)}">${esc(item.name)}</div>
        <div class="row-path" title="${esc(item.full)}"><bdi>${esc(item.path)}</bdi></div>
      </div>
      <span class="row-size">${esc(item.size)}</span>
      <div class="row-actions">
        ${t.reorder ? `<button class="mini" data-act="up" type="button" aria-label="Subir">${ic("chevron-up")}</button>
        <button class="mini" data-act="down" type="button" aria-label="Descer">${ic("chevron-down")}</button>` : ""}
        <button class="mini del" data-act="remove" type="button" aria-label="Remover da lista">${ic("x")}</button>
      </div>
    </li>`;
  }

  function renderList({ enter = null, flip = false, instant = false } = {}) {
    const key = state.active;
    const list = $("[data-list]");
    if (!list) return;
    const items = state.t[key].items;
    const flipState = flip && items.length <= MAX_ROWS ? Flip.getState($$(".row", list)) : null;

    if (!items.length) {
      list.innerHTML = `<li class="empty"><div class="empty-ico">${ic(TOOLS[key].kind === "img" ? "image" : "inbox")}</div>
        Nenhum arquivo na lista ainda.</li>`;
    } else {
      const shown = items.slice(0, MAX_ROWS);
      list.innerHTML = shown.map((it, i) => rowHtml(it, i, key)).join("") +
        (items.length > MAX_ROWS ? `<li class="list-more">e mais ${(items.length - MAX_ROWS).toLocaleString("pt-BR")} arquivos (todos serão processados)</li>` : "");
    }
    if (instant) gsap.set(list.children, { clearProps: "all" });

    if (flipState) {
      Flip.from(flipState, { duration: 0.6, ease: "power3.inOut", stagger: 0.012, targets: $$(".row", list) });
    } else if (enter && enter.size) {
      const fresh = $$(".row", list).filter((r) => enter.has(r.dataset.full));
      gsap.from(fresh, { x: -18, autoAlpha: 0, duration: 0.5, ease: "power3.out", stagger: { each: 0.03, amount: 0.5 } });
    }
    setCount(items.length);
  }

  let lastCount = 0;
  function setCount(n) {
    const el = $("[data-count]");
    if (!el) return;
    const obj = { v: lastCount };
    gsap.to(obj, { v: n, duration: 0.5, ease: "power2.out", onUpdate: () => (el.textContent = Math.round(obj.v).toLocaleString("pt-BR")) });
    if (n !== lastCount) gsap.fromTo(el, { scale: 1.35 }, { scale: 1, duration: 0.5, ease: "back.out(2.5)" });
    lastCount = n;
  }

  function renderSingle(animate) {
    const slot = $(".single-slot");
    if (!slot) return;
    const f = state.t.split.file;
    slot.innerHTML = f
      ? `<div class="single">
          <span class="file-ico">${ic("file-text")}</span>
          <div class="row-main"><div class="row-name">${esc(f.name)}</div><div class="row-path"><bdi>${esc(f.full)}</bdi></div></div>
          <span class="row-size">${esc(f.size)}</span>
          <button class="btn btn-sm" data-act="pick" type="button"><span class="btn-label">${ic("refresh-cw")}Trocar</span></button>
          <button class="mini del" data-act="remove-single" type="button" aria-label="Remover">${ic("x")}</button>
        </div>`
      : `<div class="empty">${"<div class=\"empty-ico\">" + ic("file-question") + "</div>"}Nenhum PDF selecionado.</div>`;
    if (animate) gsap.from(slot.firstElementChild, { y: 12, autoAlpha: 0, scale: 0.98, duration: 0.5, ease: "back.out(1.6)" });
  }

  /* ---------- Interações da tela ---------- */
  function bindView(key) {
    const view = $("#view");
    view.onclick = async (e) => {
      const b = e.target.closest("[data-act]");
      if (!b || state.running === key) return;
      const a = await whenApi;
      const act = b.dataset.act;
      if (act === "pick") {
        const r = await a.pick_files(key);
        if (r && r.state) applyState(r.state, { enterNew: true });
        if (r && key !== "split") reportAdded(r);
      } else if (act === "folder") {
        await a.pick_folder(key);
      } else if (act === "clear") {
        const rows = $$(".row");
        if (!rows.length) return;
        gsap.to(rows.slice(0, 40), {
          x: 24, autoAlpha: 0, duration: 0.25, stagger: 0.015, ease: "power2.in",
          onComplete: async () => applyState(await a.clear(key)),
        });
      } else if (act === "remove") {
        const row = b.closest(".row");
        const i = +row.dataset.i;
        gsap.to(row, {
          x: 30, autoAlpha: 0, duration: 0.22, ease: "power2.in",
          onComplete: async () => {
            const st = await a.remove(key, [i]);
            const fs = Flip.getState($$(".row"));
            row.remove();
            Flip.from(fs, { duration: 0.35, ease: "power3.out" });
            state.t[key].items = st.items;
            setTimeout(() => applyState(st), 360);
          },
        });
      } else if (act === "up" || act === "down") {
        const i = +b.closest(".row").dataset.i;
        const j = act === "up" ? i - 1 : i + 1;
        if (j < 0 || j >= state.t[key].items.length) return;
        applyState(await a.move(key, i, j), { flip: true });
      } else if (act === "remove-single") {
        applyState(await a.clear("split"));
      }
    };

    // Segmentados
    $$(".seg", view).forEach((s) => {
      requestAnimationFrame(() => moveSeg(s, null, true));
      s.addEventListener("click", async (e) => {
        const b = e.target.closest("button");
        if (!b || state.running === key) return;
        const name = s.dataset.opt;
        let v = b.dataset.v;
        moveSeg(s, v);
        if (name === "sort") {
          const a = await whenApi;
          applyState(await a.set_sort(v), { flip: true });
          return;
        }
        if (name === "angle") { v = +v; rotatePreview(v); }
        state.t[key].opts[name] = v;
        if (name === "pagesMode") toggleCollapse(v === "specific");
        updateActionbar();
      });
    });
    if (key === "rotate") rotatePreview(state.t.rotate.opts.angle, true);

    // Switch
    $$("input[type=checkbox][data-opt]", view).forEach((inp) => {
      inp.addEventListener("change", () => {
        state.t[key].opts[inp.dataset.opt] = inp.checked;
        gsap.fromTo(inp.parentElement, { scale: 0.92 }, { scale: 1, duration: 0.5, ease: "elastic.out(1, 0.5)" });
        updateActionbar();
      });
    });

    // Campo de páginas com validação
    const field = $("input[data-opt=pages]", view);
    if (field) {
      let timer;
      const validate = async () => {
        const hint = $("[data-hint]", view);
        const v = field.value.trim();
        state.t[key].opts.pages = v;
        if (!v) { field.classList.remove("invalid"); hint.textContent = ""; hint.classList.remove("err"); return; }
        const r = await (await whenApi).validate_pages(v);
        field.classList.toggle("invalid", !r.ok);
        hint.classList.toggle("err", !r.ok);
        hint.textContent = r.ok ? plural(r.count, "página selecionada", "páginas selecionadas") : r.message;
        if (!r.ok) gsap.fromTo(field, { x: -5 }, { x: 0, duration: 0.45, ease: "elastic.out(1.2, 0.3)" });
      };
      field.addEventListener("input", () => { state.t[key].opts.pages = field.value.trim(); clearTimeout(timer); timer = setTimeout(validate, 280); updateActionbar(); });
      if (field.value) validate();
    }

    // Arrastar para reordenar
    if (TOOLS[key].reorder) {
      const list = $("[data-list]", view);
      list.addEventListener("pointerdown", (e) => {
        const h = e.target.closest(".row-handle");
        if (h && state.running !== key) startDrag(e, h.closest(".row"), key);
      });
    }

    // Spotlight + folhas flutuando na dropzone
    const zone = $("[data-zone]", view);
    if (zone) {
      zone.addEventListener("pointermove", (e) => {
        const r = zone.getBoundingClientRect();
        zone.style.setProperty("--mx", `${e.clientX - r.left}px`);
        zone.style.setProperty("--my", `${e.clientY - r.top}px`);
      });
      if (!RM) {
        const sheets = $$(".dz-sheet", zone);
        gsap.to(sheets[2], { y: -6, duration: 2.4, ease: "sine.inOut", yoyo: true, repeat: -1 });
        zone.addEventListener("pointerenter", () => {
          gsap.to(sheets[0], { rotate: -20, x: -30, duration: 0.6, ease: "back.out(2)" });
          gsap.to(sheets[1], { rotate: 16, x: 30, duration: 0.6, ease: "back.out(2)" });
        });
        zone.addEventListener("pointerleave", () => {
          gsap.to(sheets[0], { rotate: -12, x: -18, duration: 0.6, ease: "power3.out" });
          gsap.to(sheets[1], { rotate: 9, x: 18, duration: 0.6, ease: "power3.out" });
        });
      }
    }
  }

  function moveSeg(s, value, instant = false) {
    if (!s) return;
    const btns = $$("button", s);
    let target = btns.find((b) => b.classList.contains("on"));
    if (value != null) target = btns.find((b) => b.dataset.v === String(value)) || target;
    btns.forEach((b) => { const on = b === target; b.classList.toggle("on", on); b.setAttribute("aria-checked", on); });
    if (!target) return;
    gsap.to($(".seg-thumb", s), { x: target.offsetLeft, width: target.offsetWidth, duration: instant ? 0 : 0.5, ease: "back.out(1.3)" });
  }

  function rotatePreview(angle, instant = false) {
    gsap.to(".angle-page", { rotate: angle, duration: instant ? 0 : 0.8, ease: "back.out(1.8)" });
  }

  function toggleCollapse(open) {
    const c = $("[data-collapse]");
    if (!c) return;
    if (open) {
      gsap.fromTo(c, { height: 0 }, { height: "auto", duration: 0.45, ease: "power3.out", onComplete: () => $("input", c).focus() });
      gsap.fromTo(c.firstElementChild, { autoAlpha: 0, y: -8 }, { autoAlpha: 1, y: 0, duration: 0.4, delay: 0.1 });
    } else {
      gsap.to(c, { height: 0, duration: 0.35, ease: "power3.inOut" });
    }
  }

  function startDrag(e, row, key) {
    e.preventDefault();
    const list = row.parentElement;
    const from = +row.dataset.i;
    const startY = e.clientY;
    let shift = 0;
    row.setPointerCapture(e.pointerId);
    row.classList.add("dragging");
    gsap.to(row, { scale: 1.015, duration: 0.2 });

    const move = (ev) => {
      const dy = ev.clientY - startY;
      gsap.set(row, { y: dy - shift });
      const local = dy - shift;
      const next = row.nextElementSibling;
      const prev = row.previousElementSibling;
      if (next && next.classList.contains("row") && local > next.offsetHeight / 2) {
        const st = Flip.getState(next);
        list.insertBefore(next, row);
        shift += next.offsetHeight + 2;
        gsap.set(row, { y: dy - shift });
        Flip.from(st, { duration: 0.25, ease: "power2.out" });
      } else if (prev && prev.classList.contains("row") && local < -prev.offsetHeight / 2) {
        const st = Flip.getState(prev);
        list.insertBefore(row, prev);
        shift -= prev.offsetHeight + 2;
        gsap.set(row, { y: dy - shift });
        Flip.from(st, { duration: 0.25, ease: "power2.out" });
      }
    };
    const up = async () => {
      row.removeEventListener("pointermove", move);
      row.removeEventListener("pointerup", up);
      row.removeEventListener("pointercancel", up);
      gsap.to(row, { y: 0, scale: 1, duration: 0.35, ease: "back.out(2)", onComplete: () => row.classList.remove("dragging") });
      const rows = $$(".row", list);
      const to = rows.indexOf(row);
      rows.forEach((r, i) => { r.dataset.i = i; $(".row-idx", r).textContent = i + 1; });
      if (to !== from) {
        const st = await (await whenApi).move(key, from, to);
        state.t[key].items = st.items;
        if (st.sort) { state.t[key].sort = st.sort; moveSeg($(".seg[data-opt=sort]"), st.sort); }
      }
    };
    row.addEventListener("pointermove", move);
    row.addEventListener("pointerup", up);
    row.addEventListener("pointercancel", up);
  }

  /* ---------- Barra de ação ---------- */
  const actionbar = document.createElement("div");
  actionbar.className = "actionbar";
  actionbar.innerHTML = `
    <div class="ab-info"><div class="ab-title" data-ab-title></div><div class="ab-sub" data-ab-sub></div></div>
    <div class="progress">
      <div class="prog-top"><span class="prog-label" data-prog-label>Iniciando…</span><span class="prog-pct" data-prog-pct>0%</span></div>
      <div class="bar"><span class="bar-fill" data-bar></span></div>
      <div class="prog-meta"><span data-prog-count></span><span data-prog-time></span></div>
    </div>
    <div class="magnet-wrap"><button class="btn btn-primary btn-lg" data-run type="button"><span class="btn-label" data-run-label></span></button></div>
    <button class="btn btn-danger btn-lg" data-cancel type="button" hidden><span class="btn-label">${ic("square")}Cancelar</span></button>`;

  function summary(key) {
    const o = state.t[key].opts;
    const keep = o.keepStructure ? "mantendo as pastas" : "tudo na mesma pasta";
    const pages = o.pagesMode === "specific" ? (o.pages ? `páginas ${o.pages}` : "informe as páginas") : null;
    switch (key) {
      case "reverse": return `Saída em “PDFs_Invertidos”, ${keep}`;
      case "merge": return `Ordem: ${SORTS.find((s) => s[0] === state.t.merge.sort)[1]} · você escolhe onde salvar`;
      case "split": return pages ? `Extrair ${pages} em um novo arquivo` : "Um arquivo para cada página";
      case "rotate": return `${o.angle}° · ${pages || "todas as páginas"} · ${keep}`;
      case "images": return "Na ordem da lista · você escolhe onde salvar";
    }
    return "";
  }

  function updateActionbar() {
    const key = state.active;
    const t = TOOLS[key];
    const n = t.single ? (state.t.split.file ? 1 : 0) : state.t[key].items.length;
    const noun = t.kind === "img" ? ["imagem", "imagens"] : ["arquivo", "arquivos"];
    $("[data-ab-title]", actionbar).textContent = n
      ? (t.single ? state.t.split.file.name : `${plural(n, noun[0], noun[1])} na lista`)
      : (t.single ? "Nenhum PDF selecionado" : `Nenhum${t.kind === "img" ? "a imagem" : " arquivo"} na lista`);
    $("[data-ab-sub]", actionbar).textContent = n ? summary(key) : "Adicione arquivos para começar";
    $("[data-run-label]", actionbar).innerHTML = `${ic(t.icon)}${esc(t.action)}`;
    const busyElsewhere = state.running && state.running !== key;
    $("[data-run]", actionbar).disabled = !n || !!busyElsewhere;
    if (busyElsewhere) $("[data-ab-sub]", actionbar).textContent = `Aguarde: “${TOOLS[state.running].label}” está em andamento`;
    const runningHere = state.running === key;
    actionbar.classList.toggle("running", runningHere);
    $("[data-run]", actionbar).parentElement.hidden = runningHere;
    $("[data-cancel]", actionbar).hidden = !runningHere;
  }

  async function startRun() {
    const key = state.active;
    if (state.running) return;
    const o = state.t[key].opts;
    if (o.pagesMode === "specific" && !(o.pages || "").trim()) {
      toast("Informe as páginas ou intervalos (ex.: 1-3, 5, 8-10).", "warn");
      const f = $("input[data-opt=pages]");
      if (f) { f.focus(); gsap.fromTo(f, { x: -6 }, { x: 0, duration: 0.5, ease: "elastic.out(1.2, 0.3)" }); }
      return;
    }
    const field = $("input[data-opt=pages]");
    if (o.pagesMode === "specific" && field && field.classList.contains("invalid")) {
      toast("Corrija o intervalo de páginas antes de continuar.", "warn");
      field.focus();
      return;
    }
    const a = await whenApi;
    const r = await a.run(key, o);
    if (!r.started) { if (r.message) toast(r.message, "warn"); return; }
    state.running = key;
    gsap.set($("[data-bar]"), { scaleX: 0 });
    $("[data-prog-pct]").textContent = "0%";
    $("[data-prog-label]").textContent = "Iniciando…";
    $("[data-prog-count]").textContent = "";
    $("[data-prog-time]").textContent = "";
    updateActionbar();
    gsap.from(".actionbar .progress, .actionbar [data-cancel]", { y: 10, autoAlpha: 0, duration: 0.4, stagger: 0.06, ease: "power3.out" });
    $$(".dz-actions .btn, [data-act=clear]").forEach((b) => (b.disabled = true));
  }

  const pct = { v: 0 };
  function updateProgress(p) {
    if (p.tool !== state.running) return;
    const f = p.total ? p.current / p.total : 0;
    gsap.to($("[data-bar]"), { scaleX: f, duration: 0.35, ease: "power2.out", overwrite: true });
    gsap.to(pct, {
      v: f * 100, duration: 0.35, overwrite: true,
      onUpdate: () => { const el = $("[data-prog-pct]"); if (el) el.textContent = `${Math.round(pct.v)}%`; },
    });
    $("[data-prog-label]").textContent = p.label;
    $("[data-prog-count]").textContent = `${p.current.toLocaleString("pt-BR")} de ${p.total.toLocaleString("pt-BR")}`;
    $("[data-prog-time]").textContent = clock(p.elapsed);
  }
  const clock = (s) => { s = Math.round(s); const m = Math.floor(s / 60); return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`; };

  function finishRun(p) {
    gsap.to($("[data-bar]"), { scaleX: 1, duration: 0.3 });
    $("[data-prog-pct]").textContent = "100%";
    setTimeout(() => {
      state.running = null;
      pct.v = 0;
      updateActionbar();
      $$(".dz-actions .btn, [data-act=clear]").forEach((b) => (b.disabled = false));
      openModal(p);
    }, 350);
  }

  /* ---------- Modal de resumo ---------- */
  const modal = $("#modal");
  let lastFocus = null;
  function openModal(p) {
    lastFocus = document.activeElement;
    const nouns = { arquivo: ["arquivo", "arquivos"], página: ["página", "páginas"], imagem: ["imagem", "imagens"] }[p.noun] || ["item", "itens"];
    const ok = !p.cancelled && p.failed === 0 && p.succeeded > 0;
    const bad = p.succeeded === 0;
    const badge = $("#modalBadge");
    badge.className = "modal-badge" + (bad ? " bad" : ok ? "" : " warn");
    $("#modalTitle").textContent = p.cancelled ? "Processamento cancelado" : bad ? "Nada foi gerado" : ok ? "Tudo certo!" : "Concluído com avisos";
    $("#modalSub").textContent = p.cancelled
      ? `${p.processed} de ${p.total} concluídos antes de parar.`
      : bad ? "Nenhum item pôde ser processado. Veja os detalhes abaixo." : `Os arquivos novos estão na pasta de destino. Os originais não foram alterados.`;
    $("#modalStats").innerHTML = `
      <div class="stat ok"><b data-to="${p.succeeded}">0</b><span>${p.succeeded === 1 ? nouns[0] : nouns[1]} com sucesso</span></div>
      <div class="stat ${p.failed ? "err" : ""}"><b data-to="${p.failed}">0</b><span>com erro</span></div>
      <div class="stat"><b>${esc(p.elapsed)}</b><span>tempo total</span></div>`;
    const errs = $("#modalErrors");
    errs.hidden = true;
    errs.innerHTML = p.errors.map((e) => `<div class="err-item"><b>${esc(e.item)}</b><span>${esc(e.message)}</span></div>`).join("");
    $("#modalActions").innerHTML = `
      ${p.outputDir && p.succeeded ? `<button class="btn btn-primary" data-m="open" type="button"><span class="btn-label">${ic("folder-open")}Abrir pasta</span></button>` : ""}
      ${p.errors.length ? `<button class="btn" data-m="errors" type="button"><span class="btn-label">${ic("triangle-alert")}Ver erros</span></button>` : ""}
      <button class="btn btn-ghost" data-m="close" type="button"><span class="btn-label">Fechar</span></button>`;
    $("#modalActions").onclick = async (e) => {
      const b = e.target.closest("[data-m]");
      if (!b) return;
      if (b.dataset.m === "open") (await whenApi).open_folder(p.outputDir);
      if (b.dataset.m === "errors") {
        errs.hidden = !errs.hidden;
        if (!errs.hidden) gsap.from(errs, { height: 0, autoAlpha: 0, duration: 0.4, ease: "power3.out", clearProps: "height" });
      }
      if (b.dataset.m === "close") closeModal();
    };

    modal.hidden = false;
    const box = $(".modal", modal);
    const ring = $(".ring", badge), mark = $(bad ? ".cross" : ".check", badge);
    [ring, mark].forEach((el) => { const L = el.getTotalLength(); gsap.set(el, { strokeDasharray: L, strokeDashoffset: L }); });
    const tl = gsap.timeline();
    tl.fromTo(modal, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.25 })
      .fromTo(box, { y: 40, scale: 0.94, autoAlpha: 0 }, { y: 0, scale: 1, autoAlpha: 1, duration: 0.6, ease: "back.out(1.6)" }, "<")
      .to(ring, { strokeDashoffset: 0, duration: 0.6, ease: "power2.inOut" }, "-=0.3")
      .to(mark, { strokeDashoffset: 0, duration: 0.4, ease: "power3.out" }, "-=0.1")
      .fromTo(badge, { scale: 0.9 }, { scale: 1, duration: 0.6, ease: "elastic.out(1, 0.4)" }, "<")
      .from(".modal h2, .modal-sub, .stat, .modal-actions .btn", { y: 14, autoAlpha: 0, duration: 0.45, stagger: 0.05, ease: "power3.out" }, "-=0.7");
    $$("[data-to]", box).forEach((el) => {
      const o = { v: 0 };
      tl.to(o, { v: +el.dataset.to, duration: 1, ease: "power2.out", onUpdate: () => (el.textContent = Math.round(o.v).toLocaleString("pt-BR")) }, 0.4);
    });
    if (ok && !RM) tl.add(() => confetti($("#confetti")), 0.55);
    setTimeout(() => { const f = $(".modal-actions .btn", modal); if (f) f.focus(); }, 50);
  }
  function closeModal() {
    gsap.to(".modal", { y: 20, scale: 0.97, autoAlpha: 0, duration: 0.25, ease: "power2.in" });
    gsap.to(modal, { autoAlpha: 0, duration: 0.3, onComplete: () => { modal.hidden = true; if (lastFocus) lastFocus.focus(); } });
  }
  modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.hidden) closeModal();
    if (e.key === "Tab" && !modal.hidden) {
      const f = $$("button", modal).filter((b) => !b.hidden && b.offsetParent);
      if (!f.length) return;
      if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
    }
  });

  function confetti(canvas) {
    const box = canvas.getBoundingClientRect();
    const dpr = Math.min(devicePixelRatio, 2);
    canvas.width = box.width * dpr; canvas.height = box.height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    const css = getComputedStyle(document.documentElement);
    const colors = ["--accent", "--accent-2", "--accent-3", "--success", "--warning"].map((v) => css.getPropertyValue(v).trim());
    const cx = box.width / 2, cy = 76;
    const parts = Array.from({ length: 90 }, () => ({
      x: cx, y: cy, r: 3 + Math.random() * 4, c: colors[(Math.random() * colors.length) | 0],
      rot: Math.random() * 6, vr: (Math.random() - 0.5) * 0.4, life: 1,
      sq: Math.random() > 0.5,
    }));
    parts.forEach((p) => {
      const ang = Math.random() * Math.PI * 2, dist = 80 + Math.random() * 220;
      gsap.to(p, { x: cx + Math.cos(ang) * dist, y: cy + Math.sin(ang) * dist * 0.6 + 120 + Math.random() * 160, duration: 1.4 + Math.random() * 0.8, ease: "power3.out" });
      gsap.to(p, { life: 0, duration: 0.6, delay: 1 + Math.random() * 0.8, ease: "power1.in" });
    });
    const tick = () => {
      ctx.clearRect(0, 0, box.width, box.height);
      let alive = false;
      parts.forEach((p) => {
        if (p.life <= 0) return;
        alive = true;
        p.rot += p.vr;
        ctx.save(); ctx.globalAlpha = p.life; ctx.translate(p.x, p.y); ctx.rotate(p.rot); ctx.fillStyle = p.c;
        if (p.sq) ctx.fillRect(-p.r, -p.r / 2, p.r * 2, p.r); else { ctx.beginPath(); ctx.arc(0, 0, p.r / 1.4, 0, 7); ctx.fill(); }
        ctx.restore();
      });
      if (!alive) { gsap.ticker.remove(tick); ctx.clearRect(0, 0, box.width, box.height); }
    };
    gsap.ticker.add(tick);
  }

  /* ---------- Toasts ---------- */
  function toast(msg, kind = "info") {
    const icons = { info: "info", warn: "triangle-alert", error: "circle-alert", success: "check" };
    const el = document.createElement("div");
    el.className = `toast ${kind}`;
    el.setAttribute("role", "status");
    el.innerHTML = `<span class="toast-ico">${ic(icons[kind])}</span><span>${esc(msg)}</span>`;
    $("#toasts").appendChild(el);
    gsap.fromTo(el, { x: 40, autoAlpha: 0, scale: 0.96 }, { x: 0, autoAlpha: 1, scale: 1, duration: 0.5, ease: "back.out(1.6)" });
    gsap.to(el, { x: 30, autoAlpha: 0, duration: 0.35, delay: 3.6, ease: "power2.in", onComplete: () => el.remove() });
  }

  /* ---------- Arrastar arquivos do Explorer ---------- */
  function bindDropOverlay() {
    const ov = $("#dropOverlay");
    let depth = 0;
    const show = (on) => {
      gsap.to(ov, { autoAlpha: on ? 1 : 0, duration: 0.25 });
      if (on) gsap.fromTo(".drop-overlay-icon", { y: 10, scale: 0.9 }, { y: 0, scale: 1, duration: 0.5, ease: "back.out(2)" });
    };
    window.addEventListener("dragenter", (e) => {
      if (!e.dataTransfer || ![...e.dataTransfer.types].includes("Files")) return;
      e.preventDefault();
      if (depth++ === 0) {
        const t = TOOLS[state.active];
        $("#dropOverlayText").textContent = state.running
          ? "Aguarde o processamento terminar"
          : `Solte para adicionar em “${t.label}”`;
        show(true);
      }
    });
    window.addEventListener("dragover", (e) => e.preventDefault());
    window.addEventListener("dragleave", () => { if (--depth <= 0) { depth = 0; show(false); } });
    window.addEventListener("drop", (e) => { e.preventDefault(); depth = 0; show(false); });
  }

  /* ---------- Botão magnético ---------- */
  function magnetic(wrap, force = 0.3) {
    if (!FINE || RM) return;
    const el = wrap.firstElementChild;
    const xTo = gsap.quickTo(el, "x", { duration: 0.8, ease: "elastic.out(1, 0.4)" });
    const yTo = gsap.quickTo(el, "y", { duration: 0.8, ease: "elastic.out(1, 0.4)" });
    wrap.addEventListener("pointermove", (e) => {
      const r = wrap.getBoundingClientRect();
      xTo((e.clientX - (r.left + r.width / 2)) * force);
      yTo((e.clientY - (r.top + r.height / 2)) * force);
    });
    wrap.addEventListener("pointerleave", () => { xTo(0); yTo(0); });
  }

  /* ---------- Tema ---------- */
  function bindTheme() {
    $("#themeToggle").addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("maxpdf-theme", next); } catch (e) { /* sem armazenamento */ }
    });
  }

  /* ---------- Abertura ---------- */
  function intro() {
    const pre = $(".preloader");
    document.documentElement.classList.add("ready");
    const enterApp = () => {
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
      tl.from(".sidebar", { x: -30, autoAlpha: 0, duration: 0.7 })
        .from(".brand, .nav-label, .nav-item, .sidebar-foot", { x: -16, autoAlpha: 0, duration: 0.5, stagger: 0.05 }, "<0.15")
        .add(() => { switchTool(state.active, true); movePill(false); }, "<0.1")
        .from(actionbar, { yPercent: 140, autoAlpha: 0, duration: 0.8, ease: "expo.out" }, "<0.3");
    };
    if (RM) { pre.remove(); switchTool(state.active, true); movePill(false); return; }
    const paths = $$(".draw", pre);
    paths.forEach((p) => { const L = p.getTotalLength(); gsap.set(p, { strokeDasharray: L, strokeDashoffset: L }); });
    gsap.timeline()
      .to(paths, { strokeDashoffset: 0, duration: 0.9, stagger: 0.12, ease: "power2.inOut" })
      .from(".preloader-word span", { yPercent: 110, duration: 0.6, stagger: 0.08, ease: "expo.out" }, "-=0.55")
      .to(".preloader-mark", { scale: 0.92, autoAlpha: 0, duration: 0.4, ease: "power2.in" }, "+=0.15")
      .to(pre, { clipPath: "inset(0 0 100% 0)", duration: 0.7, ease: "expo.inOut" }, "-=0.1")
      .add(enterApp, "-=0.45")
      .add(() => pre.remove());
  }

  /* ---------- Simulação (somente fora do app, para preview) ---------- */
  function createMockApi() {
    const q = { reverse: [], merge: [], rotate: [], images: [] };
    let split = null, sort = "name_asc", n = 0;
    const fake = (tool) => {
      n++;
      const img = tool === "images";
      const name = img ? `Foto_${String(n).padStart(3, "0")}.jpg` : `Lei_${n}_2026.pdf`;
      return { name, path: `Documentos\\Câmara\\${name}`, full: `C:\\Users\\Max\\Documentos\\Câmara\\${name}`, size: `${(Math.random() * 4 + 0.2).toFixed(1)} MB` };
    };
    const st = (tool) => tool === "split" ? { tool, file: split } : { tool, items: q[tool].slice(), sort };
    const delay = (v) => new Promise((r) => setTimeout(() => r(v), 120));
    return {
      set_active() {}, get_info: () => delay({ version: "2.0.0 (preview)" }), get_state: (tool) => delay(st(tool)),
      pick_files: (tool) => {
        if (tool === "split") { split = { name: "Relatorio_Anual.pdf", full: "C:\\Docs\\Relatorio_Anual.pdf", size: "8.4 MB" }; return delay({ state: st(tool) }); }
        const k = 3 + ((Math.random() * 4) | 0);
        for (let i = 0; i < k; i++) q[tool].push(fake(tool));
        return delay({ state: st(tool), added: k, skipped: 0, duplicates: 0 });
      },
      pick_folder: (tool) => {
        let c = 0;
        window.maxpdf.receive({ event: "scan", payload: { tool, count: 0, done: false } });
        const it = setInterval(() => {
          c += 7;
          window.maxpdf.receive({ event: "scan", payload: { tool, count: c, done: false } });
          if (c >= 21) {
            clearInterval(it);
            for (let i = 0; i < 6; i++) q[tool].push(fake(tool));
            window.maxpdf.receive({ event: "scan", payload: { tool, count: 6, added: 6, done: true } });
            window.maxpdf.receive({ event: "state", payload: st(tool) });
          }
        }, 300);
        return delay(true);
      },
      remove: (tool, idx) => { if (tool === "split") split = null; else idx.sort((a, b) => b - a).forEach((i) => q[tool].splice(i, 1)); return delay(st(tool)); },
      clear: (tool) => { if (tool === "split") split = null; else q[tool] = []; return delay(st(tool)); },
      move: (tool, a, b) => { const [x] = q[tool].splice(a, 1); q[tool].splice(b, 0, x); if (tool === "merge") sort = "custom"; return delay(st(tool)); },
      set_sort: (mode) => {
        sort = mode;
        const k = (s) => s.name.replace(/\d+/g, (d) => d.padStart(8, "0"));
        if (mode === "name_asc") q.merge.sort((a, b) => k(a).localeCompare(k(b)));
        if (mode === "name_desc") q.merge.sort((a, b) => k(b).localeCompare(k(a)));
        if (mode === "modified") q.merge.sort(() => Math.random() - 0.5);
        return delay(st("merge"));
      },
      validate_pages: (s) => {
        const ok = /^\s*\d+(\s*-\s*\d+)?(\s*,\s*\d+(\s*-\s*\d+)?)*\s*$/.test(s);
        return delay(ok ? { ok, count: s.split(",").length } : { ok, message: "Formato inválido. Use algo como 1-3, 5, 8-10." });
      },
      open_folder() {}, cancel() { this._cancel = true; },
      run(tool) {
        const total = tool === "split" ? 12 : q[tool].length;
        let i = 0; this._cancel = false; const t0 = Date.now();
        const it = setInterval(() => {
          i++;
          window.maxpdf.receive({ event: "progress", payload: { tool, current: i, total, label: tool === "split" ? `pagina_${i}.pdf` : (q[tool][i - 1] || {}).name, elapsed: (Date.now() - t0) / 1000 } });
          if (i >= total || this._cancel) {
            clearInterval(it);
            const failed = total > 4 ? 1 : 0;
            window.maxpdf.receive({ event: "done", payload: { tool, noun: tool === "split" ? "página" : tool === "images" ? "imagem" : "arquivo", total, succeeded: i - failed, failed, processed: i, cancelled: this._cancel, elapsed: "3 s", outputDir: "C:\\Saida", errors: failed ? [{ item: "Lei_2_2026.pdf", message: "PDF protegido por senha" }] : [] } });
          }
        }, 260);
        return delay({ started: true });
      },
    };
  }

  /* ---------- Início ---------- */
  function init() {
    hydrateIcons();
    buildNav();
    $("#main").appendChild(actionbar);
    $("[data-run]", actionbar).addEventListener("click", startRun);
    $("[data-cancel]", actionbar).addEventListener("click", async () => {
      $("[data-prog-label]").textContent = "Cancelando… o arquivo atual termina antes.";
      $("[data-cancel]").disabled = true;
      (await whenApi).cancel(state.running);
      setTimeout(() => ($("[data-cancel]").disabled = false), 400);
    });
    magnetic($(".magnet-wrap", actionbar));
    bindTheme();
    bindDropOverlay();
    window.addEventListener("resize", () => { movePill(false); $$(".seg").forEach((s) => moveSeg(s, null, true)); });

    whenApi.then(async (a) => {
      api = a;
      const info = await a.get_info();
      $("#version").textContent = `v${info.version}`;
      for (const k of ORDER) {
        const s = await a.get_state(k);
        if (s) applyState(s);
      }
    });
    document.fonts.ready.then(intro);
  }

  init();
})();
