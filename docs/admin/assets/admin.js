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

  const SURFACE_LABELS = {
    briefing_card: "Briefing card",
    btn_open: "Open button",
    commodity_primary: "Commodity primary",
    commodity_support: "Commodity support",
    search_result: "Search result",
    archive_card: "Archive card",
    home_card: "Home card",
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
    return date ? date.toISOString().slice(0, 10) : "";
  }

  function rowDate(row) {
    return isoDate((row || {}).date || (row || {}).report_date || "");
  }

  function formatNumber(value) {
    return new Intl.NumberFormat("en-US").format(toInt(value));
  }

  function formatPercent(value) {
    return `${(toNumber(value) * 100).toFixed(1)}%`;
  }

  function formatDuration(seconds) {
    const total = Math.max(0, toInt(seconds));
    const minutes = Math.floor(total / 60);
    const remain = total % 60;
    if (minutes <= 0) return `${remain}s`;
    return `${minutes}m ${String(remain).padStart(2, "0")}s`;
  }

  function formatDateRange(from, to) {
    return `${from || "-"} to ${to || "-"}`;
  }

  function formatDateShort(value) {
    const text = isoDate(value);
    if (!text) return "-";
    return text.slice(5);
  }

  function formatTimestamp(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "Asia/Seoul",
    }).format(date);
  }

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>\"']/g, function (char) {
      return ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;",
      })[char];
    });
  }

  function fetchJson(url, fallback) {
    return fetch(`${url}?t=${Date.now()}`, { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .catch(function () {
        return fallback;
      });
  }

  function humanizeSurface(value) {
    const key = String(value || "").trim();
    if (!key) return "-";
    if (SURFACE_LABELS[key]) return SURFACE_LABELS[key];
    return key.replace(/_/g, " ");
  }

  function sortByDate(rows) {
    return safeArray(rows).slice().sort(function (a, b) {
      return rowDate(a).localeCompare(rowDate(b));
    });
  }

  function latestDate() {
    const daily = sortByDate(model.timeseries.daily);
    return daily.length ? rowDate(daily[daily.length - 1]) : "";
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
      return { from: state.from || "", to: state.to || "", label: "No data" };
    }

    if (state.range === "custom") {
      const from = state.from || state.to || maxDate;
      const to = state.to || state.from || maxDate;
      const resolvedFrom = from <= to ? from : to;
      const resolvedTo = from <= to ? to : from;
      return {
        from: resolvedFrom,
        to: resolvedTo,
        label: formatDateRange(resolvedFrom, resolvedTo),
      };
    }

    const days = Number(state.range) || 7;
    const from = shiftDate(maxDate, -(days - 1));
    return {
      from: from,
      to: maxDate,
      label: formatDateRange(from, maxDate),
    };
  }

  function previousRange(range) {
    const length = daysBetweenInclusive(range.from, range.to);
    const prevTo = shiftDate(range.from, -1);
    const prevFrom = shiftDate(prevTo, -(length - 1));
    return { from: prevFrom, to: prevTo };
  }

  function rowInRange(row, range) {
    const day = rowDate(row);
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
        title: row.title || "Untitled article",
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

    return { rows: rows, items: items };
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
    const navSection = filterRows(model.navigation.section_jump, range);
    const navView = filterRows(model.navigation.view_switch, range);
    const navArchive = filterRows(model.navigation.archive_nav, range);

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
      {
        label: "Section jumps",
        value: sectionJumpCount,
        note: "Direct jumps through section chips",
      },
      {
        label: "Commodity board entries",
        value: commoditySwitchCount,
        note: "Switches from briefing into commodity mode",
      },
      {
        label: "Prev / next date moves",
        value: archivePrev + archiveNext,
        note: `${formatNumber(archivePrev)} prev / ${formatNumber(archiveNext)} next`,
      },
      {
        label: "Date picker moves",
        value: archiveSelect,
        note: "Direct archive date selections",
      },
    ];
  }

  function aggregateSearch(range) {
    const rows = filterRows(model.search.rows, range);
    const grouped = new Map();
    rows.forEach(function (row) {
      const query = String(row.query || "").trim();
      if (!query) return;
      const current = grouped.get(query) || {
        query: query,
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

  function comparisonState(current, previous, enabled) {
    if (!enabled) return { text: "compare off", className: "flat" };
    if (previous <= 0 && current <= 0) return { text: "no baseline", className: "flat" };
    if (previous <= 0 && current > 0) return { text: "new activity", className: "up" };
    const delta = ((current - previous) / previous) || 0;
    if (delta > 0.001) return { text: `+${(delta * 100).toFixed(1)}%`, className: "up" };
    if (delta < -0.001) return { text: `${(delta * 100).toFixed(1)}%`, className: "down" };
    return { text: "flat", className: "flat" };
  }

  function renderCards(totals, previous) {
    const cardDefs = [
      { key: "visits", label: "Visits", code: "SESSIONS", format: formatNumber, hint: "Incoming session volume" },
      { key: "users", label: "Users", code: "USERS", format: formatNumber, hint: "Unique active users" },
      { key: "pageviews", label: "Pageviews", code: "PAGEVIEWS", format: formatNumber, hint: "Brief and archive views" },
      { key: "article_clicks", label: "Article clicks", code: "ARTICLE_OPENS", format: formatNumber, hint: "Outbound source clicks" },
      { key: "article_ctr", label: "Article CTR", code: "CTR", format: formatPercent, hint: "Clicks divided by pageviews" },
      { key: "avg_engagement_sec", label: "Avg engage", code: "AVG_TIME", format: formatDuration, hint: "Average engaged time" },
    ];

    nodes.kpiGrid.innerHTML = cardDefs.map(function (card) {
      const value = toNumber(totals[card.key]);
      const prev = toNumber(previous[card.key]);
      const comparison = comparisonState(value, prev, state.compare);
      return [
        '<article class="kpiCard">',
        '<div class="kpiTop">',
        `<div class="kpiLabel">${escapeHtml(card.label)}</div>`,
        `<div class="kpiTrend ${escapeHtml(comparison.className)}">${escapeHtml(comparison.text)}</div>`,
        "</div>",
        `<div class="kpiValue">${escapeHtml(card.format(value))}</div>`,
        '<div class="kpiMeta">',
        `<div class="kpiCode">${escapeHtml(card.code)}</div>`,
        `<div class="kpiHint">${escapeHtml(card.hint)}</div>`,
        "</div>",
        "</article>",
      ].join("");
    }).join("");
  }

  function renderTrendChart(range, articleRows) {
    const dailyRows = sortByDate(filterRows(model.timeseries.daily, range));
    const articleMap = {};
    articleRows.forEach(function (row) {
      const day = rowDate(row);
      articleMap[day] = (articleMap[day] || 0) + toNumber(row.clicks);
    });

    if (!dailyRows.length) {
      nodes.trendChart.innerHTML = '<div class="emptyState">No time series data for the selected window.</div>';
      return;
    }

    const width = 880;
    const height = 300;
    const paddingX = 28;
    const paddingTop = 18;
    const paddingBottom = 34;
    const innerHeight = height - paddingTop - paddingBottom;
    const valuesVisits = dailyRows.map(function (row) { return toNumber(row.visits); });
    const valuesClicks = dailyRows.map(function (row) { return toNumber(articleMap[rowDate(row)] || 0); });
    const maxValue = Math.max(1, ...valuesVisits, ...valuesClicks);
    const totalVisits = valuesVisits.reduce(function (sum, value) { return sum + value; }, 0);
    const totalClicks = valuesClicks.reduce(function (sum, value) { return sum + value; }, 0);
    const peakValue = Math.max(Math.max(0, ...valuesVisits), Math.max(0, ...valuesClicks));

    function pointFor(index, value) {
      const ratio = dailyRows.length === 1 ? 0.5 : index / (dailyRows.length - 1);
      const x = paddingX + ((width - paddingX * 2) * ratio);
      const y = paddingTop + (innerHeight - (innerHeight * (value / maxValue)));
      return { x: x, y: y };
    }

    function polyline(values) {
      return values.map(function (value, index) {
        const point = pointFor(index, value);
        return `${point.x.toFixed(2)},${point.y.toFixed(2)}`;
      }).join(" ");
    }

    function area(values) {
      const points = values.map(function (value, index) {
        const point = pointFor(index, value);
        return `${point.x.toFixed(2)},${point.y.toFixed(2)}`;
      }).join(" ");
      const first = pointFor(0, values[0] || 0);
      const last = pointFor(values.length - 1, values[values.length - 1] || 0);
      return `${first.x.toFixed(2)},${(height - paddingBottom).toFixed(2)} ${points} ${last.x.toFixed(2)},${(height - paddingBottom).toFixed(2)}`;
    }

    const visitPoints = polyline(valuesVisits);
    const clickPoints = polyline(valuesClicks);
    const visitArea = area(valuesVisits);
    const clickArea = area(valuesClicks);
    const lastVisit = pointFor(valuesVisits.length - 1, valuesVisits[valuesVisits.length - 1] || 0);
    const lastClick = pointFor(valuesClicks.length - 1, valuesClicks[valuesClicks.length - 1] || 0);

    const gridLines = [0, 0.25, 0.5, 0.75, 1].map(function (ratio) {
      const value = Math.round(maxValue * (1 - ratio));
      const y = paddingTop + (innerHeight * ratio);
      return [
        `<line x1="${paddingX}" y1="${y.toFixed(2)}" x2="${width - paddingX}" y2="${y.toFixed(2)}" stroke="rgba(152,169,192,0.18)" stroke-dasharray="4 8"></line>`,
        `<text x="${paddingX}" y="${(y - 8).toFixed(2)}" fill="#8fa1ba" font-size="11">${escapeHtml(formatNumber(value))}</text>`,
      ].join("");
    }).join("");

    const labels = dailyRows.map(function (row, index) {
      if (dailyRows.length > 10 && index % Math.ceil(dailyRows.length / 6) !== 0 && index !== dailyRows.length - 1) return "";
      const point = pointFor(index, 0);
      return `<text x="${point.x.toFixed(2)}" y="${(height - 8).toFixed(2)}" text-anchor="middle" fill="#8fa1ba" font-size="11">${escapeHtml(formatDateShort(rowDate(row)))}</text>`;
    }).join("");

    nodes.trendChart.innerHTML = [
      '<div class="chartSummary">',
      `<div class="chartStat"><span>Total visits</span><strong>${escapeHtml(formatNumber(totalVisits))}</strong></div>`,
      `<div class="chartStat"><span>Total clicks</span><strong>${escapeHtml(formatNumber(totalClicks))}</strong></div>`,
      `<div class="chartStat"><span>Peak day</span><strong>${escapeHtml(formatNumber(peakValue))}</strong></div>`,
      `<div class="chartStat"><span>Window</span><strong>${escapeHtml(formatDateRange(range.from, range.to))}</strong></div>`,
      "</div>",
      `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Sessions and article opens trend">`,
      "<defs>",
      '<linearGradient id="visitLine" x1="0%" y1="0%" x2="100%" y2="0%">',
      '<stop offset="0%" stop-color="#78c7ff"></stop>',
      '<stop offset="100%" stop-color="#d0e7ff"></stop>',
      "</linearGradient>",
      '<linearGradient id="clickLine" x1="0%" y1="0%" x2="100%" y2="0%">',
      '<stop offset="0%" stop-color="#9cf13c"></stop>',
      '<stop offset="100%" stop-color="#c9ff7a"></stop>',
      "</linearGradient>",
      '<linearGradient id="visitArea" x1="0%" y1="0%" x2="0%" y2="100%">',
      '<stop offset="0%" stop-color="rgba(120,199,255,0.28)"></stop>',
      '<stop offset="100%" stop-color="rgba(120,199,255,0.01)"></stop>',
      "</linearGradient>",
      '<linearGradient id="clickArea" x1="0%" y1="0%" x2="0%" y2="100%">',
      '<stop offset="0%" stop-color="rgba(156,241,60,0.22)"></stop>',
      '<stop offset="100%" stop-color="rgba(156,241,60,0.01)"></stop>',
      "</linearGradient>",
      "</defs>",
      gridLines,
      `<polygon fill="url(#visitArea)" points="${visitArea}"></polygon>`,
      `<polygon fill="url(#clickArea)" points="${clickArea}"></polygon>`,
      `<polyline fill="none" stroke="url(#visitLine)" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" points="${visitPoints}"></polyline>`,
      `<polyline fill="none" stroke="url(#clickLine)" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" points="${clickPoints}"></polyline>`,
      `<circle cx="${lastVisit.x.toFixed(2)}" cy="${lastVisit.y.toFixed(2)}" r="5" fill="#78c7ff"></circle>`,
      `<circle cx="${lastClick.x.toFixed(2)}" cy="${lastClick.y.toFixed(2)}" r="5" fill="#b8ff5a"></circle>`,
      labels,
      "</svg>",
      '<div class="chartLegend">',
      '<span><span class="legendDot" style="background:#78c7ff"></span>Sessions</span>',
      '<span><span class="legendDot" style="background:#b8ff5a"></span>Article opens</span>',
      "</div>",
    ].join("");
  }

  function renderSectionBars(items) {
    if (!items.length) {
      nodes.sectionBars.innerHTML = '<div class="emptyState">No section click data for the selected window.</div>';
      return;
    }

    const max = Math.max(1, ...items.map(function (item) { return item.clicks; }));
    const total = items.reduce(function (sum, item) { return sum + item.clicks; }, 0);
    nodes.sectionBars.innerHTML = items.map(function (item) {
      const pct = (item.clicks / max) * 100;
      const share = total ? formatPercent(item.clicks / total) : "0.0%";
      return [
        '<div class="barRow">',
        '<div class="barMeta">',
        '<div class="barLabelGroup">',
        `<span class="barLabel">${escapeHtml(item.label)}</span>`,
        `<span class="barNote">${escapeHtml(share)} of tracked article clicks</span>`,
        "</div>",
        `<strong class="barValue">${escapeHtml(formatNumber(item.clicks))}</strong>`,
        "</div>",
        `<div class="barTrack"><div class="barFill" style="width:${pct.toFixed(2)}%"></div></div>`,
        "</div>",
      ].join("");
    }).join("");
  }

  function renderTopArticles(items) {
    nodes.articleSummary.textContent = items.length
      ? `Showing the top 12 of ${formatNumber(items.length)} tracked article rows`
      : "No article clicks in the selected window";

    if (!items.length) {
      nodes.topArticlesBody.innerHTML = '<tr><td colspan="8"><div class="emptyState">No article click data available yet.</div></td></tr>';
      return;
    }

    nodes.topArticlesBody.innerHTML = items.slice(0, 12).map(function (item, index) {
      const sectionLabel = SECTION_LABELS[item.section] || item.section || "-";
      const rankClass = index < 3 ? "rankBadge top" : "rankBadge";
      return [
        "<tr>",
        `<td><span class="${rankClass}">${index + 1}</span></td>`,
        '<td><div class="articleCell">',
        `<strong class="articleTitle">${escapeHtml(item.title)}</strong>`,
        '<div class="articleMeta">',
        `<span>${escapeHtml(item.target_domain || "Unknown source")}</span>`,
        `<span>${escapeHtml(humanizeSurface(item.surface_top))}</span>`,
        "</div>",
        "</div></td>",
        `<td>${escapeHtml(item.date || "-")}</td>`,
        `<td>${escapeHtml(sectionLabel)}</td>`,
        `<td class="tableNumber">${escapeHtml(formatNumber(item.clicks))}</td>`,
        `<td class="tableNumber">${escapeHtml(formatNumber(item.users))}</td>`,
        `<td><span class="surfaceBadge">${escapeHtml(humanizeSurface(item.surface_top))}</span></td>`,
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
      nodes.searchTerms.innerHTML = '<div class="emptyState">No search events for the current window.</div>';
      return;
    }

    nodes.searchTerms.innerHTML = items.slice(0, 8).map(function (item) {
      return [
        '<div class="listItem">',
        `<strong>${escapeHtml(item.query)}</strong>`,
        `<div>${escapeHtml(formatNumber(item.count))} searches</div>`,
        `<div class="muted">Average results: ${escapeHtml(item.avg_result_count.toFixed(1))}</div>`,
        "</div>",
      ].join("");
    }).join("");
  }

  function renderHealth() {
    const warnings = safeArray(model.health.warnings);
    const trackingEnabled = !!(model.health.collection && model.health.collection.tracking_enabled);
    const pipelineStatus = String(((model.health.pipeline || {}).status || "unknown")).toLowerCase();

    let statusText = "idle";
    let statusClass = "statusIdle";

    if (pipelineStatus !== "ok") {
      statusText = "pipeline issue";
      statusClass = "statusError";
    } else if (warnings.length) {
      statusText = "attention";
      statusClass = "statusWarn";
    } else if (trackingEnabled) {
      statusText = "healthy";
      statusClass = "statusOk";
    }

    nodes.statusBadge.textContent = statusText;
    nodes.statusBadge.className = `statusPill ${statusClass}`;
    nodes.lastUpdated.textContent = formatTimestamp(model.health.generated_at || model.summary.generated_at || "");

    const items = [
      {
        title: "Tracking",
        value: trackingEnabled ? "Enabled" : "Disabled",
        note: trackingEnabled ? "Events are flowing into the property." : "No recent event signal detected yet.",
      },
      {
        title: "Last event",
        value: formatTimestamp((model.health.collection || {}).last_event_at || ""),
        note: (model.health.collection || {}).tracking_build_id
          ? `Build ${(model.health.collection || {}).tracking_build_id}`
          : "No build id available",
      },
      {
        title: "Pipeline",
        value: (model.health.pipeline || {}).status || "unknown",
        note: "Latest admin build job status",
      },
      {
        title: "Last success",
        value: formatTimestamp((model.health.pipeline || {}).last_success_at || ""),
        note: "Most recent successful dashboard data refresh",
      },
    ];

    warnings.forEach(function (warning) {
      items.push({
        title: "Warning",
        value: warning,
        note: "Review setup or collection state",
      });
    });

    nodes.healthState.innerHTML = items.map(function (item) {
      return [
        '<div class="healthItem">',
        `<strong>${escapeHtml(item.title)}</strong>`,
        `<div>${escapeHtml(item.value || "-")}</div>`,
        `<div class="muted">${escapeHtml(item.note || "")}</div>`,
        "</div>",
      ].join("");
    }).join("");
  }

  function render() {
    const range = resolveRange();
    nodes.rangeLabel.textContent = range.label || formatDateRange(range.from, range.to);

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
      option.textContent = humanizeSurface(surface);
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
    document.body.classList.add("isReady");
  });
})();
