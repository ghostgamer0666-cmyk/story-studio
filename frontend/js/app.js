const AppState = {
    selectedGenre: "horror",
    narratorFile: null,
    narratorObjectUrl: null,
    characterSlots: [],
    activeProjectId: null,
    pollTimer: null,
};

const els = {
    serverBadge: document.getElementById("server-status-badge"),
    serverText: document.getElementById("server-status-text"),
    screenCreate: document.getElementById("screen-create"),
    screenProgress: document.getElementById("screen-progress"),
    screenResult: document.getElementById("screen-result"),
    projectNameInput: document.getElementById("project-name"),
    genreGrid: document.getElementById("genre-grid"),
    previousChoiceSelect: document.getElementById("previous-choice"),
    narratorFileInput: document.getElementById("narrator-file-input"),
    narratorEmptyState: document.getElementById("narrator-empty-state"),
    narratorLoadedState: document.getElementById("narrator-loaded-state"),
    narratorFileName: document.getElementById("narrator-file-name"),
    narratorFileSize: document.getElementById("narrator-file-size"),
    narratorAudioPreview: document.getElementById("narrator-audio-preview"),
    btnPickNarrator: document.getElementById("btn-pick-narrator"),
    btnChangeNarrator: document.getElementById("btn-change-narrator"),
    btnRemoveNarrator: document.getElementById("btn-remove-narrator"),
    characterListContainer: document.getElementById("character-list-container"),
    btnAddCharacter: document.getElementById("btn-add-character"),
    formErrorBox: document.getElementById("form-error-box"),
    btnStartCreate: document.getElementById("btn-start-create"),
    progressPercentText: document.getElementById("progress-percent-text"),
    progressProjectTitle: document.getElementById("progress-project-title"),
    progressCurrentLabel: document.getElementById("progress-current-label"),
    progressBarFill: document.getElementById("progress-bar-fill"),
    resultProjectTitle: document.getElementById("result-project-title"),
    resultMetaInfo: document.getElementById("result-meta-info"),
    resultVideoPlayer: document.getElementById("result-video-player"),
    videoPlaceholderNotice: document.getElementById("video-placeholder-notice"),
    placeholderStatusMsg: document.getElementById("placeholder-status-msg"),
    resultChoicesList: document.getElementById("result-choices-list"),
    btnExportMp4: document.getElementById("btn-export-mp4"),
    btnNewProject: document.getElementById("btn-new-project"),
};

function formatBytes(bytes) {
    if (!bytes || bytes === 0) return "0 KB";
    const mb = bytes / (1024 * 1024);
    if (mb >= 1) return `${mb.toFixed(2)} MB`;
    return `${(bytes / 1024).toFixed(1)} KB`;
}

function showError(message) {
    if (!message) {
        els.formErrorBox.classList.add("hidden");
        els.formErrorBox.textContent = "";
        return;
    }
    els.formErrorBox.textContent = message;
    els.formErrorBox.classList.remove("hidden");
}

function switchScreen(screenName) {
    els.screenCreate.classList.remove("active");
    els.screenProgress.classList.remove("active");
    els.screenResult.classList.remove("active");

    if (screenName === "create") els.screenCreate.classList.add("active");
    if (screenName === "progress") els.screenProgress.classList.add("active");
    if (screenName === "result") els.screenResult.classList.add("active");
    window.scrollTo({ top: 0, behavior: "smooth" });
}

async function checkServerHealth() {
    try {
        const res = await fetch("/api/health");
        if (!res.ok) throw new Error("Sunucu yanıt vermedi");
        const data = await res.json();
        els.serverBadge.className = "status-badge online";
        els.serverText.textContent = `Sunucu Hazır (${data.resolution})`;
    } catch (err) {
        els.serverBadge.className = "status-badge offline";
        els.serverText.textContent = "Sunucu Bağlantısı Yok";
    }
}

function initGenreSelector() {
    const chips = els.genreGrid.querySelectorAll(".genre-chip");
    chips.forEach((chip) => {
        chip.addEventListener("click", () => {
            chips.forEach((c) => c.classList.remove("selected"));
            chip.classList.add("selected");
            AppState.selectedGenre = chip.getAttribute("data-genre");
        });
    });
}

function initNarratorUpload() {
    els.btnPickNarrator.addEventListener("click", () => els.narratorFileInput.click());
    els.btnChangeNarrator.addEventListener("click", () => els.narratorFileInput.click());

    els.btnRemoveNarrator.addEventListener("click", () => {
        if (AppState.narratorObjectUrl) URL.revokeObjectURL(AppState.narratorObjectUrl);
        AppState.narratorFile = null;
        AppState.narratorObjectUrl = null;
        els.narratorFileInput.value = "";
        els.narratorAudioPreview.removeAttribute("src");
        els.narratorLoadedState.classList.add("hidden");
        els.narratorEmptyState.classList.remove("hidden");
    });

    els.narratorFileInput.addEventListener("change", (e) => {
        const file = e.target.files && e.target.files[0];
        if (!file) return;
        if (AppState.narratorObjectUrl) URL.revokeObjectURL(AppState.narratorObjectUrl);

        AppState.narratorFile = file;
        AppState.narratorObjectUrl = URL.createObjectURL(file);

        els.narratorFileName.textContent = file.name;
        els.narratorFileSize.textContent = formatBytes(file.size);
        els.narratorAudioPreview.src = AppState.narratorObjectUrl;

        els.narratorEmptyState.classList.add("hidden");
        els.narratorLoadedState.classList.remove("hidden");
        showError(null);
    });
}

function addCharacterSlot() {
    const slotId = `slot_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
    const indexNumber = AppState.characterSlots.length + 1;
    AppState.characterSlots.push({
        id: slotId,
        characterName: `karakter_${indexNumber}`,
        roleType: indexNumber === 1 ? "main" : "supporting",
        file: null,
        objectUrl: null,
    });
    renderCharacterSlots();
}

function removeCharacterSlot(slotId) {
    const target = AppState.characterSlots.find((s) => s.id === slotId);
    if (target && target.objectUrl) URL.revokeObjectURL(target.objectUrl);
    AppState.characterSlots = AppState.characterSlots.filter((s) => s.id !== slotId);
    renderCharacterSlots();
}

function renderCharacterSlots() {
    els.characterListContainer.innerHTML = "";
    AppState.characterSlots.forEach((slot, idx) => {
        const card = document.createElement("div");
        card.className = "character-slot-card";
        card.innerHTML = `
            <div class="character-slot-header">
                <span class="character-slot-title">🎭 Karakter #${idx + 1}</span>
                <button type="button" class="btn btn-small btn-danger" data-remove="${slot.id}" style="flex:0; padding:4px 10px;">Kaldır</button>
            </div>
            <div class="char-inputs-grid">
                <input type="text" class="text-input char-name-input" placeholder="Karakter Adı" value="${slot.characterName}" />
                <select class="select-input char-role-select">
                    <option value="main" ${slot.roleType === "main" ? "selected" : ""}>Ana Karakter</option>
                    <option value="supporting" ${slot.roleType === "supporting" ? "selected" : ""}>Yan Karakter</option>
                    <option value="monster" ${slot.roleType === "monster" ? "selected" : ""}>Canavar</option>
                </select>
            </div>
            <input type="file" accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg" class="hidden-file-input char-file-input" />
            <div class="char-file-area">
                ${slot.file ? `
                    <p class="file-name">🎵 ${slot.file.name} (${formatBytes(slot.file.size)})</p>
                    <audio controls preload="metadata" src="${slot.objectUrl}" class="audio-player"></audio>
                    <button type="button" class="btn btn-small btn-outline char-pick-btn" style="width:100%;">Değiştir</button>
                ` : `
                    <button type="button" class="btn btn-secondary char-pick-btn" style="width:100%;">📂 Ses Dosyası Seç</button>
                `}
            </div>
        `;

        card.querySelector(".char-name-input").addEventListener("input", (e) => { slot.characterName = e.target.value; });
        card.querySelector(".char-role-select").addEventListener("change", (e) => { slot.roleType = e.target.value; });
        card.querySelector("[data-remove]").addEventListener("click", () => removeCharacterSlot(slot.id));

        const fileInput = card.querySelector(".char-file-input");
        card.querySelector(".char-pick-btn").addEventListener("click", () => fileInput.click());

        fileInput.addEventListener("change", (e) => {
            const f = e.target.files && e.target.files[0];
            if (!f) return;
            if (slot.objectUrl) URL.revokeObjectURL(slot.objectUrl);
            slot.file = f;
            slot.objectUrl = URL.createObjectURL(f);
            const stem = f.name.replace(/\.[^/.]+$/, "");
            if (slot.characterName.startsWith("karakter_") && stem) slot.characterName = stem;
            renderCharacterSlots();
        });

        els.characterListContainer.appendChild(card);
    });
}

async function startProjectCreation() {
    showError(null);
    if (!AppState.narratorFile) {
        showError("Lütfen önce Anlatıcı Ses dosyasını yükleyin.");
        return;
    }

    for (let i = 0; i < AppState.characterSlots.length; i++) {
        if (!AppState.characterSlots[i].file) {
            showError(`Karakter #${i + 1} için ses dosyası seçilmedi.`);
            return;
        }
    }

    const projectName = els.projectNameInput.value.trim() || "Otomatik Hikâye Videosu";
    const previousChoice = els.previousChoiceSelect.value;

    const formData = new FormData();
    formData.append("project_name", projectName);
    formData.append("genre", AppState.selectedGenre);
    if (previousChoice) formData.append("previous_choice", previousChoice);
    formData.append("narrator_audio", AppState.narratorFile);

    const charMetaList = [];
    AppState.characterSlots.forEach((slot) => {
        if (slot.file) {
            formData.append("character_audios", slot.file);
            charMetaList.push({ character_name: slot.characterName.trim(), role_type: slot.roleType });
        }
    });
    formData.append("character_metadata", JSON.stringify(charMetaList));

    els.btnStartCreate.disabled = true;
    els.btnStartCreate.textContent = "Yükleniyor...";

    try {
        const response = await fetch("/api/projects/create", { method: "POST", body: formData });
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || "Sunucu hatası.");
        }
        const statusData = await response.json();
        AppState.activeProjectId = statusData.project_id;
        els.progressProjectTitle.textContent = statusData.project_name;
        switchScreen("progress");
        updateProgressUI(statusData);
        startPollingStatus(statusData.project_id);
    } catch (err) {
        showError(err.message);
    } finally {
        els.btnStartCreate.disabled = false;
        els.btnStartCreate.textContent = "✨ Videoyu Otomatik Oluştur";
    }
}

function startPollingStatus(projectId) {
    if (AppState.pollTimer) clearInterval(AppState.pollTimer);
    AppState.pollTimer = setInterval(async () => {
        try {
            const res = await fetch(`/api/projects/${projectId}/status`);
            if (!res.ok) return;
            const data = await res.json();
            updateProgressUI(data);

            if (data.status === "completed") {
                clearInterval(AppState.pollTimer);
                showResultScreen(data);
            } else if (data.status === "failed") {
                clearInterval(AppState.pollTimer);
                els.progressCurrentLabel.textContent = data.error_message || "Hata oluştu.";
            }
        } catch (e) {}
    }, 1000);
}

function updateProgressUI(data) {
    els.progressPercentText.textContent = `${data.progress}%`;
    els.progressBarFill.style.width = `${data.progress}%`;
    els.progressCurrentLabel.textContent = data.current_step_label;

    const currentIdx = data.step_index || 1;
    for (let i = 1; i <= 5; i++) {
        const item = document.getElementById(`step-item-${i}`);
        if (!item) continue;
        item.classList.remove("active", "done");
        if (i < currentIdx) item.classList.add("done");
        else if (i === currentIdx) item.classList.add("active");
    }
}

function showResultScreen(data) {
    els.resultProjectTitle.textContent = data.project_name;
    els.resultMetaInfo.textContent = `1080x1920 • 9:16 • 30 FPS • ${data.scene_count || 0} Sahne`;

    if (data.video_url) {
        els.videoPlaceholderNotice.classList.add("hidden");
        els.resultVideoPlayer.classList.remove("hidden");
        els.resultVideoPlayer.src = data.video_url;
    }

    els.resultChoicesList.innerHTML = "";
    (data.interactive_choices || []).forEach((choice) => {
        const div = document.createElement("div");
        div.className = "choice-card";
        div.innerHTML = `
            <span class="choice-key">${choice.key}</span>
            <div><strong>${choice.text}</strong><div style="font-size:11px; color:#94a3b8;">${choice.consequence_hint || ""}</div></div>
        `;
        els.resultChoicesList.appendChild(div);
    });

    switchScreen("result");
}

document.addEventListener("DOMContentLoaded", () => {
    checkServerHealth();
    initGenreSelector();
    initNarratorUpload();
    els.btnAddCharacter.addEventListener("click", addCharacterSlot);
    els.btnStartCreate.addEventListener("click", startProjectCreation);
    els.btnExportMp4.addEventListener("click", () => {
        if (!AppState.activeProjectId) return;
        window.location.href = `/api/projects/${AppState.activeProjectId}/download`;
    });
    els.btnNewProject.addEventListener("click", () => switchScreen("create"));
});
