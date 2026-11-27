// Drag-and-drop ranking for the pilot page. Buttons do the same for keyboard and phones.
(function () {
  const ranked = document.getElementById("ranked");
  const unranked = document.getElementById("unranked");
  const form = document.getElementById("rank-form");
  const dirty = document.getElementById("dirty");
  let dragged = null;

  function acts(li) {
    const inRanked = li.parentElement === ranked;
    let box = li.querySelector(".acts");
    if (!box) { box = document.createElement("span"); box.className = "acts"; li.appendChild(box); }
    box.innerHTML = inRanked
      ? '<button type="button" data-act="up" title="Move up">↑</button>' +
        '<button type="button" data-act="down" title="Move down">↓</button>' +
        '<button type="button" data-act="remove" title="Remove from ranking">✕</button>'
      : '<button type="button" data-act="add" title="Add to ranking">+</button>';
  }

  function sortUnranked() {
    [...unranked.children].sort((a, b) => a.dataset.key.localeCompare(b.dataset.key))
      .forEach(li => unranked.appendChild(li));
  }

  function changed() {
    [...ranked.children, ...unranked.children].forEach(acts);
    ranked.parentElement.classList.toggle("is-empty", ranked.children.length === 0);
    if (dirty) dirty.hidden = false;
  }

  function after(list, y) {
    const items = [...list.querySelectorAll("li:not(.dragging)")];
    return items.find(li => { const r = li.getBoundingClientRect(); return y < r.top + r.height / 2; }) || null;
  }

  [ranked, unranked].forEach(list => {
    list.addEventListener("dragstart", e => {
      dragged = e.target.closest("li"); dragged.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", dragged.dataset.key);
    });
    list.addEventListener("dragend", () => {
      if (dragged) dragged.classList.remove("dragging");
      if (dragged && dragged.parentElement === unranked) sortUnranked();
      dragged = null; changed();
    });
    list.addEventListener("dragover", e => {
      e.preventDefault();
      if (!dragged) return;
      if (list === ranked) list.insertBefore(dragged, after(list, e.clientY));
      else if (dragged.parentElement !== unranked) unranked.appendChild(dragged);
    });
  });
  ranked.parentElement.addEventListener("dragover", e => {
    if (dragged && e.target === ranked.parentElement) { e.preventDefault(); ranked.appendChild(dragged); }
  });

  form.addEventListener("click", e => {
    const btn = e.target.closest("button[data-act]");
    if (!btn) return;
    const li = btn.closest("li");
    const act = btn.dataset.act;
    if (act === "add") ranked.appendChild(li);
    if (act === "remove") { unranked.appendChild(li); sortUnranked(); }
    if (act === "up" && li.previousElementSibling) ranked.insertBefore(li, li.previousElementSibling);
    if (act === "down" && li.nextElementSibling) ranked.insertBefore(li.nextElementSibling, li);
    changed();
  });

  form.addEventListener("submit", () => {
    form.querySelectorAll("input[name=ranked]").forEach(i => i.remove());
    [...ranked.children].forEach(li => {
      const i = document.createElement("input");
      i.type = "hidden"; i.name = "ranked"; i.value = li.dataset.key; form.appendChild(i);
    });
    window.onbeforeunload = null;
  });

  window.onbeforeunload = () => (dirty && !dirty.hidden ? "unsaved" : undefined);
  ranked.parentElement.classList.toggle("is-empty", ranked.children.length === 0);
})();
