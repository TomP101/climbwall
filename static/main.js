document.addEventListener("DOMContentLoaded", () => {
    const routesList = document.getElementById("routes-list");
    const filterType = document.getElementById("filter-type");
    const filterGrade = document.getElementById("filter-grade");
    const filterSector = document.getElementById("filter-sector");
    const sortAscBtn = document.getElementById("sort-grade-asc");
    const sortDescBtn = document.getElementById("sort-grade-desc");
    const routeOfTheDay = document.getElementById("route-of-the-day");
    const themeToggle = document.getElementById("theme-toggle");
    const body = document.body;
    const THEME_KEY = "climbwall-theme";

    /* -------------------------------
       FILTROWANIE, SORTOWANIE, PROPOZYCJA DNIA
    -------------------------------- */
    if (routesList) {
        const cards = Array.from(routesList.querySelectorAll(".route-card"));

        function applyFilters() {
            const typeVal = filterType ? filterType.value : "all";
            const gradeVal = filterGrade ? filterGrade.value : "all";
            const sectorVal = filterSector ? filterSector.value : "all";

            cards.forEach(card => {
                const cardType = card.dataset.type;
                const cardGrade = card.dataset.grade;
                const cardSector = card.dataset.sector;

                let visible = true;

                if (typeVal !== "all" && cardType !== typeVal) {
                    visible = false;
                }

                if (gradeVal !== "all") {
                    if (cardGrade < gradeVal) {
                        visible = false;
                    }
                }

                if (sectorVal !== "all" && cardSector !== sectorVal) {
                    visible = false;
                }

                card.style.display = visible ? "block" : "none";
            });
        }

        if (filterType) filterType.addEventListener("change", applyFilters);
        if (filterGrade) filterGrade.addEventListener("change", applyFilters);
        if (filterSector) filterSector.addEventListener("change", applyFilters);

        function sortCards(direction = "asc") {
            const sorted = cards.slice().sort((a, b) => {
                const gradeA = a.dataset.grade;
                const gradeB = b.dataset.grade;
                if (gradeA < gradeB) return direction === "asc" ? -1 : 1;
                if (gradeA > gradeB) return direction === "asc" ? 1 : -1;
                return 0;
            });

            sorted.forEach(card => routesList.appendChild(card));
        }

        if (sortAscBtn) sortAscBtn.addEventListener("click", () => sortCards("asc"));
        if (sortDescBtn) sortDescBtn.addEventListener("click", () => sortCards("desc"));

        if (routeOfTheDay && cards.length > 0) {
            const randomCard = cards[Math.floor(Math.random() * cards.length)];
            routeOfTheDay.innerHTML = randomCard.outerHTML;
        }
    }

    /* -------------------------------
       DARK / LIGHT THEME
    -------------------------------- */
    function updateThemeButtonLabel(theme) {
        if (!themeToggle) return;
        if (theme === "dark") {
            themeToggle.textContent = "☀️ Tryb jasny";
        } else {
            themeToggle.textContent = "🌙 Tryb ciemny";
        }
    }

    function applyTheme(theme) {
        if (theme === "dark") {
            body.classList.add("dark-theme");
        } else {
            body.classList.remove("dark-theme");
        }
        updateThemeButtonLabel(theme);
    }

    // odczyt z localStorage
    const storedTheme = localStorage.getItem(THEME_KEY);
    if (storedTheme === "dark" || storedTheme === "light") {
        applyTheme(storedTheme);
    } else {
        applyTheme("light");
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const current = body.classList.contains("dark-theme") ? "dark" : "light";
            const next = current === "dark" ? "light" : "dark";
            applyTheme(next);
            localStorage.setItem(THEME_KEY, next);
        });
    }
});
