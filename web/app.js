(() => {
  "use strict";

  const config = window.PACTOLS_APP_CONFIG || {};
  const apiBaseUrl = String(config.apiBaseUrl || "").replace(/\/$/, "");
  const allowedUsers = new Set(config.allowedUsers || []);
  const pollIntervalMs = Number(config.pollIntervalMs) || 5000;

  const elements = {
    login: document.querySelector("#login-button"),
    logout: document.querySelector("#logout-button"),
    sessionBar: document.querySelector("#session-bar"),
    sessionLabel: document.querySelector("#session-label"),
    dropPanel: document.querySelector("#drop-panel"),
    fileInput: document.querySelector("#file-input"),
    selectButton: document.querySelector("#select-button"),
    selectedFile: document.querySelector("#selected-file"),
    selectedFileName: document.querySelector("#selected-file-name"),
    selectedFileSize: document.querySelector("#selected-file-size"),
    removeFile: document.querySelector("#remove-file-button"),
    publicNotice: document.querySelector("#public-notice"),
    publicConfirmation: document.querySelector("#public-confirmation"),
    submit: document.querySelector("#submit-button"),
    uploadStatus: document.querySelector("#upload-status"),
    progressPanel: document.querySelector("#progress-panel"),
    progressMessage: document.querySelector("#progress-message"),
    resultsPanel: document.querySelector("#results-panel"),
    resultsSummary: document.querySelector("#results-summary"),
    downloadXml: document.querySelector("#download-xml"),
    downloadTxt: document.querySelector("#download-txt"),
    downloadCsv: document.querySelector("#download-csv"),
    newTreatment: document.querySelector("#new-treatment-button"),
    steps: {
      upload: document.querySelector("#step-upload"),
      workflow: document.querySelector("#step-workflow"),
      results: document.querySelector("#step-results"),
    },
  };

  const state = {
    user: null,
    file: null,
    pollTimer: null,
    session: window.sessionStorage.getItem("pactolsSession") || "",
  };

  const callbackSession = new URLSearchParams(window.location.hash.slice(1)).get("session");
  if (callbackSession) {
    state.session = callbackSession;
    window.sessionStorage.setItem("pactolsSession", callbackSession);
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
  }

  function apiUrl(path) {
    return `${apiBaseUrl}${path}`;
  }

  async function api(path, options = {}) {
    if (!apiBaseUrl) {
      throw new Error("Le service d’authentification n’est pas encore configuré.");
    }
    const response = await fetch(apiUrl(path), {
      headers: {
        ...(state.session ? { Authorization: `Bearer ${state.session}` } : {}),
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
      ...options,
    });
    const body = response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(body?.message || body?.detail || `Erreur du service (${response.status}).`);
    }
    return body;
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} octets`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
  }

  function setStatus(message, type = "neutral") {
    elements.uploadStatus.textContent = message;
    elements.uploadStatus.dataset.type = type;
  }

  function updateSession(user) {
    state.user = user;
    const authorized = Boolean(user && allowedUsers.has(user.login));
    elements.sessionBar.dataset.state = authorized ? "connected" : "disconnected";
    elements.login.hidden = authorized;
    elements.logout.hidden = !authorized;
    elements.sessionLabel.textContent = authorized
      ? `Connecté avec GitHub : ${user.login}`
      : "Connexion GitHub requise";
    updateSubmitState();
  }

  function updateSubmitState() {
    const authorized = Boolean(state.user && allowedUsers.has(state.user.login));
    elements.submit.disabled = !(authorized && state.file && elements.publicConfirmation.checked);
  }

  function validateFile(file) {
    if (!file || !file.name.toLowerCase().endsWith(".xml")) {
      throw new Error("Le fichier sélectionné doit porter l’extension .xml.");
    }
    if (file.size === 0) throw new Error("Le fichier XML est vide.");
    if (file.size > 25 * 1024 * 1024) throw new Error("Le fichier dépasse la limite de 25 Mo.");
  }

  function selectFile(file) {
    try {
      validateFile(file);
      state.file = file;
      elements.selectedFileName.textContent = file.name;
      elements.selectedFileSize.textContent = formatBytes(file.size);
      elements.selectedFile.hidden = false;
      elements.publicNotice.hidden = false;
      setStatus(
        state.user ? "Le fichier est prêt à être envoyé." : "Connectez-vous avec GitHub pour envoyer ce fichier.",
      );
    } catch (error) {
      state.file = null;
      elements.fileInput.value = "";
      setStatus(error.message, "error");
    }
    updateSubmitState();
  }

  function clearFile() {
    state.file = null;
    elements.fileInput.value = "";
    elements.selectedFile.hidden = true;
    elements.publicNotice.hidden = true;
    elements.publicConfirmation.checked = false;
    setStatus("Sélectionnez un fichier XML pour commencer.");
    updateSubmitState();
  }

  function readAsBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(",", 2)[1]);
      reader.onerror = () => reject(new Error("Le fichier n’a pas pu être lu."));
      reader.readAsDataURL(file);
    });
  }

  function setStep(name, status) {
    elements.steps[name].dataset.status = status;
  }

  function showProgress(message) {
    elements.dropPanel.hidden = true;
    elements.resultsPanel.hidden = true;
    elements.progressPanel.hidden = false;
    elements.progressMessage.textContent = message;
  }

  function showResults(job) {
    clearTimeout(state.pollTimer);
    elements.progressPanel.hidden = true;
    elements.resultsPanel.hidden = false;
    elements.resultsSummary.textContent = `${job.sourceName} a été enrichi avec succès.`;
    elements.downloadXml.href = job.files.xml;
    elements.downloadTxt.href = job.files.txt;
    elements.downloadCsv.href = job.files.csv;
  }

  function filenameFromUrl(url) {
    try {
      return decodeURIComponent(new URL(url).pathname.split("/").pop());
    } catch {
      return "resultat-pactols";
    }
  }

  async function downloadResult(event) {
    event.preventDefault();
    const link = event.currentTarget;
    const url = link.href;
    const label = link.querySelector(":scope > span:last-child");
    const originalLabel = label.textContent;
    link.setAttribute("aria-busy", "true");
    label.textContent = "Téléchargement…";

    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Erreur de téléchargement (${response.status}).`);
      const blobUrl = URL.createObjectURL(await response.blob());
      const temporaryLink = document.createElement("a");
      temporaryLink.href = blobUrl;
      temporaryLink.download = filenameFromUrl(url);
      document.body.appendChild(temporaryLink);
      temporaryLink.click();
      temporaryLink.remove();
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
    } catch {
      setStatus("Le téléchargement a échoué. Veuillez réessayer.", "error");
    } finally {
      link.removeAttribute("aria-busy");
      label.textContent = originalLabel;
    }
  }

  function showJobFailure(job) {
    clearTimeout(state.pollTimer);
    elements.progressPanel.hidden = true;
    elements.dropPanel.hidden = false;
    setStatus(job.message || "Le traitement a échoué. Consultez les Actions GitHub.", "error");
  }

  async function pollJob(jobId) {
    try {
      const job = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
      if (job.status === "queued") {
        setStep("upload", "complete");
        setStep("workflow", "active");
        elements.progressMessage.textContent = "Le traitement attend son exécution sur GitHub.";
      } else if (job.status === "processing") {
        setStep("upload", "complete");
        setStep("workflow", "active");
        elements.progressMessage.textContent = "Le fichier est en cours d’enrichissement.";
      } else if (job.status === "completed") {
        setStep("upload", "complete");
        setStep("workflow", "complete");
        setStep("results", "complete");
        showResults(job);
        return;
      } else if (job.status === "failed") {
        showJobFailure(job);
        return;
      }
      state.pollTimer = window.setTimeout(() => pollJob(jobId), pollIntervalMs);
    } catch (error) {
      elements.progressMessage.textContent = `${error.message} Nouvelle tentative dans quelques secondes.`;
      state.pollTimer = window.setTimeout(() => pollJob(jobId), pollIntervalMs);
    }
  }

  async function submitFile() {
    if (elements.submit.disabled) return;
    elements.submit.disabled = true;
    setStep("upload", "active");
    setStep("workflow", "pending");
    setStep("results", "pending");
    showProgress("Envoi du fichier vers GitHub…");
    try {
      const content = await readAsBase64(state.file);
      const job = await api("/api/jobs", {
        method: "POST",
        body: JSON.stringify({ filename: state.file.name, content }),
      });
      setStep("upload", "complete");
      setStep("workflow", "active");
      elements.progressMessage.textContent = "Le fichier est déposé. GitHub Actions démarre le traitement.";
      await pollJob(job.id);
    } catch (error) {
      elements.progressPanel.hidden = true;
      elements.dropPanel.hidden = false;
      setStatus(error.message, "error");
      updateSubmitState();
    }
  }

  async function loadSession() {
    if (!apiBaseUrl) {
      updateSession(null);
      setStatus("L’interface de dépôt est prête ; la connexion GitHub reste à configurer.", "warning");
      return;
    }
    try {
      const session = await api("/auth/session");
      if (session?.user && !allowedUsers.has(session.user.login)) {
        throw new Error("Ce compte GitHub n’est pas autorisé à utiliser cette interface.");
      }
      updateSession(session?.user || null);
    } catch (error) {
      state.session = "";
      window.sessionStorage.removeItem("pactolsSession");
      updateSession(null);
      setStatus(error.message, "error");
    }
  }

  elements.login.addEventListener("click", () => {
    if (!apiBaseUrl) {
      setStatus("Le point d’authentification GitHub doit d’abord être configuré.", "warning");
      return;
    }
    window.location.assign(apiUrl(`/auth/github?returnTo=${encodeURIComponent(window.location.href)}`));
  });
  elements.logout.addEventListener("click", async () => {
    try {
      await api("/auth/logout", { method: "POST" });
      state.session = "";
      window.sessionStorage.removeItem("pactolsSession");
      updateSession(null);
      clearFile();
    } catch (error) {
      setStatus(error.message, "error");
    }
  });
  elements.selectButton.addEventListener("click", (event) => {
    event.stopPropagation();
    elements.fileInput.click();
  });
  elements.fileInput.addEventListener("change", () => selectFile(elements.fileInput.files[0]));
  elements.removeFile.addEventListener("click", (event) => {
    event.stopPropagation();
    clearFile();
  });
  elements.publicConfirmation.addEventListener("change", updateSubmitState);
  elements.submit.addEventListener("click", (event) => {
    event.stopPropagation();
    submitFile();
  });
  elements.dropPanel.addEventListener("click", (event) => {
    if (event.target === elements.dropPanel) elements.fileInput.click();
  });
  elements.dropPanel.addEventListener("keydown", (event) => {
    if ((event.key === "Enter" || event.key === " ") && event.target === elements.dropPanel) {
      event.preventDefault();
      elements.fileInput.click();
    }
  });
  ["dragenter", "dragover"].forEach((name) => {
    elements.dropPanel.addEventListener(name, (event) => {
      event.preventDefault();
      elements.dropPanel.classList.add("is-dragging");
    });
  });
  ["dragleave", "drop"].forEach((name) => {
    elements.dropPanel.addEventListener(name, (event) => {
      event.preventDefault();
      elements.dropPanel.classList.remove("is-dragging");
    });
  });
  elements.dropPanel.addEventListener("drop", (event) => selectFile(event.dataTransfer.files[0]));
  elements.newTreatment.addEventListener("click", () => {
    elements.resultsPanel.hidden = true;
    elements.dropPanel.hidden = false;
    clearFile();
  });
  [elements.downloadXml, elements.downloadTxt, elements.downloadCsv].forEach((link) => {
    link.addEventListener("click", downloadResult);
  });

  loadSession();
})();
