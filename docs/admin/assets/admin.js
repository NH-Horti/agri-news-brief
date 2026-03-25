(function () {
  const DATA_FILES = {
    summary: "./data/summary.json",
    timeseries: "./data/timeseries.json",
    articles: "./data/top_articles.json",
    navigation: "./data/navigation.json",
    search: "./data/search_terms.json",
    health: "./data/health.json",
  };

  const state = {
    range: "7",
    compare: true,
    section: "",
    surface: "",
    from: "",
    to: "",
  };

  const model = {
    summary: { windows: {} },
    timeseries: { daily: [] },
    articles: { rows: [] },
    navigation: { section_jump: [], view_switch: [], archive_nav: [] },
    search: { rows: [] },
    health: { warnings: [], collection: {}, pipeline: {} },
  };

  const nodes = {
    statusBadge: document.getElementById("statusBadge"),
    lastUpdated: document.getElementById("lastUpdated"),
    compareToggle: document.getElementById("compareToggle"),
    sectionFilter: document.getElementById("sectionFilter"),
    surfaceFilter: document.getElementById("surfaceFilter"),
    fromDate: document.getElementById("fromDate"),
    toDate: document.getElementById("toDate"),
    applyCustomRange: document.getElementById("applyCustomRange"),
    kpiGrid: document.getElementById("kpiGrid"),
    trendChart: document.getElementById("trendChart"),
    sectionBars: document.getElementById("sectionBars"),
    topArticlesBody: document.getElementById("topArticlesBody"),
    articleSummary: document.getElementById("articleSummary"),
    navigationMetrics: document.getElementById("navigationMetrics"),
    searchTerms: document.getElementById("searchTerms"),
    healthState: document.getElementById("healthState"),
    rangeLabel: document.getElementById("rangeLabel"),
  };

  const SECTION_LABELS = {
    supply: "Supply",
    policy: "Policy",
    dist: "Distribution",
    pest: "Risk",
  };

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function toNumber(value) {
    const num = Number(value);
    return Number.isFinite(num) ? num : 0;
  }

  function toInt(value) {
    return Math.round(toNumber(value));
  }

  function parseDate(value) {
    if (!value) return null;
    const text = String(value).trim();
    const iso = /^\d{8}$/.test(text)
      ? `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)}`
      : text;
    const date = new Date(`${iso}T00:00:00`);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function isoDate(value) {
    if (!value) return "";
    const date = parseDate(value);
    if (!date) return "";
    return date.toISOString().slice(0, 10);
  }

  function formatNumber(value) {
    return new Intl.NumberFormat("ko-KR").format(toInt(value));
  }

  function formatPercent(value) {
    return `${(toNumber(value) * 100).toFixed(1)}%`;
  }

  function formatDelta(value) {
    const num = toNumber(value);
    if (!Number.isFinite(num) || num === 0) return "0.0%";
    return `${num > 0 ? "+" : ""}${(num * 100).toFixed(1)}%`;
  }

  function deltaClass(value) {
    const num = toNumber(value);
    if (num > 0.001) return "up";
    if (num < -0.001) return "down";
    return "flat";
  }

  function formatDuration(seconds) {
    const total = Math.max(0, toInt(seconds));
    const minutes = Math.floor(total / 60);
    const remain = total % 60;
    return `${String(minutes).padStart(2, "0")}:${String(remain).padStart(2, "0")}`;
  }

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>"']/g, function (char) {
      return ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[char];
    });
  }

  function fetchJson(url, fallback) {
    return fetch(`${url}?t=${Date.now()}`, { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
      })
      .catch(function () {
        return fallback;
      });
  }

  function sortByDate(rows) {
    return safeArray(rows).slice().sort(function (a, b) {
      return isoDate(a.date).localeCompare(isoDate(b.date));
    });
  }

  function latestDate() {
    const daily = sortByDate(model.timeseries.daily);
    return daily.length ? isoDate(daily[daily.length - 1].date) : "";
  }

  function shiftDate(dateText, days) {
    const date = parseDate(dateText);
    if (!date) return "";
    date.setDate(date.getDate() + days);
    return date.toISOString().slice(0, 10);
  }

  function daysBetweenInclusive(fromText, toText) {
    const from = parseDate(fromText);
    const to = parseDate(toText);
    if (!from || !to) return 0;
    return Math.max(1, Math.round((to - from) / 86400000) + 1);
  }

  function resolveRange() {
    const maxDate = latestDate();
    if (!maxDate) {
      return { from: "", to: "", label: "No data" };
    }

    if (state.range === "custom") {
      const from = state.from || state.to || maxDate;
      const to = state.to || state.from || maxDate;
      return {
        from: from <= to ? from : to,
        to: from <= to ? to : from,
        label: `${from} to ${to}`,
      };
    }

    const days = Number(state.range) || 7;
    const from = shiftDate(maxDate, -(days - 1));
    return {
      from,
      to: maxDate,
      label: `Last ${days} days`,
    };
  }

  function previousRange(range) {
    const length = daysBetweenInclusive(range.from, range.to);
    const prevTo = shiftDate(range.from, -1);
    const prevFrom = shiftDate(prevTo, -(length - 1));
    return {
      from: prevFrom,
      to: prevTo,
    };
  }

  function rowInRange(row, range) {
    const day = isoDate(row.date);
    return !!day && day >= range.from && day <= range.to;
  }

  function filterRows(rows, range, predicate) {
    return safeArray(rows).filter(function (row) {
      if (!rowInRange(row, range)) return false;
      return predicate ? predicate(row) : true;
    });
  }

  function summaryWindowKey() {
    if (state.section || state.surface || state.range === "custom") return "";
    return String(state.range || "");
  }

  function aggregateDailyMetrics(rows, articleRows) {
    const totals = {
      visits: 0,
      users: 0,
      pageviews: 0,
      article_clicks: 0,
      avg_engagement_sec: 0,
    };

    const sessionWeight = rows.reduce(function (sum, row) {
      return sum + toNumber(row.visits);
    }, 0);

    rows.forEach(function (row) {
      totals.visits += toNumber(row.visits);
      totals.users += toNumber(row.users);
      totals.pageviews += toNumber(row.pageviews);
    });

    totals.article_clicks = articleRows.reduce(function (sum, row) {
      return sum + toNumber(row.clicks);
    }, 0);

    const weightedEngagement = rows.reduce(function (sum, row) {
      return sum + (toNumber(row.avg_engagement_sec) * toNumber(row.visits));
    }, 0);
    totals.avg_engagement_sec = sessionWeight ? (weightedEngagement / sessionWeight) : 0;
    totals.article_ctr = totals.pageviews ? (totals.article_clicks / totals.pageviews) : 0;
    return totals;
  }

  function overrideWithSummary(totals) {
    const key = summaryWindowKey();
    const windowSummary = key ? (((model.summary || {}).windows || {})[key] || null) : null;
    if (!windowSummary || !windowSummary.totals) return totals;
    return Object.assign({}, totals, windowSummary.totals);
  }

  function previousTotals(range, articlePredicate) {
    const compareRange = previousRange(range);
    const dailyRows = filterRows(model.timeseries.daily, compareRange);
    const articleRows = filterRows(model.articles.rows, compareRange, articlePredicate);
    const totals = aggregateDailyMetrics(dailyRows, articleRows);
    const key = summaryWindowKey();
    const windowSummary = key ? (((model.summary || {}).windows || {})[key] || null) : null;
    if (windowSummary && windowSummary.prev && !state.section && !state.surface) {
      return Object.assign({}, totals, windowSummary.prev);
    }
    return totals;
  }

  function aggregateArticles(range) {
    const rows = filterRows(model.articles.rows, range, function (row) {
      if (state.section && row.section !== state.section) return false;
      if (state.surface && row.surface !== state.surface) return false;
      return true;
    });
    const grouped = new Map();
    rows.forEach(function (row) {
      const id = row.article_id || row.articleId || row.id || `${row.title}|${row.date}|${row.section}`;
      const current = grouped.get(id) || {
        article_id: id,
        title: row.title || "Untitled",
        date: row.report_date || row.date || "",
        section: row.section || "",
        surface_top: row.surface || "",
        clicks: 0,
        users: 0,
        archive_url: row.archive_url || "",
        source_url: row.source_url || "",
        target_domain: row.target_domain || "",
        surfaces: {},
      };
      current.clicks += toNumber(row.clicks);
      current.users += toNumber(row.users);
      current.date = current.date || row.report_date || row.date || "";
      current.section = current.section || row.section || "";
      current.archive_url = current.archive_url || row.archive_url || "";
      current.source_url = current.source_url || row.source_url || "";
      current.target_domain = current.target_domain || row.target_domain || "";
      current.surfaces[row.surface || "unknown"] = (current.surfaces[row.surface || "unknown"] || 0) + toNumber(row.clicks);
      grouped.set(id, current);
    });

    const items = Array.from(grouped.values()).map(function (item) {
      let topSurface = item.surface_top;
      let maxClicks = -1;
      Object.keys(item.surfaces).forEach(function (surface) {
        const clicks = item.surfaces[surface];
        if (clicks > maxClicks) {
          maxClicks = clicks;
          topSurface = surface;
        }
      });
      item.surface_top = topSurface || "";
      return item;
    });

    items.sort(function (a, b) {
      if (toNumber(b.clicks) !== toNumber(a.clicks)) return toNumber(b.clicks) - toNumber(a.clicks);
      return String(b.date || "").localeCompare(String(a.date || ""));
    });

    return {
      rows,
      items,
    };
  }

  function aggregateSections(articleRows) {
    const totals = {};
    articleRows.forEach(function (row) {
      const key = row.section || "unknown";
      totals[key] = (totals[key] || 0) + toNumber(row.clicks);
    });
    const entries = Object.keys(totals).map(function (key) {
      return {
        section: key,
        label: SECTION_LABELS[key] || key,
        clicks: totals[key],
      };
    });
    entries.sort(function (a, b) {
      return b.clicks - a.clicks;
    });
    return entries;
  }

  function aggregateNavigation(range) {
    const navSection = filterRows(model.navigation.section_jump, range, function () { return true; });
    const navView = filterRows(model.navigation.view_switch, range, function () { return true; });
    const navArchive = filterRows(model.navigation.archive_nav, range, function () { return true; });

    const sectionJumpCount = navSection.reduce(function (sum, row) { return sum + toNumber(row.count); }, 0);
    const commoditySwitchCount = navView
      .filter(function (row) { return row.to_view === "commodity"; })
      .reduce(function (sum, row) { return sum + toNumber(row.count); }, 0);
    const archivePrev = navArchive
      .filter(function (row) { return row.nav_type === "prev"; })
      .reduce(function (sum, row) { return sum + toNumber(row.count); }, 0);
    const archiveNext = navArchive
      .filter(function (row) { return row.nav_type === "next"; })
      .reduce(function (sum, row) { return sum + toNumber(row.count); }, 0);
    const archiveSelect = navArchive
      .filter(function (row) { return row.nav_type === "select"; })
      .reduce(function (sum, row) { return sum + toNumber(row.count); }, 0);

    return [
      { label: "Section jumps", value: sectionJumpCount, note: `${navSection.length} daily records` },
      { label: "Commodity tab entries", value: commoditySwitchCount, note: `${navView.length} switch records` },
      { label: "Prev / next clicks", value: archivePrev + archiveNext, note: `${formatNumber(archivePrev)} prev, ${formatNumber(archiveNext)} next` },
      { label: "Date picker jumps", value: archiveSelect, note: "Direct archive selection" },
    ];
  }

  function aggregateSearch(range) {
    const rows = filterRows(model.search.rows, range, function () { return true; });
    const grouped = new Map();
    rows.forEach(function (row) {
      const query = (row.query || "").trim();
      if (!query) return;
      const current = grouped.get(query) || {
        query,
        count: 0,
        result_weighted: 0,
      };
      current.count += toNumber(row.count);
      current.result_weighted += toNumber(row.result_count) * toNumber(row.count);
      grouped.set(query, current);
    });
    const items = Array.from(grouped.values()).map(function (item) {
      item.avg_result_count = item.count ? (item.result_weighted / item.count) : 0;
      return item;
    });
    items.sort(function (a, b) {
      return b.count - a.count;
    });
    return items;
  }

  function rangeLabel(range) {
    return `${range.from || "-"} to ${range.to || "-"}`;
  }

  function renderCards(totals, previous) {
    const compare = state.compare;
    const cardDefs = [
      { key: "visits", label: "Visits", format: formatNumber },
      { key: "users", label: "Users", format: formatNumber },
      { key: "pageviews", label: "Pageviews", format: formatNumber },
      { key: "article_clicks", label: "Article Clicks", format: formatNumber },
      { key: "article_ctr", label: "Article CTR", format: formatPercent },
      { key: "avg_engagement_sec", label: "Avg Engage", format: formatDuration },
    ];

    nodes.kpiGrid.innerHTML = cardDefs.map(function (card) {
      const value = toNumber(totals[card.key]);
      const prev = toNumber(previous[card.key]);
      let delta = 0;
      if (card.key === "article_ctr" || card.key === "avg_engagement_sec") {
        delta = prev ? ((value - prev) / prev) : 0;
      } else {
        delta = prev ? ((value - prev) / prev) : 0;
      }
      return [
        '<article class="kpiCard">',
        `<div class="kpiLabel">${escapeHtml(card.label)}</div>`,
        `<div class="kpiValue">${escapeHtml(card.format(value))}</div>`,
        `<div class="kpiDelta ${deltaClass(delta)}">${compare ? escapeHtml(formatDelta(delta)) : "Compare off"}</div>`,
        "</article>",
      ].join("");
    }).join("");
  }

  function renderTrendChart(range, articleRows) {
    const dailyRows = sortByDate(filterRows(model.timeseries.daily, range));
    const articleMap = {};
    articleRows.forEach(function (row) {
      const day = isoDate(row.date);
      articleMap[day] = (articleMap[day] || 0) + toNumber(row.clicks);
    });

    if (!dailyRows.length) {
      nodes.trendChart.innerHTML = '<div class="emptyState">No time series data available for the selected range.</div>';
      return;
    }

    const width = 760;
    const height = 260;
    const padding = 18;
    const valuesA = dailyRows.map(function (row) { return toNumber(row.visits); });
    const valuesB = dailyRows.map(function (row) { return toNumber(articleMap[isoDate(row.date)] || 0); });
    const maxValue = Math.max(1, ...valuesA, ...valuesB);

    function toPoints(values) {
      return values.map(function (value, index) {
        const x = padding + ((width - padding * 2) * (dailyRows.length === 1 ? 0.5 : index / (dailyRows.length - 1)));
        const y = height - padding - ((height - padding * 2) * (value / maxValue));
        return `${x.toFixed(2)},${y.toFixed(2)}`;
      }).join(" ");
    }

    const labels = dailyRows.map(function (row, index) {
      if (dailyRows.length > 10 && index % Math.ceil(dailyRows.length / 6) !== 0 && index !== dailyRows.length - 1) return "";
      return `<text x="${padding + ((width - padding * 2) * (dailyRows.length === 1 ? 0.5 : index / (dailyRows.length - 1)))}" y="${height - 4}" text-anchor="middle" fill="#5f6b76" font-size="11">${escapeHtml(isoDate(row.date).slice(5))}</text>`;
    }).join("");

    nodes.trendChart.innerHTML = [
      `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Visits and article clicks trend">`,
      `<polyline fill="none" stroke="#16202a" stroke-width="3" points="${toPoints(valuesA)}"></polyline>`,
      `<polyline fill="none" stroke="#0f766e" stroke-width="3" points="${toPoints(valuesB)}"></polyline>`,
      labels,
      "</svg>",
      '<div class="chartLegend">',
      '<span><span class="legendDot" style="background:#16202a"></span>Visits</span>',
      '<span><span class="legendDot" style="background:#0f766e"></span>Article clicks</span>',
      "</div>",
    ].join("");
  }

  function renderSectionBars(items) {
    if (!items.length) {
      nodes.sectionBars.innerHTML = '<div class="emptyState">No article click data for this range.</div>';
      return;
    }
    const max = Math.max(1, ...items.map(function (item) { return item.clicks; }));
    nodes.sectionBars.innerHTML = items.map(function (item) {
      const pct = (item.clicks / max) * 100;
      return [
        '<div class="barRow">',
        `<div class="barMeta"><span>${escapeHtml(item.label)}</span><span>${escapeHtml(formatNumber(item.clicks))}</span></div>`,
        `<div class="barTrack"><div class="barFill" style="width:${pct.toFixed(2)}%"></div></div>`,
        "</div>",
      ].join("");
    }).join("");
  }

  function renderTopArticles(items) {
    nodes.articleSummary.textContent = items.length ? `${items.length} aggregated rows` : "No article clicks found";
    if (!items.length) {
      nodes.topArticlesBody.innerHTML = '<tr><td colspan="8"><div class="emptyState">No article click data available.</div></td></tr>';
      return;
    }

    nodes.topArticlesBody.innerHTML = items.slice(0, 12).map(function (item, index) {
      const sectionLabel = SECTION_LABELS[item.section] || item.section || "-";
      return [
        "<tr>",
        `<td>${index + 1}</td>`,
        `<td><strong>${escapeHtml(item.title)}</strong><span class="muted">${escapeHtml(item.target_domain || "-")}</span></td>`,
        `<td>${escapeHtml(item.date || "-")}</td>`,
        `<td>${escapeHtml(sectionLabel)}</td>`,
        `<td>${escapeHtml(formatNumber(item.clicks))}</td>`,
        `<td>${escapeHtml(formatNumber(item.users))}</td>`,
        `<td>${escapeHtml(item.surface_top || "-")}</td>`,
        `<td><div class="tableLinks">${item.archive_url ? `<a href="${escapeHtml(item.archive_url)}" target="_blank" rel="noopener">Archive</a>` : ""}${item.source_url ? `<a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener">Source</a>` : ""}</div></td>`,
        "</tr>",
      ].join("");
    }).join("");
  }

  function renderNavigation(items) {
    nodes.navigationMetrics.innerHTML = items.map(function (item) {
      return [
        '<div class="metricItem">',
        `<strong>${escapeHtml(formatNumber(item.value))}</strong>`,
        `<div>${escapeHtml(item.label)}</div>`,
        `<div class="muted">${escapeHtml(item.note || "")}</div>`,
        "</div>",
      ].join("");
    }).join("");
  }

  function renderSearch(items) {
    if (!items.length) {
      nodes.searchTerms.innerHTML = '<div class="emptyState">No search events available.</div>';
      return;
    }
    nodes.searchTerms.innerHTML = items.slice(0, 8).map(function (item) {
      return [
        '<div class="listItem">',
        `<strong>${escapeHtml(item.query)}</strong>`,
        `<div>${escapeHtml(formatNumber(item.count))} searches</div>`,
        `<div class="muted">Avg results ${escapeHtml(item.avg_result_count.toFixed(1))}</div>`,
        "</div>",
      ].join("");
    }).join("");
  }

  function renderHealth() {
    const warnings = safeArray(model.health.warnings);
    const trackingEnabled = !!(model.health.collection && model.health.collection.tracking_enabled);
    const pipelineStatus = ((model.health.pipeline || {}).status || "unknown").toLowerCase();

    let statusText = "Healthy";
    let statusClass = "statusOk";
    if (!trackingEnabled || pipelineStatus !== "ok") {
      statusText = "Attention";
      statusClass = "statusWarn";
    }
    if (warnings.length) {
      statusText = "Warnings";
      statusClass = "statusWarn";
    }

    nodes.statusBadge.textContent = statusText;
    nodes.statusBadge.className = statusClass;
    nodes.lastUpdated.textContent = model.health.generated_at || model.summary.generated_at || "-";

    const items = [
      {
        title: "Tracking enabled",
        value: trackingEnabled ? "Yes" : "No",
      },
      {
        title: "Last event",
        value: (model.health.collection || {}).last_event_at || "No event data",
      },
      {
        title: "Pipeline",
        value: (model.health.pipeline || {}).status || "unknown",
      },
      {
        title: "Last pipeline success",
        value: (model.health.pipeline || {}).last_success_at || "-",
      },
    ];

    if (warnings.length) {
      warnings.forEach(function (warning) {
        items.push({
          title: "Warning",
          value: warning,
        });
      });
    }

    nodes.healthState.innerHTML = items.map(function (item) {
      return [
        '<div class="healthItem">',
        `<strong>${escapeHtml(item.title)}</strong>`,
        `<div class="muted">${escapeHtml(item.value)}</div>`,
        "</div>",
      ].join("");
    }).join("");
  }

  function render() {
    const range = resolveRange();
    nodes.rangeLabel.textContent = rangeLabel(range);

    const articleAggregate = aggregateArticles(range);
    const dailyRows = filterRows(model.timeseries.daily, range);
    const totals = overrideWithSummary(aggregateDailyMetrics(dailyRows, articleAggregate.rows));
    const previous = state.compare
      ? previousTotals(range, function (row) {
          if (state.section && row.section !== state.section) return false;
          if (state.surface && row.surface !== state.surface) return false;
          return true;
        })
      : {};

    renderCards(totals, previous);
    renderTrendChart(range, articleAggregate.rows);
    renderSectionBars(aggregateSections(articleAggregate.rows));
    renderTopArticles(articleAggregate.items);
    renderNavigation(aggregateNavigation(range));
    renderSearch(aggregateSearch(range));
    renderHealth();
  }

  function populateFilters() {
    const sections = new Set();
    const surfaces = new Set();
    safeArray(model.articles.rows).forEach(function (row) {
      if (row.section) sections.add(row.section);
      if (row.surface) surfaces.add(row.surface);
    });

    Array.from(sections).sort().forEach(function (section) {
      const option = document.createElement("option");
      option.value = section;
      option.textContent = SECTION_LABELS[section] || section;
      nodes.sectionFilter.appendChild(option);
    });

    Array.from(surfaces).sort().forEach(function (surface) {
      const option = document.createElement("option");
      option.value = surface;
      option.textContent = surface;
      nodes.surfaceFilter.appendChild(option);
    });

    const last = latestDate();
    nodes.toDate.value = last;
    nodes.fromDate.value = shiftDate(last, -6);
    state.from = nodes.fromDate.value;
    state.to = nodes.toDate.value;
  }

  function bindEvents() {
    document.querySelectorAll("[data-range]").forEach(function (button) {
      button.addEventListener("click", function () {
        document.querySelectorAll("[data-range]").forEach(function (node) {
          node.classList.toggle("isActive", node === button);
        });
        state.range = button.getAttribute("data-range") || "7";
        if (state.range !== "custom") {
          const range = resolveRange();
          state.from = range.from;
          state.to = range.to;
          nodes.fromDate.value = range.from;
          nodes.toDate.value = range.to;
        }
        render();
      });
    });

    nodes.compareToggle.addEventListener("change", function () {
      state.compare = !!nodes.compareToggle.checked;
      render();
    });

    nodes.sectionFilter.addEventListener("change", function () {
      state.section = nodes.sectionFilter.value || "";
      render();
    });

    nodes.surfaceFilter.addEventListener("change", function () {
      state.surface = nodes.surfaceFilter.value || "";
      render();
    });

    nodes.applyCustomRange.addEventListener("click", function () {
      state.range = "custom";
      state.from = nodes.fromDate.value || state.from;
      state.to = nodes.toDate.value || state.to;
      document.querySelectorAll("[data-range]").forEach(function (node) {
        node.classList.toggle("isActive", node.getAttribute("data-range") === "custom");
      });
      render();
    });
  }

  Promise.all([
    fetchJson(DATA_FILES.summary, model.summary),
    fetchJson(DATA_FILES.timeseries, model.timeseries),
    fetchJson(DATA_FILES.articles, model.articles),
    fetchJson(DATA_FILES.navigation, model.navigation),
    fetchJson(DATA_FILES.search, model.search),
    fetchJson(DATA_FILES.health, model.health),
  ]).then(function (results) {
    model.summary = results[0] || model.summary;
    model.timeseries = results[1] || model.timeseries;
    model.articles = results[2] || model.articles;
    model.navigation = results[3] || model.navigation;
    model.search = results[4] || model.search;
    model.health = results[5] || model.health;

    populateFilters();
    bindEvents();
    render();
  });
})();
