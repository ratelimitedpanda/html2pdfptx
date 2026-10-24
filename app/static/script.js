const form = document.getElementById("convert-form");
const fileInput = document.getElementById("file");
const button = document.getElementById("submit-btn");
const result = document.getElementById("result");
const status = document.getElementById("status");
const grid = document.getElementById("grid");
const picked = document.getElementById("picked");
const formatSelect = document.getElementById("format");
const downloadButton = document.getElementById("download-btn");

const POLL_INTERVAL = 700;
const FILE_TYPES = {
    pdf: { description: "PDF", accept: { "application/pdf": [".pdf"] } },
    pptx: {
        description: "PowerPoint",
        accept: { "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"] },
    },
};

let jobId = null;
let jobName = "presentation";
let jobMode = null;
const excluded = new Set();

const modeSelect = document.getElementById("mode");

function updateOptions() {
    document.querySelectorAll(".option").forEach((option) => {
        option.hidden = !option.dataset.modes.split(" ").includes(modeSelect.value);
    });
}

modeSelect.addEventListener("change", updateOptions);
updateOptions();

fileInput.addEventListener("change", () => showFile(fileInput.files[0]));

function showFile(file) {
    if (file) {
        jobName = file.name.replace(/\.[^.]+$/, "");
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    button.disabled = true;
    downloadButton.disabled = true;
    button.textContent = "Обработка...";
    grid.innerHTML = "";
    excluded.clear();
    jobMode = null;
    picked.textContent = "";
    result.hidden = true;
    showStatus("Конвертирую презентацию...");

    try {
        const response = await fetch("/convert", { method: "POST", body: new FormData(form) });
        if (!response.ok) {
            throw new Error(await response.text());
        }
        jobId = (await response.json()).id;
        await waitForSlides();
    } catch (err) {
        showStatus("Ошибка при обработке: " + err.message, "error");
    } finally {
        button.disabled = false;
        button.textContent = "Конвертировать";
    }
});

async function waitForSlides() {
    while (true) {
        const response = await fetch(`/jobs/${jobId}`);
        const job = await response.json();

        if (job.mode !== jobMode) {
            jobMode = job.mode;
            grid.innerHTML = "";
        }
        for (let i = grid.children.length; i < job.count; i++) {
            addThumb(i);
        }

        if (job.status === "done") {
            showStatus(job.message, "ok");
            downloadButton.disabled = false;
            updatePicked();
            return;
        }
        if (job.status === "error") {
            throw new Error(job.message);
        }

        if (job.count) {
            result.hidden = false;
            showStatus(`Обработано слайдов: ${job.count}${job.total ? " из " + job.total : ""}...`);
        }
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL));
    }
}

function showStatus(text, kind = "") {
    status.className = kind;
    status.style.display = "block";
    status.textContent = text;
}

function addThumb(index) {
    const thumb = document.createElement("div");
    thumb.className = "thumb";
    thumb.innerHTML = `<img loading="lazy" src="/jobs/${jobId}/slides/${index}.png?mode=${jobMode}" alt="Слайд ${index + 1}"><span>${String(index + 1).padStart(2, "0")}</span>`;

    let clickTimer = null;
    thumb.addEventListener("click", () => {
        clearTimeout(clickTimer);
        clickTimer = setTimeout(() => {
            excluded.has(index) ? excluded.delete(index) : excluded.add(index);
            thumb.classList.toggle("off", excluded.has(index));
            updatePicked();
        }, 220);
    });
    thumb.addEventListener("dblclick", () => {
        clearTimeout(clickTimer);
        const viewer = document.getElementById("viewer");
        viewer.querySelector("img").src = thumb.querySelector("img").src;
        viewer.showModal();
    });

    grid.appendChild(thumb);
}

function selectedSlides() {
    return [...grid.children].map((_, i) => i).filter((i) => !excluded.has(i));
}

function updatePicked() {
    const total = grid.children.length;
    picked.textContent = excluded.size ? `В файл войдёт ${selectedSlides().length} из ${total}.` : "";
}

formatSelect.addEventListener("change", updateDownloadLabel);
updateDownloadLabel();

function updateDownloadLabel() {
    downloadButton.textContent = `Скачать ${formatSelect.value.toUpperCase()}`;
}

downloadButton.addEventListener("click", download);

async function download() {
    const format = formatSelect.value;
    const slides = selectedSlides();
    if (!slides.length) {
        alert("Не выбрано ни одного слайда");
        return;
    }
    const suggestedName = `${jobName}.${format}`;

    let fileHandle = null;
    if (window.showSaveFilePicker) {
        try {
            fileHandle = await window.showSaveFilePicker({ suggestedName, types: [FILE_TYPES[format]] });
        } catch (err) {
            if (err.name === "AbortError") return;
            throw err;
        }
    }

    downloadButton.disabled = true;
    downloadButton.textContent = "Собираю...";

    try {
        const query = excluded.size ? `&slides=${slides.join(",")}` : "";
        const response = await fetch(`/jobs/${jobId}/download?format=${format}${query}`);
        if (!response.ok) {
            throw new Error(await response.text());
        }

        const blob = await response.blob();

        if (fileHandle) {
            const writable = await fileHandle.createWritable();
            await writable.write(blob);
            await writable.close();
        } else {
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = suggestedName;
            link.click();
            URL.revokeObjectURL(link.href);
        }
    } catch (err) {
        alert("Не удалось собрать файл: " + err.message);
    } finally {
        downloadButton.disabled = false;
        updateDownloadLabel();
    }
}
