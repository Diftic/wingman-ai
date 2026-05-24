/* SC Log Donor -- Frontend */

(function () {
  "use strict";

  // -----------------------------------------------------------------------
  // State
  // -----------------------------------------------------------------------

  var state = {
    // "preview" | "uploading" | "done"
    view: "preview",
    preview: null,      // GET /api/preview response
    status: null,       // GET /api/status response
    pollTimer: null,
    error: null,
  };

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  function formatBytes(bytes) {
    if (bytes === 0) return "0 B";
    var units = ["B", "KB", "MB", "GB"];
    var i = Math.floor(Math.log(bytes) / Math.log(1024));
    i = Math.min(i, units.length - 1);
    var val = bytes / Math.pow(1024, i);
    return val.toFixed(i >= 2 ? 1 : 0) + " " + units[i];
  }

  function badgeClass(install) {
    var lower = (install || "").toLowerCase();
    if (lower === "live") return "install-badge live";
    if (lower === "ptu") return "install-badge ptu";
    return "install-badge other";
  }

  function esc(str) {
    var d = document.createElement("div");
    d.textContent = str == null ? "" : String(str);
    return d.innerHTML;
  }

  function relativeTime(isoStr) {
    if (!isoStr) return "unknown";
    var then = new Date(isoStr);
    var diffSec = Math.round((Date.now() - then.getTime()) / 1000);
    if (diffSec < 5) return "just now";
    if (diffSec < 60) return diffSec + "s ago";
    var diffMin = Math.round(diffSec / 60);
    if (diffMin < 60) return diffMin + "m ago";
    return then.toLocaleTimeString();
  }

  // -----------------------------------------------------------------------
  // API calls
  // -----------------------------------------------------------------------

  function loadPreview() {
    var app = document.getElementById("app");
    app.innerHTML = '<div class="loading">Loading...</div>';

    fetch("/api/preview")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        state.preview = data;
        state.view = "preview";
        render();
      })
      .catch(function (err) {
        state.error = String(err);
        renderError("Failed to load preview: " + err);
      });
  }

  function startUpload() {
    fetch("/api/upload", { method: "POST" })
      .then(function (r) {
        if (r.status === 409) {
          return r.json().then(function (d) {
            throw new Error(d.error || "Upload already running");
          });
        }
        if (!r.ok) {
          throw new Error("Unexpected response: " + r.status);
        }
        return r.json();
      })
      .then(function () {
        state.view = "uploading";
        render();
        schedulePoll();
      })
      .catch(function (err) {
        renderError("Could not start upload: " + err);
      });
  }

  function pollStatus() {
    fetch("/api/status")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        state.status = data;
        if (data.phase === "done") {
          state.view = "done";
          clearPoll();
          render();
        } else {
          // Still running -- re-render progress then schedule next poll
          render();
          schedulePoll();
        }
      })
      .catch(function () {
        // Transient network error -- retry silently
        schedulePoll();
      });
  }

  function schedulePoll() {
    clearPoll();
    state.pollTimer = setTimeout(pollStatus, 1500);
  }

  function clearPoll() {
    if (state.pollTimer !== null) {
      clearTimeout(state.pollTimer);
      state.pollTimer = null;
    }
  }

  // -----------------------------------------------------------------------
  // Render dispatch
  // -----------------------------------------------------------------------

  function render() {
    if (state.view === "preview") {
      renderPreview(state.preview);
    } else if (state.view === "uploading") {
      renderUploading(state.status);
    } else if (state.view === "done") {
      renderDone(state.status);
    }
  }

  // -----------------------------------------------------------------------
  // State 1: Preview + consent
  // -----------------------------------------------------------------------

  function renderPreview(data) {
    var app = document.getElementById("app");
    var candidates = (data && data.candidates) || [];
    var totalBytes = (data && data.total_bytes) || 0;
    var configured = data && data.sc_root_configured;
    var alreadyCount = (data && data.already_uploaded_count) || 0;

    var html = "";

    // Subheader from server
    if (data && data.header) {
      html += '<p class="subheader">' + esc(data.header) + "</p>";
    }

    // Consent box
    html += buildConsentBox();

    // File list or empty state
    if (!configured) {
      html += buildEmptyState(
        "Star Citizen path is not configured in skill settings. Configure it, then refresh.",
        true
      );
    } else if (candidates.length === 0 && alreadyCount > 0) {
      html += buildEmptyState(
        "All eligible logs have already been donated. Thanks!",
        true
      );
    } else if (candidates.length === 0) {
      html += buildEmptyState("No Star Citizen logs found to donate.", false);
    } else {
      html += buildFileList(candidates);
    }

    // Donate button
    var btnLabel =
      candidates.length > 0
        ? "Donate " + candidates.length + " log" + (candidates.length !== 1 ? "s" : "") +
          " (" + formatBytes(totalBytes) + ")"
        : "Donate logs";
    var disabled = candidates.length === 0 ? " disabled" : "";
    html +=
      '<div class="action-row">' +
      '<button id="btn-donate" class="btn-primary"' + disabled + ">" + esc(btnLabel) + "</button>" +
      "</div>";

    app.innerHTML = html;

    var btn = document.getElementById("btn-donate");
    if (btn && !btn.disabled) {
      btn.addEventListener("click", startUpload);
    }
  }

  function buildConsentBox() {
    return (
      '<div class="consent-box">' +
      '<h2>What you are donating</h2>' +
      '<div class="consent-body">' +
      "<p>Donating your Star Citizen logs helps improve sc_log_reader's parsing.</p>" +
      "<p>Logs contain in-game activity, including:</p>" +
      "<ul>" +
      "<li>In-game chat</li>" +
      "<li>Player handle and character names</li>" +
      "<li>Locations, missions, and deaths</li>" +
      "<li>Hangar / loadout details and vehicle ownership</li>" +
      "<li>In-game purchases and party / org membership</li>" +
      "<li>Kill events and error stacks</li>" +
      "</ul>" +
      "<p>Logs are sent to a private donation server (Cloudflare R2). They are not made public and are used only to improve the skill.</p>" +
      "<p>No background uploads happen. Donation only runs when you click the button. You can review what is about to be sent before confirming.</p>" +
      "</div>" +
      "</div>"
    );
  }

  function buildFileList(candidates) {
    var rows = candidates
      .map(function (c) {
        return (
          '<div class="file-row">' +
          '<span class="' + badgeClass(c.install) + '">' + esc(c.install) + "</span>" +
          '<span class="file-name">' + esc(c.renamed) + "</span>" +
          '<span class="file-size">' + esc(formatBytes(c.size_bytes)) + "</span>" +
          '<span class="file-handle">' + esc(c.handle) + "</span>" +
          "</div>"
        );
      })
      .join("");

    return (
      '<div class="file-list-header">Files to donate</div>' +
      '<div class="file-list">' + rows + "</div>"
    );
  }

  function buildEmptyState(message, showRefresh) {
    var btn = showRefresh
      ? '<br><br><button class="btn-secondary" id="btn-refresh">Refresh</button>'
      : "";
    return (
      '<div class="empty-state">' + esc(message) + btn + "</div>"
    );
  }

  // -----------------------------------------------------------------------
  // State 2: Uploading
  // -----------------------------------------------------------------------

  function renderUploading(statusData) {
    var app = document.getElementById("app");
    var progress = (statusData && statusData.progress) || { done: 0, total: 0 };
    var total = progress.total || 0;
    var done = progress.done || 0;
    var pct = total > 0 ? Math.round((done / total) * 100) : 0;
    var startedAt = statusData && statusData.started_at;

    var html =
      '<div class="progress-section">' +
      '<p class="progress-label">Uploading logs...</p>' +
      '<div class="progress-bar-track">' +
      '<div class="progress-bar-fill" style="width: ' + pct + '%"></div>' +
      "</div>" +
      '<p class="progress-label">' + done + " of " + total + " uploaded</p>";

    if (startedAt) {
      html +=
        '<p class="progress-subtext">Started ' + esc(relativeTime(startedAt)) + "</p>";
    }

    html += "</div>";

    app.innerHTML = html;
  }

  // -----------------------------------------------------------------------
  // State 3: Done
  // -----------------------------------------------------------------------

  function renderDone(statusData) {
    var app = document.getElementById("app");
    var result = statusData && statusData.result;
    var html = "";

    if (!result) {
      html += '<p class="result-header error">Donation failed (no result returned).</p>';
    } else if (result.top_level_error) {
      html +=
        '<p class="result-header error">Donation failed: ' + esc(result.top_level_error) + "</p>";
    } else if (result.failed_count > 0) {
      var total = result.succeeded_count + result.failed_count;
      html +=
        '<p class="result-header partial">Donated ' + result.succeeded_count + " of " + total + " logs.</p>" +
        '<p class="result-subtext">' +
        result.failed_count +
        " log" + (result.failed_count !== 1 ? "s" : "") + " failed and will retry on next run.</p>";
    } else {
      var mb = formatBytes(result.total_bytes_uploaded || 0);
      html +=
        '<p class="result-header success">Thanks! Donated ' +
        result.succeeded_count +
        " log" + (result.succeeded_count !== 1 ? "s" : "") +
        " (" + mb + ").</p>";
    }

    // File-by-file result table
    if (result && result.files && result.files.length > 0) {
      html += buildResultTable(result.files);
    }

    // Action row
    html +=
      '<div class="action-row">' +
      '<button class="btn-secondary" id="btn-donate-more">Donate more logs</button>' +
      "</div>" +
      '<p class="close-hint">You can close this tab. The donation state is saved.</p>';

    app.innerHTML = html;

    var btn = document.getElementById("btn-donate-more");
    if (btn) {
      btn.addEventListener("click", function () {
        // Reset server-side job state so the next preview re-runs discovery.
        // Without this the server still reports phase="done" and we land back
        // on this same screen after reload.
        fetch("/api/reset", { method: "POST" })
          .finally(function () { window.location.reload(); });
      });
    }
  }

  function buildResultTable(files) {
    var rows = files
      .map(function (f) {
        var statusLabel, statusClass;
        if (f.already_uploaded) {
          statusLabel = "Already uploaded";
          statusClass = "status-already";
        } else if (f.succeeded) {
          statusLabel = "Succeeded";
          statusClass = "status-succeeded";
        } else {
          statusLabel = "Failed";
          statusClass = "status-failed";
        }
        var errorCell = f.error
          ? '<span class="error-cell">' + esc(f.error) + "</span>"
          : "";
        return (
          "<tr>" +
          "<td>" + esc(f.renamed) + "</td>" +
          '<td class="' + statusClass + '">' + statusLabel + "</td>" +
          "<td>" + errorCell + "</td>" +
          "</tr>"
        );
      })
      .join("");

    return (
      '<table class="result-table">' +
      "<thead><tr><th>File</th><th>Status</th><th>Error</th></tr></thead>" +
      "<tbody>" + rows + "</tbody>" +
      "</table>"
    );
  }

  // -----------------------------------------------------------------------
  // Error display
  // -----------------------------------------------------------------------

  function renderError(msg) {
    var app = document.getElementById("app");
    app.innerHTML =
      '<div class="empty-state">' +
      esc(msg) +
      '<br><br><button class="btn-secondary" id="btn-retry">Retry</button>' +
      "</div>";
    var btn = document.getElementById("btn-retry");
    if (btn) {
      btn.addEventListener("click", loadPreview);
    }
  }

  // -----------------------------------------------------------------------
  // Delegated event: refresh button inside empty-state
  // -----------------------------------------------------------------------

  document.addEventListener("click", function (e) {
    if (e.target && e.target.id === "btn-refresh") {
      loadPreview();
    }
  });

  // -----------------------------------------------------------------------
  // Boot
  // -----------------------------------------------------------------------

  document.addEventListener("DOMContentLoaded", function () {
    // Check if an upload is already in progress (e.g. page reload mid-run)
    fetch("/api/status")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.phase === "running") {
          state.view = "uploading";
          state.status = data;
          render();
          schedulePoll();
        } else if (data.phase === "done") {
          state.view = "done";
          state.status = data;
          render();
        } else {
          loadPreview();
        }
      })
      .catch(function () {
        loadPreview();
      });
  });
})();
