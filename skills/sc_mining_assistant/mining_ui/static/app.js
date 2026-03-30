/* SC Mining Interface — Dashboard */
/* Author: Mallachi */

const content = document.getElementById("content");

// ------------------------------------------------------------------ //
// Tab routing
// ------------------------------------------------------------------ //

let currentTab = "dashboard";

document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
        document.querySelector(".tab.active")?.classList.remove("active");
        btn.classList.add("active");
        currentTab = btn.dataset.tab;
        loadTab();
    });
});

function loadTab() {
    switch (currentTab) {
        case "dashboard":
            renderDashboard();
            break;
    }
}

// ------------------------------------------------------------------ //
// Dashboard
// ------------------------------------------------------------------ //

function renderDashboard() {
    content.innerHTML = `<div class="empty-state">
        <p>Mining data library loading...<br>
        Data files will be available here once configured.</p>
    </div>`;
}

// ------------------------------------------------------------------ //
// Initial load
// ------------------------------------------------------------------ //

loadTab();
