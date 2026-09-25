/** @odoo-module **/

let observerStarted = false;

function getCurrentModel() {
    const hash = window.location.hash;
    const match = hash.match(/model=([^&]+)/);
    return match ? match[1] : "unknown";
}

function injectToggleButton() {
    if (window.innerWidth < 992) return;

    const formView = document.querySelector(".o_form_view");
    const controlPanel = document.querySelector(".o_control_panel");
    const chatter = document.querySelector(".o-mail-Form-chatter");

    if (!formView || !controlPanel || !chatter) return;
    if (controlPanel.querySelector(".o_toggle_chatter_btn")) return;

    const model = getCurrentModel();

    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-light btn-sm o_toggle_chatter_btn ms-2";
    button.innerHTML = `<i class="fa fa-comments"></i>`;
    button.title = "Toon / Verberg chatter";

    // Restore state
    const saved = localStorage.getItem("chatter_hidden_" + model);
    if (saved === "1") {
        formView.classList.add("o_chatter_hidden");
        button.classList.add("btn-primary");
    }

    button.addEventListener("click", () => {
        const hidden = formView.classList.toggle("o_chatter_hidden");
        button.classList.toggle("btn-primary", hidden);

        localStorage.setItem(
            "chatter_hidden_" + model,
            hidden ? "1" : "0"
        );
    });

    const target =
        controlPanel.querySelector(".o_cp_action_menus") ||
        controlPanel.querySelector(".o_cp_buttons") ||
        controlPanel;

    target.appendChild(button);
}

function startObserver() {
    if (observerStarted) return;
    observerStarted = true;

    const observer = new MutationObserver(() => {
        injectToggleButton();
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startObserver);
} else {
    startObserver();
}
