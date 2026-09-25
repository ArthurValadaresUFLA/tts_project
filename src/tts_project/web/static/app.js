// Lógica de front-end: envia o formulário, faz polling do status do job
// e, quando pronto, carrega o áudio no player.

const form = document.getElementById("tts-form");
const submitBtn = document.getElementById("submit-btn");
const progressSection = document.getElementById("progress-section");
const progressBar = document.getElementById("progress-bar");
const statusText = document.getElementById("status-text");
const resultSection = document.getElementById("result-section");
const resultText = document.getElementById("result-text");
const audioPlayer = document.getElementById("audio-player");
const errorText = document.getElementById("error-text");

const POLL_INTERVAL_MS = 800;

function resetUI() {
  errorText.hidden = true;
  resultSection.hidden = true;
  progressSection.hidden = false;
  progressBar.value = 0;
  statusText.textContent = "Enviando...";
  submitBtn.disabled = true;
}

function showError(message) {
  errorText.textContent = message;
  errorText.hidden = false;
  progressSection.hidden = true;
  submitBtn.disabled = false;
}

async function pollStatus(jobId) {
  try {
    const response = await fetch(`/api/status/${jobId}`);
    const data = await response.json();

    if (!response.ok) {
      showError(data.error || "Erro ao consultar o status.");
      return;
    }

    progressBar.value = data.progress;
    statusText.textContent = `Processando... ${data.progress}%`;

    if (data.status === "done") {
      progressSection.hidden = true;
      resultText.textContent = `Concluído (idioma: ${data.detected_language}).`;
      audioPlayer.src = `/api/audio/${jobId}`;
      resultSection.hidden = false;
      submitBtn.disabled = false;
      return;
    }

    if (data.status === "error") {
      showError(data.error_message || "Falha na síntese.");
      return;
    }

    setTimeout(() => pollStatus(jobId), POLL_INTERVAL_MS);
  } catch (err) {
    showError("Erro de comunicação com o servidor.");
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resetUI();

  const formData = new FormData(form);

  try {
    const response = await fetch("/api/synthesize", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
      showError(data.error || "Erro ao iniciar a síntese.");
      return;
    }

    pollStatus(data.job_id);
  } catch (err) {
    showError("Erro de comunicação com o servidor.");
  }
});
