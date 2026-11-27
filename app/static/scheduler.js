// Admin calendar: hover tooltips with the assignment explanation, click to move a vacation.
(function () {
  const tip = document.getElementById("tip");
  const table = document.querySelector("table.cal");
  if (!table) return;
  table.addEventListener("mouseover", e => {
    const td = e.target.closest("td[data-tip]");
    if (!td) { tip.hidden = true; return; }
    tip.textContent = td.dataset.tip;
    tip.hidden = false;
    const r = td.getBoundingClientRect();
    const left = Math.min(r.left, window.innerWidth - 380);
    tip.style.left = Math.max(8, left) + "px";
    tip.style.top = (r.bottom + 6) + "px";
  });
  table.addEventListener("mouseleave", () => { tip.hidden = true; });

  if (table.dataset.status !== "draft") return;
  table.classList.add("editable");
  table.addEventListener("click", e => {
    const td = e.target.closest("td[data-period]");
    if (!td) return;
    const form = document.getElementById("assign-form");
    const isVac = td.classList.contains("vac");
    const msg = isVac
      ? `Remove ${td.dataset.name}'s vacation (${td.dataset.label})? They will have no week until you pick one.`
      : `Move ${td.dataset.name}'s vacation to ${td.dataset.label}?`;
    if (!confirm(msg)) return;
    form.user_id.value = td.dataset.user;
    form.period.value = isVac ? "" : td.dataset.period;
    form.submit();
  });
})();
