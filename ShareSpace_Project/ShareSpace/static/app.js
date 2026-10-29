document.addEventListener("DOMContentLoaded", () => {
  const search = document.getElementById("resourceSearch");
  const category = document.getElementById("categoryFilter");
  const cards = [...document.querySelectorAll(".resource-card")];
  const noResults = document.getElementById("noResults");
  function filterResources() {
    if (!search || !category) return;
    const term = search.value.toLowerCase().trim();
    const selected = category.value;
    let shown = 0;
    cards.forEach(card => {
      const matches = card.dataset.name.includes(term) && (!selected || card.dataset.category === selected);
      card.classList.toggle("hidden", !matches);
      if (matches) shown++;
    });
    if (noResults) noResults.classList.toggle("hidden", shown > 0);
  }
  search?.addEventListener("input", filterResources);
  category?.addEventListener("change", filterResources);
  document.querySelectorAll("input[type='datetime-local']").forEach(input => {
    input.addEventListener("change", () => {
      const form = input.closest("form");
      const start = form?.querySelector("[name='start_at']");
      const end = form?.querySelector("[name='end_at']");
      if (start && end && start.value) end.min = start.value;
    });
  });
});
