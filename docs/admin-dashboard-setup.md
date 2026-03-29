# Admin Dashboard Setup

This document covers the production setup for the static analytics dashboard under `docs/admin/`.

Related files:

- `docs/admin/index.html`
- `scripts/build_admin_analytics.py`
- `.github/workflows/admin-dashboard.yml`
- `docs/admin-dashboard-design.md`

## 1. First-Time GA4 Setup

If you have never used GA4 before, follow this order.

### 1.1 Create the GA4 property and web data stream

1. Open Google Analytics and create a new GA4 property for this site.
2. Use a clear property name such as `agri-news-brief`.
3. Set the reporting time zone to `South Korea` / `Asia/Seoul`.
4. Create one `Web` data stream for the public site:
   - `https://nh-horti.github.io/agri-news-brief/`
5. Keep the generated web stream open and copy the `Measurement ID`.

For this repo:

- `GA4_MEASUREMENT_ID` = the web stream Measurement ID
- Format example: `G-ABCDEFG123`
- Purpose: inject the front-end tracking tag into generated pages

### 1.2 Understand the two IDs you need

- `GA4_MEASUREMENT_ID`
  - starts with `G-`
  - belongs to the web data stream
  - used by the public site pages
- `GA4_PROPERTY_ID`
  - numeric only
  - belongs to the GA4 property
  - used by the scheduled export job and Data API

Do not swap them. The dashboard needs both.

### 1.3 Enable API export access

For the admin dashboard export job:

1. Create or select a Google Cloud project.
2. Enable the `Google Analytics Data API`.
3. Create a service account for the export job.
4. Create a JSON key for that service account.
5. In GA4 property access management, add the service account email as a property user.

Operational recommendation:

- start with property-level `Viewer` access for the service account
- if your organization uses stricter reporting permissions and export fails, raise it to `Analyst`
- if you want to auto-register custom dimensions with the Admin API, temporarily raise the service account to `Editor` or `Administrator`

The repo currently expects this JSON in GitHub Actions as `GA4_SERVICE_ACCOUNT_JSON`.

For local development, the recommended setup is different:

- save the downloaded service-account JSON file under `.secrets/ga4-service-account.json`
- set `GA4_SERVICE_ACCOUNT_FILE=.secrets/ga4-service-account.json` in `.env.final.local`
- `.secrets/` is ignored by git, so the raw key file does not get committed by accident

If you want to auto-register custom dimensions:

- also enable the `Google Analytics Admin API`
- the export dashboard script uses the Data API
- the custom-dimension registration script uses the Admin API

### 1.4 Register custom dimensions

Register the event-scoped custom dimensions listed in section 3 before expecting full dashboard data.

You can do this either:

- manually in `Admin > Custom definitions > Create custom dimensions`
- automatically with `scripts/register_ga4_custom_dimensions.py`

Important:

- this project currently needs 21 event-scoped dimensions
- standard GA4 properties support up to 50 event-scoped custom dimensions
- new custom dimensions can take 24-48 hours before data appears in standard reporting surfaces

### 1.5 First validation flow

1. Add the GitHub secrets from section 2.
2. Run `.github/workflows/secrets-check.yml` with `check_ga4=true`.
3. Run `.github/workflows/rebuild.yml` once so production HTML is rebuilt with the GA tag.
4. Open the public site and click a few articles and search results.
5. Check Realtime / DebugView in GA4.
6. Run `.github/workflows/admin-dashboard.yml`.
7. Open `/admin/` and confirm JSON-backed cards and tables render.

## 2. Required GitHub Secrets

Add these repository secrets before enabling the dashboard in production:

- `GA4_MEASUREMENT_ID`
  - Used by `daily.yml`, `rebuild.yml`, `maintenance.yml`, and `ux_patch.yml`
  - Injects the front-end tracking tag into generated pages
- `GA4_PROPERTY_ID`
  - Used by `admin-dashboard.yml` and `secrets-check.yml`
  - GA4 property ID for Data API export
- `GA4_SERVICE_ACCOUNT_JSON`
  - Recommended for scheduled exports
  - Full JSON payload for a service account with `analytics.readonly`
- `GA4_ACCESS_TOKEN`
  - Optional alternative to the service account secret
  - Use only if you already rotate short-lived tokens externally

Only one of `GA4_SERVICE_ACCOUNT_JSON` or `GA4_ACCESS_TOKEN` is required.

## 3. GA4 Custom Dimensions

Register these event-scoped custom dimensions in GA4 before expecting full dashboard data:

- `page_type`
- `report_date`
- `view_mode`
- `build_id`
- `article_id`
- `article_title`
- `section`
- `surface`
- `target_domain`
- `article_rank`
- `query`
- `query_length`
- `result_count`
- `section_filter`
- `sort_mode`
- `group_mode`
- `from_view`
- `to_view`
- `nav_type`
- `from_date`
- `to_date`

The dashboard will still render without them, but the export job will return warnings and sparse data.

Automatic registration:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run-local-register-ga4-custom-dimensions.ps1 -DryRun
powershell -ExecutionPolicy Bypass -File scripts/run-local-register-ga4-custom-dimensions.ps1 -PropertyId 529705878 -DryRun
powershell -ExecutionPolicy Bypass -File scripts/run-local-register-ga4-custom-dimensions.ps1
```

Notes:

- the auto-registration script creates only missing dimensions
- it uses the Google Analytics Admin API, not the Data API export path
- the service account must have edit-level property access while the script runs
- after registration is complete, you can lower the service account back to `Viewer` or `Analyst` for normal export jobs

Recommended local env example:

```dotenv
GA4_MEASUREMENT_ID=G-M5Y1GRYB0J
GA4_PROPERTY_ID=529705878
GA4_SERVICE_ACCOUNT_FILE=.secrets/ga4-service-account.json
```

If you really need to inline the JSON instead of using a file path:

- use `GA4_SERVICE_ACCOUNT_JSON`
- keep the entire JSON on one line
- do not paste multi-line JSON directly into `.env.final.local`

Suggested display names:

- `page_type` -> `Page type`
- `report_date` -> `Report date`
- `view_mode` -> `View mode`
- `build_id` -> `Build ID`
- `article_id` -> `Article ID`
- `article_title` -> `Article title`
- `section` -> `Section`
- `surface` -> `Surface`
- `target_domain` -> `Target domain`
- `article_rank` -> `Article rank`
- `query` -> `Search query`
- `query_length` -> `Query length`
- `result_count` -> `Result count`
- `section_filter` -> `Section filter`
- `sort_mode` -> `Sort mode`
- `group_mode` -> `Group mode`
- `from_view` -> `From view`
- `to_view` -> `To view`
- `nav_type` -> `Navigation type`
- `from_date` -> `From date`
- `to_date` -> `To date`

## 4. Workflow Wiring

Production page generation now injects `GA4_MEASUREMENT_ID` in:

- `.github/workflows/daily.yml`
- `.github/workflows/rebuild.yml`
- `.github/workflows/maintenance.yml`
- `.github/workflows/ux_patch.yml`

The dashboard export runs in:

- `.github/workflows/admin-dashboard.yml`

Manual validation is available in:

- `.github/workflows/secrets-check.yml`

## 5. Local Validation

Build the admin JSON locally:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run-local-admin-dashboard.ps1 -Strict
```

Behavior:

- prefers `.env.final.local`, then `.env.local`
- reads `GA4_*` values from `AGRI_ENV_FILE`
- writes JSON files under `.local-builds/admin-dashboard/`
- returns non-zero when configuration or API warnings are present if `-Strict` is used

## 6. Deployment Checklist

1. Add the GA4 secrets listed above.
2. Register the custom dimensions in GA4.
3. Run `secrets-check.yml` with `check_ga4=true`.
4. Run `admin-dashboard.yml` manually once and confirm `docs/admin/data/*.json` updates.
5. Verify the published dashboard at `/admin/` and the public brief pages include the GA tag.

## 7. Common Mistakes

- Using `GA4_MEASUREMENT_ID` where `GA4_PROPERTY_ID` is required
- Creating the service account in Google Cloud but not adding that email to GA4 property access management
- Expecting custom-dimension-based reports to populate immediately after registration
- Forgetting to rerun `rebuild.yml` after adding `GA4_MEASUREMENT_ID`
- Testing only on `/dev/`
  - current production analytics wiring is intentionally attached to the production build workflows

## 8. Official References

- Google Analytics setup for a website/app: <https://support.google.com/analytics/answer/14183469>
- Create and manage data streams: <https://support.google.com/analytics/answer/9303323>
- Find Google tag IDs / stream details: <https://support.google.com/analytics/answer/12326985>
- GA4 events with `gtag.js`: <https://developers.google.com/analytics/devguides/collection/ga4/events>
- Custom dimensions and metrics: <https://support.google.com/analytics/answer/14239696>
- GA4 DebugView: <https://support.google.com/analytics/answer/7201382>
- User roles and permissions: <https://support.google.com/analytics/answer/9305587>
- Google Analytics Data API basics: <https://developers.google.com/analytics/devguides/reporting/data/v1/basics>
- Data API Python quickstart: <https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart-client-libraries>
- Google Analytics Admin API overview: <https://developers.google.com/analytics/devguides/config/admin/v1>
- Create custom dimensions via Admin API: <https://developers.google.com/analytics/devguides/config/admin/v1/rest/v1alpha/properties.customDimensions/create>
- Create and manage service accounts: <https://cloud.google.com/iam/docs/creating-managing-service-accounts>
