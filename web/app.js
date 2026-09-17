(() => {
  "use strict";

  const config = window.ADLFI_APP_CONFIG || window.PACTOLS_APP_CONFIG || {};
  const apiBaseUrl = String(config.apiBaseUrl || "").replace(/\/$/, "");
  const allowedUsers = new Set(config.allowedUsers || []);
  const pollIntervalMs = Number(config.pollIntervalMs) || 5000;
  const sessionKey = "adlfiXmlSession";

  const account = {
    login: document.querySelector("#login-button"),
    logout: document.querySelector("#logout-button"),
    bar: document.querySelector("#session-bar"),
    label: document.querySelector("#session-label"),
    message: document.querySelector("#session-message"),
  };

  function moduleElements(name) {
    const id = (suffix) => document.querySelector(`#${name}-${suffix}`);
    return {
      name,
      file: null,
      pollTimer: null,
      result: null,
      dropPanel: id("drop-panel"),
      fileInput: id("file-input"),
      selectButton: id("select-button"),
      selectedFile: id("selected-file"),
      selectedFileName: id("selected-file-name"),
      selectedFileSize: id("selected-file-size"),
      removeFile: id("remove-file-button"),
      publicNotice: id("public-notice"),
      publicConfirmation: id("public-confirmation"),
      submit: id("submit-button"),
      uploadStatus: id("upload-status"),
      progressPanel: id("progress-panel"),
      progressMessage: id("progress-message"),
      resultsPanel: id("results-panel"),
      resultsSummary: id("results-summary"),
      downloadXml: id("download-xml"),
      downloadTxt: id("download-txt"),
      downloadCsv: id("download-csv"),
      downloadStatus: id("download-status"),
      newTreatment: id("new-treatment-button"),
      steps: { upload: id("step-upload"), workflow: id("step-workflow"), results: id("step-results") },
    };
  }

  const modules = {
    preparation: moduleElements("preparation"),
    pactols: moduleElements("pactols"),
  };
  const state = {
    user: null,
    session: window.sessionStorage.getItem(sessionKey) || window.sessionStorage.getItem("pactolsSession") || "",
  };

  const callbackSession = new URLSearchParams(window.location.hash.slice(1)).get("session");
  if (callbackSession) {
    state.session = callbackSession;
    window.sessionStorage.setItem(sessionKey, callbackSession);
    window.sessionStorage.removeItem("pactolsSession");
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
  }

  function apiUrl(path) { return `${apiBaseUrl}${path}`; }

  async function api(path, options = {}) {
    if (!apiBaseUrl) throw new Error("Le service d’authentification n’est pas encore configuré.");
    const response = await fetch(apiUrl(path), {
      headers: {
        ...(state.session ? { Authorization: `Bearer ${state.session}` } : {}),
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
      ...options,
    });
    const body = response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) throw new Error(body?.message || body?.detail || `Erreur du service (${response.status}).`);
    return body;
  }

  function authorized() { return Boolean(state.user && allowedUsers.has(state.user.login)); }
  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} octets`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
  }
  function setStatus(module, message, type = "neutral") {
    module.uploadStatus.textContent = message;
    module.uploadStatus.dataset.type = type;
  }
  function updateSubmitState(module) {
    module.submit.disabled = !(authorized() && module.file && module.publicConfirmation.checked);
  }
  function updateSession(user) {
    state.user = user;
    const connected = authorized();
    account.bar.dataset.state = connected ? "connected" : "disconnected";
    account.login.hidden = connected;
    account.logout.hidden = !connected;
    account.label.textContent = connected ? `Connecté avec GitHub : ${user.login}` : "Connexion GitHub requise";
    Object.values(modules).forEach(updateSubmitState);
  }

  function validateFile(file) {
    if (!file || !file.name.toLowerCase().endsWith(".xml")) throw new Error("Le fichier sélectionné doit porter l’extension .xml.");
    if (file.size === 0) throw new Error("Le fichier XML est vide.");
    if (file.size > 25 * 1024 * 1024) throw new Error("Le fichier dépasse la limite de 25 Mo.");
  }
  function selectFile(module, file) {
    try {
      validateFile(file);
      module.file = file;
      module.selectedFileName.textContent = file.name;
      module.selectedFileSize.textContent = formatBytes(file.size);
      module.selectedFile.hidden = false;
      module.publicNotice.hidden = false;
      setStatus(module, authorized() ? "Le fichier est prêt à être envoyé." : "Connectez-vous avec GitHub pour envoyer ce fichier.");
    } catch (error) {
      module.file = null;
      module.fileInput.value = "";
      setStatus(module, error.message, "error");
    }
    updateSubmitState(module);
  }
  function clearFile(module) {
    module.file = null;
    module.fileInput.value = "";
    module.selectedFile.hidden = true;
    module.publicNotice.hidden = true;
    module.publicConfirmation.checked = false;
    setStatus(module, "Sélectionnez un fichier XML pour commencer.");
    updateSubmitState(module);
  }
  function resetModule(module) {
    clearTimeout(module.pollTimer);
    module.result = null;
    module.resultsPanel.hidden = true;
    module.progressPanel.hidden = true;
    module.dropPanel.hidden = false;
    if (module.downloadStatus) { module.downloadStatus.hidden = true; module.downloadStatus.textContent = ""; }
    clearFile(module);
  }
  function readAsBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(",", 2)[1]);
      reader.onerror = () => reject(new Error("Le fichier n’a pas pu être lu."));
      reader.readAsDataURL(file);
    });
  }
  function setStep(module, name, status) { module.steps[name].dataset.status = status; }
  function showProgress(module, message) {
    module.dropPanel.hidden = true;
    module.resultsPanel.hidden = true;
    module.progressPanel.hidden = false;
    module.progressMessage.textContent = message;
  }
  function showResults(module, job) {
    clearTimeout(module.pollTimer);
    module.result = job;
    module.progressPanel.hidden = true;
    module.resultsPanel.hidden = false;
    module.resultsSummary.textContent = module.name === "preparation"
      ? `${job.sourceName} a été préparé avec succès.`
      : `${job.sourceName} a été indexé avec succès.`;
    module.downloadXml.href = job.files.xml;
    module.downloadTxt.href = job.files.txt;
    if (module.downloadCsv) module.downloadCsv.href = job.files.csv;
  }
  function showJobFailure(module, job) {
    clearTimeout(module.pollTimer);
    module.progressPanel.hidden = true;
    module.dropPanel.hidden = false;
    setStatus(module, job.message || "Le traitement a échoué. Consultez les Actions GitHub.", "error");
  }
  async function pollJob(module, jobId) {
    try {
      const job = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
      if (job.status === "queued") {
        setStep(module, "upload", "complete"); setStep(module, "workflow", "active");
        module.progressMessage.textContent = "Le traitement attend son exécution sur GitHub.";
      } else if (job.status === "processing") {
        setStep(module, "upload", "complete"); setStep(module, "workflow", "active");
        module.progressMessage.textContent = "Le fichier est en cours de traitement.";
      } else if (job.status === "completed") {
        setStep(module, "upload", "complete"); setStep(module, "workflow", "complete"); setStep(module, "results", "complete");
        showResults(module, job); return;
      } else if (job.status === "failed") { showJobFailure(module, job); return; }
      module.pollTimer = window.setTimeout(() => pollJob(module, jobId), pollIntervalMs);
    } catch (error) {
      module.progressMessage.textContent = `${error.message} Nouvelle tentative dans quelques secondes.`;
      module.pollTimer = window.setTimeout(() => pollJob(module, jobId), pollIntervalMs);
    }
  }
  async function submitFile(module) {
    if (module.submit.disabled) return;
    module.submit.disabled = true;
    setStep(module, "upload", "active"); setStep(module, "workflow", "pending"); setStep(module, "results", "pending");
    showProgress(module, "Envoi du fichier vers GitHub…");
    try {
      const content = await readAsBase64(module.file);
      const job = await api("/api/jobs", { method: "POST", body: JSON.stringify({ module: module.name, filename: module.file.name, content }) });
      setStep(module, "upload", "complete"); setStep(module, "workflow", "active");
      module.progressMessage.textContent = "Le fichier est déposé. GitHub Actions démarre le traitement.";
      await pollJob(module, job.id);
    } catch (error) {
      module.progressPanel.hidden = true; module.dropPanel.hidden = false;
      setStatus(module, error.message, "error"); updateSubmitState(module);
    }
  }
  function filenameFromUrl(url) {
    try { return decodeURIComponent(new URL(url).pathname.split("/").pop()); }
    catch { return "resultat.xml"; }
  }
  async function downloadResult(event, module) {
    event.preventDefault();
    const link = event.currentTarget;
    const label = link.querySelector(":scope > span:last-child");
    const originalLabel = label.textContent;
    link.setAttribute("aria-busy", "true"); label.textContent = "Téléchargement…";
    module.downloadStatus.hidden = true;
    try {
      const response = await fetch(link.href);
      if (!response.ok) throw new Error();
      const blobUrl = URL.createObjectURL(await response.blob());
      const temporary = document.createElement("a");
      temporary.href = blobUrl; temporary.download = filenameFromUrl(link.href);
      document.body.appendChild(temporary); temporary.click(); temporary.remove();
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
    } catch {
      module.downloadStatus.textContent = "Le téléchargement a échoué. Veuillez réessayer.";
      module.downloadStatus.hidden = false;
    } finally { link.removeAttribute("aria-busy"); label.textContent = originalLabel; }
  }

  async function continueWithPactols() {
    const source = modules.preparation.result?.files?.xml;
    if (!source) return;
    const button = document.querySelector("#preparation-continue-button");
    button.disabled = true; button.textContent = "Transfert en cours…";
    try {
      const response = await fetch(source);
      if (!response.ok) throw new Error();
      const file = new File([await response.blob()], filenameFromUrl(source), { type: "application/xml" });
      resetModule(modules.pactols);
      selectFile(modules.pactols, file);
      document.querySelector("#pactols-module").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch {
      modules.preparation.downloadStatus.textContent = "Le transfert vers Pactols a échoué. Téléchargez le XML préparé puis déposez-le dans le second module.";
      modules.preparation.downloadStatus.hidden = false;
    } finally { button.disabled = false; button.textContent = "Continuer avec l’indexation Pactols"; }
  }

  function bindModule(module) {
    module.selectButton.addEventListener("click", (event) => { event.stopPropagation(); module.fileInput.click(); });
    module.fileInput.addEventListener("change", () => selectFile(module, module.fileInput.files[0]));
    module.removeFile.addEventListener("click", (event) => { event.stopPropagation(); clearFile(module); });
    module.publicConfirmation.addEventListener("change", () => updateSubmitState(module));
    module.submit.addEventListener("click", (event) => { event.stopPropagation(); submitFile(module); });
    module.dropPanel.addEventListener("click", (event) => { if (event.target === module.dropPanel) module.fileInput.click(); });
    module.dropPanel.addEventListener("keydown", (event) => {
      if ((event.key === "Enter" || event.key === " ") && event.target === module.dropPanel) { event.preventDefault(); module.fileInput.click(); }
    });
    ["dragenter", "dragover"].forEach((name) => module.dropPanel.addEventListener(name, (event) => { event.preventDefault(); module.dropPanel.classList.add("is-dragging"); }));
    ["dragleave", "drop"].forEach((name) => module.dropPanel.addEventListener(name, (event) => { event.preventDefault(); module.dropPanel.classList.remove("is-dragging"); }));
    module.dropPanel.addEventListener("drop", (event) => selectFile(module, event.dataTransfer.files[0]));
    module.newTreatment.addEventListener("click", () => resetModule(module));
    [module.downloadXml, module.downloadTxt, module.downloadCsv].filter(Boolean).forEach((link) => link.addEventListener("click", (event) => downloadResult(event, module)));
  }

  async function loadSession() {
    if (!apiBaseUrl) { updateSession(null); account.message.textContent = "Le service de connexion GitHub reste à configurer."; return; }
    try {
      const session = await api("/auth/session");
      if (session?.user && !allowedUsers.has(session.user.login)) throw new Error("Ce compte GitHub n’est pas autorisé à utiliser cette interface.");
      updateSession(session?.user || null); account.message.textContent = "";
    } catch (error) {
      state.session = ""; window.sessionStorage.removeItem(sessionKey); window.sessionStorage.removeItem("pactolsSession");
      updateSession(null); account.message.textContent = error.message;
    }
  }

  account.login.addEventListener("click", () => {
    if (!apiBaseUrl) { account.message.textContent = "Le point d’authentification GitHub doit d’abord être configuré."; return; }
    window.location.assign(apiUrl(`/auth/github?returnTo=${encodeURIComponent(window.location.href)}`));
  });
  account.logout.addEventListener("click", async () => {
    try {
      await api("/auth/logout", { method: "POST" });
      state.session = ""; window.sessionStorage.removeItem(sessionKey); window.sessionStorage.removeItem("pactolsSession");
      updateSession(null); Object.values(modules).forEach(resetModule);
    } catch (error) { account.message.textContent = error.message; }
  });
  Object.values(modules).forEach(bindModule);
  document.querySelector("#preparation-continue-button").addEventListener("click", continueWithPactols);
  loadSession();
})();
