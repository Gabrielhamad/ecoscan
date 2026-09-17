from __future__ import annotations

import argparse
import json
import logging
import socket
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ecoscan.config import load_config
from ecoscan.errors import build_error_payload, public_error_payload
from ecoscan.live_camera.analyzer import LiveCameraAnalyzer, LiveCameraSettings
from ecoscan.utils.logging_config import configure_logging


LOGGER = logging.getLogger(__name__)


LIVE_CAMERA_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EcoScan Live</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f7f2;
      --panel: #ffffff;
      --ink: #16231c;
      --muted: #5a6d62;
      --line: #d9e1db;
      --accent: #24745d;
      --accent-blue: #2f80ed;
      --accent-dark: #165845;
      --warn: #8a5d09;
      --danger: #8c3024;
      --shadow: 0 18px 50px rgba(25, 41, 32, 0.14);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: linear-gradient(180deg, #edf4ef 0%, var(--bg) 48%, #eef3f7 100%);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .app {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 18px;
      width: min(1280px, calc(100vw - 28px));
      margin: 14px auto;
    }

    .topbar {
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 12px 14px;
      box-shadow: 0 8px 22px rgba(25, 41, 32, 0.08);
    }

    .brand {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }

    .brand strong {
      font-size: 1.1rem;
      line-height: 1.2;
    }

    .brand span,
    .status-line {
      color: var(--muted);
      font-size: 0.88rem;
    }

    .controls {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    button {
      appearance: none;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      color: var(--ink);
      cursor: pointer;
      font-weight: 700;
      min-height: 38px;
      padding: 0 12px;
      touch-action: manipulation;
    }

    button.primary {
      background: var(--accent);
      border-color: var(--accent);
      color: white;
    }

    button:hover { border-color: var(--accent); }
    button.primary:hover { background: var(--accent-dark); }

    .stage {
      position: relative;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #101a15;
      box-shadow: var(--shadow);
      min-height: 420px;
      isolation: isolate;
    }

    video {
      display: block;
      width: 100%;
      height: auto;
      min-height: 420px;
      object-fit: contain;
      background: #101a15;
    }

    .scan-frame {
      position: absolute;
      inset: 12%;
      border: 1px solid rgba(255,255,255,0.45);
      border-radius: 8px;
      pointer-events: none;
      box-shadow: 0 0 0 999px rgba(5, 16, 12, 0.08);
      opacity: 0.62;
    }

    #overlay {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
    }

    .video-status {
      position: absolute;
      left: 12px;
      right: 12px;
      bottom: 12px;
      display: flex;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: wrap;
      pointer-events: none;
    }

    .pill {
      border: 1px solid rgba(255,255,255,0.28);
      border-radius: 999px;
      background: rgba(12, 25, 20, 0.74);
      color: white;
      font-size: 0.84rem;
      font-weight: 700;
      padding: 7px 10px;
      backdrop-filter: blur(8px);
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 14px;
      box-shadow: 0 8px 22px rgba(25, 41, 32, 0.08);
    }

    .panel h2 {
      font-size: 1rem;
      margin: 0 0 10px;
    }

    .panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .state-badge {
      border: 1px solid #b9d8ca;
      border-radius: 999px;
      color: #165845;
      background: #e6f4ee;
      font-size: 0.76rem;
      font-weight: 800;
      padding: 5px 8px;
      white-space: nowrap;
    }

    .state-badge.warn {
      border-color: #edd18f;
      color: #76520c;
      background: #fff7df;
    }

    .metric-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin: 10px 0;
    }

    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      min-height: 76px;
    }

    .metric span {
      display: block;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 700;
      margin-bottom: 6px;
    }

    .metric strong {
      display: block;
      font-size: 1rem;
      line-height: 1.2;
      overflow-wrap: anywhere;
    }

    .score-ring {
      --score: 0%;
      width: 82px;
      height: 82px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: conic-gradient(var(--accent) var(--score), #e6ece8 0);
      margin: 4px 0 10px;
    }

    .score-ring span {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: #ffffff;
      color: #17211b;
      font-weight: 850;
    }

    .result {
      border-left: 4px solid var(--accent);
      background: #eef7f1;
      border-radius: 8px;
      padding: 10px 12px;
      margin: 10px 0;
    }

    .result.warn {
      border-left-color: var(--warn);
      background: #fff8e8;
    }

    .result strong {
      display: block;
      margin-bottom: 4px;
    }

    .result p {
      margin: 0;
      color: #33463b;
      font-size: 0.9rem;
      line-height: 1.45;
    }

    .target-panel {
      display: none;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f8fbf8;
      padding: 10px 12px;
      margin: 10px 0;
    }

    .target-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 850;
      color: var(--ink);
    }

    .target-dot {
      width: 14px;
      height: 14px;
      border-radius: 999px;
      border: 1px solid rgba(15, 27, 21, 0.25);
      flex: 0 0 auto;
    }

    .target-panel ul {
      margin: 8px 0;
      padding-left: 18px;
      color: #33463b;
      font-size: 0.86rem;
      line-height: 1.4;
    }

    .target-impact {
      border-top: 1px solid var(--line);
      margin-top: 10px;
      padding-top: 10px;
    }

    .target-impact strong {
      display: block;
      color: var(--ink);
      font-size: 0.88rem;
      line-height: 1.3;
      margin-bottom: 4px;
    }

    .target-impact span {
      display: inline-flex;
      border: 1px solid rgba(35, 54, 45, 0.16);
      border-radius: 999px;
      background: #ffffff;
      color: #33463b;
      font-size: 0.74rem;
      font-weight: 850;
      margin-bottom: 4px;
      padding: 3px 7px;
    }

    .target-impact p {
      color: #33463b;
      font-size: 0.84rem;
      line-height: 1.4;
      margin: 4px 0 0;
    }

    .map-link {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--accent);
      border-radius: 8px;
      background: var(--accent);
      color: white;
      text-decoration: none;
      font-weight: 850;
      margin-top: 6px;
    }

    .detections {
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }

    .probabilities {
      display: grid;
      gap: 8px;
      margin: 10px 0;
    }

    .probability {
      display: grid;
      grid-template-columns: minmax(90px, 1fr) minmax(90px, 1.2fr) 44px;
      gap: 8px;
      align-items: center;
      font-size: 0.84rem;
      font-weight: 750;
    }

    .probability-label {
      overflow-wrap: anywhere;
    }

    .probability-track {
      height: 8px;
      overflow: hidden;
      border-radius: 999px;
      background: #edf2ef;
    }

    .probability-fill {
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--accent), var(--accent-blue));
    }

    .probability-value {
      text-align: right;
      color: var(--muted);
      font-size: 0.78rem;
    }

    .detection {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 10px;
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: center;
    }

    .detection small {
      color: var(--muted);
      display: block;
      margin-top: 2px;
    }

    .message {
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.4;
    }

    .message.danger { color: var(--danger); }

    @media (max-width: 920px) {
      .app {
        grid-template-columns: 1fr;
        width: min(100vw - 18px, 720px);
        margin: 9px auto;
      }

      .topbar {
        align-items: stretch;
        flex-direction: column;
      }

      .controls {
        justify-content: stretch;
      }

      button {
        flex: 1;
      }

      .stage,
      video {
        min-height: 360px;
      }

      body {
        background: #101a15;
      }

      .app {
        gap: 0;
        width: 100vw;
        margin: 0;
      }

      .topbar {
        position: sticky;
        top: 0;
        z-index: 3;
        border-radius: 0;
        border-left: 0;
        border-right: 0;
      }

      .stage {
        border: 0;
        border-radius: 0;
        box-shadow: none;
        min-height: 56vh;
      }

      video {
        height: 56vh;
        object-fit: cover;
      }

      .panel {
        position: relative;
        z-index: 2;
        border-radius: 8px 8px 0 0;
        border-left: 0;
        border-right: 0;
        margin-top: -10px;
        box-shadow: 0 -12px 32px rgba(5, 16, 12, 0.22);
      }

      .metric-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
      }

      .metric {
        min-height: 66px;
        padding: 8px;
      }

      .metric span {
        font-size: 0.68rem;
      }

      .metric strong {
        font-size: 0.82rem;
      }
    }

    @media (max-width: 520px) {
      .metric-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .probability {
        grid-template-columns: minmax(88px, 1fr) minmax(84px, 1fr) 40px;
      }
    }
  </style>
</head>
<body>
  <main class="app">
    <header class="topbar">
      <div class="brand">
        <strong>EcoScan Live</strong>
        <span>Reconhecimento local com câmera traseira preferencial</span>
      </div>
      <div class="controls">
        <button id="startButton" class="primary">Iniciar traseira</button>
        <button id="switchButton">Alternar câmera</button>
        <button id="pauseButton">Pausar</button>
      </div>
    </header>

    <section class="stage">
      <video id="video" autoplay muted playsinline></video>
      <canvas id="overlay"></canvas>
      <div class="scan-frame"></div>
      <div class="video-status">
        <span id="cameraStatus" class="pill">câmera parada</span>
        <span id="trackingStatus" class="pill">0 objetos</span>
      </div>
    </section>

    <aside class="panel">
      <div class="panel-header">
        <h2>Leitura atual</h2>
        <span id="stateBadge" class="state-badge warn">aguardando</span>
      </div>
      <div id="secureWarning" class="message danger"></div>
      <div id="mainResult" class="result warn">
        <strong>Aguardando câmera</strong>
        <p>Inicie a câmera e aponte para um resíduo.</p>
      </div>
      <div id="targetPanel" class="target-panel"></div>
      <div id="scoreRing" class="score-ring" style="--score: 0%"><span>-</span></div>
      <div class="metric-grid">
        <div class="metric">
          <span>Confiança</span>
          <strong id="score">-</strong>
        </div>
        <div class="metric">
          <span>Latência</span>
          <strong id="latency">-</strong>
        </div>
        <div class="metric">
          <span>Filtro</span>
          <strong id="filter">-</strong>
        </div>
        <div class="metric">
          <span>Segmentação</span>
          <strong id="segmentation">-</strong>
        </div>
      </div>
      <div id="probabilities" class="probabilities"></div>
      <div id="quality" class="message"></div>
      <div id="detections" class="detections"></div>
    </aside>
  </main>

  <script>
    const video = document.getElementById("video");
    const overlay = document.getElementById("overlay");
    const overlayContext = overlay.getContext("2d");
    const captureCanvas = document.createElement("canvas");
    const captureContext = captureCanvas.getContext("2d");
    const startButton = document.getElementById("startButton");
    const switchButton = document.getElementById("switchButton");
    const pauseButton = document.getElementById("pauseButton");
    const cameraStatus = document.getElementById("cameraStatus");
    const trackingStatus = document.getElementById("trackingStatus");
    const mainResult = document.getElementById("mainResult");
    const targetPanel = document.getElementById("targetPanel");
    const stateBadge = document.getElementById("stateBadge");
    const scoreRing = document.getElementById("scoreRing");
    const score = document.getElementById("score");
    const latency = document.getElementById("latency");
    const filter = document.getElementById("filter");
    const segmentation = document.getElementById("segmentation");
    const probabilities = document.getElementById("probabilities");
    const quality = document.getElementById("quality");
    const detections = document.getElementById("detections");
    const secureWarning = document.getElementById("secureWarning");

    let stream = null;
    let running = false;
    let paused = false;
    let inFlight = false;
    let facingMode = "environment";
    let activeFacingMode = null;
    let cameraAttemptLabel = "";
    let timer = null;
    let lastResult = null;

    const backCameraPattern = /(back|rear|environment|traseira|externa|wide|telephoto)/i;
    const frontCameraPattern = /(front|user|frontal|selfie|facetime)/i;

    if (!window.isSecureContext && !["localhost", "127.0.0.1"].includes(location.hostname)) {
      secureWarning.textContent = "No celular, a câmera pode exigir HTTPS. Se o navegador bloquear, abra por HTTPS ou túnel seguro.";
    }

    function stopStream() {
      if (stream) {
        for (const track of stream.getTracks()) {
          track.stop();
        }
      }
      stream = null;
    }

    async function startCamera() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Este navegador bloqueou acesso à câmera. Use localhost, HTTPS ou um túnel seguro.");
      }
      stopStream();
      paused = false;
      cameraStatus.textContent = facingMode === "environment" ? "abrindo câmera traseira..." : "abrindo câmera frontal...";
      const openedCamera = await openPreferredCamera(facingMode);
      stream = openedCamera.stream;
      cameraAttemptLabel = openedCamera.label;
      activeFacingMode = inferFacingMode(stream);
      video.srcObject = stream;
      await video.play();
      running = true;
      cameraStatus.textContent = cameraStatusText();
      startLoop();
      requestAnimationFrame(drawOverlay);
    }

    async function openPreferredCamera(mode) {
      let lastError = null;
      for (const attempt of await cameraFallbackOrder(mode)) {
        try {
          const openedStream = await navigator.mediaDevices.getUserMedia(attempt.constraints);
          return { stream: openedStream, label: attempt.label };
        } catch (error) {
          lastError = error;
        }
      }
      throw lastError || new Error("Não foi possível abrir uma câmera disponível neste dispositivo.");
    }

    async function cameraFallbackOrder(mode) {
      const modeLabel = mode === "environment" ? "traseira" : "frontal";
      const attempts = [
        { label: `${modeLabel} obrigatória`, constraints: cameraConstraints(mode, "exact") },
        { label: `${modeLabel} preferencial`, constraints: cameraConstraints(mode, "ideal") }
      ];
      const deviceConstraint = await matchingDeviceConstraint(mode);
      if (deviceConstraint) {
        attempts.push({ label: `${modeLabel} por dispositivo`, constraints: deviceConstraint });
      }
      attempts.push({ label: "câmera disponível", constraints: cameraConstraints(mode, "generic") });
      return attempts;
    }

    function cameraConstraints(mode, strategy) {
      const videoConstraints = {
        width: { ideal: 1280 },
        height: { ideal: 720 }
      };
      if (strategy === "exact") {
        videoConstraints.facingMode = { exact: mode };
      } else if (strategy === "ideal") {
        videoConstraints.facingMode = { ideal: mode };
      }
      return { audio: false, video: videoConstraints };
    }

    async function matchingDeviceConstraint(mode) {
      if (!navigator.mediaDevices.enumerateDevices) {
        return null;
      }
      try {
        const pattern = mode === "environment" ? backCameraPattern : frontCameraPattern;
        const devices = await navigator.mediaDevices.enumerateDevices();
        const camera = devices.find((device) => (
          device.kind === "videoinput" && device.deviceId && pattern.test(device.label || "")
        ));
        if (!camera) {
          return null;
        }
        return {
          audio: false,
          video: {
            deviceId: { exact: camera.deviceId },
            width: { ideal: 1280 },
            height: { ideal: 720 }
          }
        };
      } catch (error) {
        return null;
      }
    }

    function inferFacingMode(cameraStream) {
      const [track] = cameraStream.getVideoTracks();
      const settings = typeof track?.getSettings === "function" ? track.getSettings() : {};
      const label = track?.label || "";
      if (settings.facingMode === "environment" || backCameraPattern.test(label)) {
        return "environment";
      }
      if (settings.facingMode === "user" || frontCameraPattern.test(label)) {
        return "user";
      }
      return null;
    }

    function cameraStatusText() {
      if (activeFacingMode === "environment") {
        return "câmera traseira";
      }
      if (activeFacingMode === "user") {
        return "câmera frontal";
      }
      if (cameraAttemptLabel === "câmera disponível" && facingMode === "environment") {
        return "câmera ativa; traseira não confirmada";
      }
      return facingMode === "environment" ? "câmera traseira preferencial" : "câmera frontal preferencial";
    }

    function startLoop() {
      if (timer) {
        window.clearInterval(timer);
      }
      timer = window.setInterval(analyzeFrame, 850);
      analyzeFrame();
    }

    async function analyzeFrame() {
      if (!running || paused || inFlight || video.readyState < 2) {
        return;
      }

      const sourceWidth = video.videoWidth || 640;
      const sourceHeight = video.videoHeight || 480;
      const targetWidth = Math.min(640, sourceWidth);
      const targetHeight = Math.round(targetWidth * sourceHeight / sourceWidth);
      captureCanvas.width = targetWidth;
      captureCanvas.height = targetHeight;
      captureContext.drawImage(video, 0, 0, targetWidth, targetHeight);

      inFlight = true;
      try {
        const blob = await new Promise((resolve) => captureCanvas.toBlob(resolve, "image/jpeg", 0.78));
        const response = await fetch("/api/analyze-frame", {
          method: "POST",
          headers: { "Content-Type": "image/jpeg" },
          body: blob
        });
        lastResult = await response.json();
        renderResult(lastResult);
      } catch (error) {
        renderError(error);
      } finally {
        inFlight = false;
      }
    }

    function renderResult(result) {
      if (!result.ok) {
        renderError(result);
        return;
      }

      const probability = typeof result.probability === "number" ? `${Math.round(result.probability * 100)}%` : "-";
      const scorePercent = typeof result.probability === "number" ? Math.round(result.probability * 100) : 0;
      const label = result.guidance?.display_name || result.predicted_class || result.top_class || "incerto";
      mainResult.className = result.accepted ? "result" : "result warn";
      mainResult.innerHTML = `<strong>${escapeHtml(label)}</strong><p>${escapeHtml(result.message || "")}</p>`;
      stateBadge.className = result.accepted ? "state-badge" : "state-badge warn";
      stateBadge.textContent = result.accepted ? "identificado" : "incerto";
      scoreRing.style.setProperty("--score", `${scorePercent}%`);
      scoreRing.querySelector("span").textContent = probability;
      score.textContent = probability;
      latency.textContent = `${result.latency_ms} ms`;
      filter.textContent = result.filter?.decision?.selected || result.filter?.name || "-";
      segmentation.textContent = result.segmentation?.decision?.selected || result.segmentation?.name || "-";
      quality.className = `message ${result.capture_quality?.status === "retake" ? "danger" : ""}`;
      quality.textContent = captureQualityMessage(result);
      renderDisposalTarget(result.disposal_target, result.environmental_impact);
      renderProbabilities(result.probabilities || {});
      trackingStatus.textContent = `${result.detections.length} objeto${result.detections.length === 1 ? "" : "s"}`;
      detections.innerHTML = result.detections.map((item) => {
        const itemScore = typeof item.score === "number" ? `${Math.round(item.score * 100)}%` : "-";
        return `<div class="detection"><div><strong>#${item.track_id} ${escapeHtml(item.label)}</strong><small>${escapeHtml(item.top_class || "sem classe")}</small></div><strong>${itemScore}</strong></div>`;
      }).join("");
    }

    function renderProbabilities(values) {
      const rows = Object.entries(values)
        .sort((left, right) => Number(right[1]) - Number(left[1]))
        .slice(0, 5)
        .map(([label, value]) => {
          const percent = Math.max(0, Math.min(100, Math.round(Number(value) * 100)));
          return `<div class="probability"><div class="probability-label">${escapeHtml(label)}</div><div class="probability-track"><div class="probability-fill" style="width:${percent}%"></div></div><div class="probability-value">${percent}%</div></div>`;
        });
      probabilities.innerHTML = rows.join("");
    }

    function captureQualityMessage(result) {
      const captureQuality = result.capture_quality || {};
      const score = typeof captureQuality.score === "number" ? ` (${captureQuality.score}/100)` : "";
      const action = Array.isArray(captureQuality.actions) && captureQuality.actions.length
        ? ` ${captureQuality.actions[0]}`
        : "";
      if (captureQuality.title || captureQuality.message) {
        return `${captureQuality.title || "Qualidade da captura"}${score}: ${captureQuality.message || ""}${action}`.trim();
      }
      return result.elements_warning || "";
    }

    function renderDisposalTarget(target, impact) {
      if (!target) {
        targetPanel.style.display = "none";
        targetPanel.innerHTML = "";
        return;
      }
      const steps = (target.preparation_steps || [])
        .slice(0, 3)
        .map((step) => `<li>${escapeHtml(step)}</li>`)
        .join("");
      const impactHtml = impact ? `
        <div class="target-impact">
          <strong>${escapeHtml(impact.impact_title || "Consequência do descarte incorreto")}</strong>
          <span>${escapeHtml(impact.risk_label || impact.risk_level || "risco ambiental")}</span>
          <p>${escapeHtml((impact.bad_disposal_risks || [])[0] || impact.positive_action || "")}</p>
        </div>
      ` : "";
      targetPanel.style.display = "block";
      targetPanel.innerHTML = `
        <div class="target-title">
          <span class="target-dot" style="background:${escapeHtml(target.bin_color_hex || "#d9e1db")}"></span>
          <span>${escapeHtml(target.destination_title || "Ponto de descarte")}</span>
        </div>
        <ul>${steps}</ul>
        <a class="map-link" href="${escapeHtml(target.map_url || "#")}" target="_blank" rel="noopener noreferrer">
          Buscar ponto próximo
        </a>
        ${impactHtml}
      `;
    }

    function renderError(error) {
      const title = error.title || "Análise indisponível";
      const code = error.code ? `${error.code} - ` : "";
      const message = error.error || error.message || String(error);
      const action = error.action ? `<p><strong>Ação:</strong> ${escapeHtml(error.action)}</p>` : "";
      mainResult.className = "result warn";
      mainResult.innerHTML = `<strong>${escapeHtml(code + title)}</strong><p>${escapeHtml(message)}</p>${action}`;
      stateBadge.className = "state-badge warn";
      stateBadge.textContent = "atenção";
      scoreRing.style.setProperty("--score", "0%");
      scoreRing.querySelector("span").textContent = "-";
      probabilities.innerHTML = "";
      targetPanel.style.display = "none";
      targetPanel.innerHTML = "";
    }

    function drawOverlay() {
      const rect = video.getBoundingClientRect();
      const ratio = window.devicePixelRatio || 1;
      overlay.width = Math.max(1, Math.round(rect.width * ratio));
      overlay.height = Math.max(1, Math.round(rect.height * ratio));
      overlay.style.width = `${rect.width}px`;
      overlay.style.height = `${rect.height}px`;
      overlayContext.setTransform(ratio, 0, 0, ratio, 0, 0);
      overlayContext.clearRect(0, 0, rect.width, rect.height);

      if (lastResult?.ok && lastResult.analysis_size) {
        const scaleX = rect.width / lastResult.analysis_size.width;
        const scaleY = rect.height / lastResult.analysis_size.height;
        for (const item of lastResult.detections) {
          drawBox(item, scaleX, scaleY);
        }
      }

      if (running) {
        requestAnimationFrame(drawOverlay);
      }
    }

    function drawBox(item, scaleX, scaleY) {
      const color = item.accepted ? "#2bd492" : "#f0b84a";
      const x = item.bbox.x * scaleX;
      const y = item.bbox.y * scaleY;
      const width = item.bbox.width * scaleX;
      const height = item.bbox.height * scaleY;
      const label = `#${item.track_id} ${item.label}`;

      overlayContext.lineWidth = 3;
      overlayContext.strokeStyle = color;
      overlayContext.strokeRect(x, y, width, height);
      overlayContext.font = "700 14px system-ui, sans-serif";
      const textWidth = overlayContext.measureText(label).width + 14;
      const labelY = Math.max(0, y - 28);
      overlayContext.fillStyle = color;
      overlayContext.fillRect(x, labelY, Math.max(80, textWidth), 24);
      overlayContext.fillStyle = "#102019";
      overlayContext.fillText(label, x + 7, labelY + 16);
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    startButton.addEventListener("click", () => startCamera().catch(renderError));
    switchButton.addEventListener("click", () => {
      facingMode = facingMode === "environment" ? "user" : "environment";
      startCamera().catch(renderError);
    });
    pauseButton.addEventListener("click", () => {
      paused = !paused;
      pauseButton.textContent = paused ? "Retomar" : "Pausar";
      cameraStatus.textContent = paused ? "pausado" : cameraStatusText();
    });
  </script>
</body>
</html>
"""


class EcoScanLiveServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], analyzer: LiveCameraAnalyzer) -> None:
        super().__init__(server_address, LiveCameraRequestHandler)
        self.analyzer = analyzer


class LiveCameraRequestHandler(BaseHTTPRequestHandler):
    server: EcoScanLiveServer

    def do_OPTIONS(self) -> None:
        self._send_empty(204)

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send_bytes(LIVE_CAMERA_HTML.encode("utf-8"), content_type="text/html; charset=utf-8")
            return
        if self.path == "/health":
            self._send_json({"ok": True, "service": "ecoscan-live-camera"})
            return
        self._send_json(_live_error_payload("HTTP-404", "Rota não encontrada", "A rota solicitada não existe no EcoScan Live.", "Abra a página inicial do EcoScan Live ou use /api/analyze-frame.", "http"), status=404)

    def do_POST(self) -> None:
        if self.path != "/api/analyze-frame":
            self._send_json(_live_error_payload("HTTP-404", "Rota não encontrada", "A rota solicitada não existe no EcoScan Live.", "Envie frames apenas para /api/analyze-frame.", "http"), status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            self._send_json(
                _live_error_payload(
                    "CAM-003",
                    "Cabeçalho inválido",
                    "O tamanho do frame enviado pela câmera é inválido.",
                    "Atualize a página e tente iniciar a câmera novamente.",
                    "camera",
                ),
                status=400,
            )
            return

        if length <= 0:
            self._send_json(
                _live_error_payload(
                    "CAM-001",
                    "Frame vazio",
                    "A câmera não enviou imagem para análise.",
                    "Mantenha a câmera ativa e tente capturar o frame novamente.",
                    "camera",
                ),
                status=400,
            )
            return
        if length > 8_000_000:
            self._send_json(
                _live_error_payload(
                    "CAM-002",
                    "Frame muito grande",
                    "O frame enviado excede o limite aceito pelo EcoScan Live.",
                    "Reduza a resolução da câmera ou atualize a página para usar a captura compactada.",
                    "camera",
                ),
                status=413,
            )
            return

        frame_bytes = self.rfile.read(length)
        if len(frame_bytes) != length:
            self._send_json(
                _live_error_payload(
                    "CAM-004",
                    "Frame incompleto",
                    "A câmera enviou um frame incompleto para análise.",
                    "Verifique a conexão do navegador e tente novamente.",
                    "camera",
                ),
                status=400,
            )
            return

        try:
            payload = self.server.analyzer.analyze_frame(frame_bytes)
        except Exception as exc:
            LOGGER.exception("live_camera_analysis_failed detail=%s", exc)
            payload = public_error_payload(exc)
            self._send_json(payload, status=_http_status_for_error(payload.get("code")))
            return
        self._send_json(payload, status=_http_status_for_error(payload.get("code")) if not payload.get("ok") else 200)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_empty(self, status: int) -> None:
        self.send_response(status)
        self._send_default_headers()
        self.end_headers()

    def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(data, status=status, content_type="application/json; charset=utf-8")

    def _send_bytes(self, data: bytes, *, status: int = 200, content_type: str) -> None:
        self.send_response(status)
        self._send_default_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_default_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


def _live_error_payload(
    code: str,
    title: str,
    message: str,
    action: str,
    category: str,
) -> dict[str, str | bool]:
    return build_error_payload(
        code=code,
        title=title,
        message=message,
        action=action,
        category=category,
    )


def _http_status_for_error(code: object) -> int:
    if not isinstance(code, str):
        return 200
    if code == "HTTP-404":
        return 404
    if code in {"CAM-001", "CAM-003", "CAM-004"}:
        return 400
    if code == "CAM-002":
        return 413
    if code.startswith(("IMG-", "PROC-", "SEG-", "DATA-", "APP-002")):
        return 422
    if code.startswith("MODEL-"):
        return 503
    return 500


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run EcoScan live camera web server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--filter", default="auto")
    parser.add_argument("--segmentation", default="auto")
    parser.add_argument("--model", type=Path, default=None)
    parser.add_argument("--cert-file", type=Path, default=None)
    parser.add_argument("--key-file", type=Path, default=None)
    return parser


def run_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    filter_name: str = "auto",
    segmentation_name: str = "auto",
    model_path: str | Path | None = None,
    cert_file: str | Path | None = None,
    key_file: str | Path | None = None,
) -> None:
    config = load_config()
    configure_logging(config.directories["logs"])
    analyzer = LiveCameraAnalyzer(
        config,
        settings=LiveCameraSettings(filter_name=filter_name, segmentation_name=segmentation_name),
        model_path=model_path,
    )
    server = EcoScanLiveServer((host, port), analyzer)

    scheme = "http"
    if cert_file and key_file:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(cert_file), str(key_file))
        server.socket = context.wrap_socket(server.socket, server_side=True)
        scheme = "https"

    print(f"EcoScan Live: {scheme}://{host}:{port}/")
    for address in _lan_addresses():
        if host in {"0.0.0.0", "::"}:
            print(f"LAN: {scheme}://{address}:{port}/")
    print("Pressione Ctrl+C para parar.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor finalizado.")
    finally:
        server.server_close()


def _lan_addresses() -> list[str]:
    addresses: set[str] = set()
    try:
        hostname = socket.gethostname()
        for address in socket.gethostbyname_ex(hostname)[2]:
            if not address.startswith("127."):
                addresses.add(address)
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            address = sock.getsockname()[0]
            if not address.startswith("127."):
                addresses.add(address)
    except OSError:
        pass
    return sorted(addresses)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_server(
        host=args.host,
        port=args.port,
        filter_name=args.filter,
        segmentation_name=args.segmentation,
        model_path=args.model,
        cert_file=args.cert_file,
        key_file=args.key_file,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
