# Naming Rubric

Image Namer follows a consistent naming rubric to generate descriptive, searchable filenames.

## Rubric Rules

### 1. Word Count: 5-8 Words

Filenames should contain **5 to 8 short words** for optimal balance between specificity and readability.

**Good**:
- `golden-retriever-puppy--running-in-park.jpg` (6 words)
- `sales-chart--q4-2024-revenue-comparison.png` (5 words)
- `mountain-landscape--sunset-over-alpine-lake.webp` (6 words)

**Too short**:
- `dog-park.jpg` (2 words - not descriptive enough)

**Too long**:
- `golden-retriever-puppy-running-in-park-with-tennis-ball-during-sunset.jpg` (11 words - too verbose)

### 2. Format: Lowercase with Hyphens

- **All lowercase letters**
- **Words separated by hyphens** (`-`)
- **Double hyphen** (`--`) separates primary subject from details

**Good**:
- `web-app-dashboard--sales-metrics.png`
- `architecture-diagram--microservices-overview.png`

**Bad**:
- `Web_App_Dashboard.png` (underscores, capitals)
- `webappdashboard.png` (no separators)
- `Web-App-Dashboard.png` (capitals)

### 3. Structure: `<primary-subject>--<specific-detail>`

Use a **double hyphen** (`--`) to separate the primary subject from specific details:

```
<primary-subject>--<specific-detail>.<extension>
```

**Examples**:

| Primary Subject | Specific Detail | Full Name |
|----------------|-----------------|-----------|
| `golden-retriever` | `running-in-park` | `golden-retriever--running-in-park.jpg` |
| `sales-chart` | `q4-2024-revenue` | `sales-chart--q4-2024-revenue.png` |
| `web-dashboard` | `user-analytics-metrics` | `web-dashboard--user-analytics-metrics.png` |
| `mountain-landscape` | `sunset-over-alpine-lake` | `mountain-landscape--sunset-over-alpine-lake.webp` |

### 4. Maximum Length: 80 Characters

Keep the full filename (stem + extension) under **80 characters** for compatibility with various systems and readability.

**Good**:
- `architecture-diagram--microservices-api-gateway.png` (52 chars)

**Too long**:
- `architecture-diagram-for-our-company-microservices-based-system-with-api-gateway-and-load-balancer.png` (105 chars)

### 5. Helpful Discriminators

Include specific details that make the image searchable and distinguishable:

#### Chart Types
- `sales-chart--bar-graph-q4-revenue.png`
- `performance-chart--line-graph-cpu-usage.png`
- `org-chart--company-hierarchy-2024.png`

#### Versions
- `logo--version-3-blue.png`
- `mockup--homepage-redesign-v2.png`

#### Colors
- `icon-set--blue-gradient-theme.png`
- `background-pattern--dark-mode-variant.png`

#### Angles/Views
- `car-photo--front-view-quarter-angle.jpg`
- `building--aerial-top-down-view.jpg`

#### Time/Date
- `screenshot--login-page-2024-11-02.png`
- `report--annual-results-2024.pdf`

#### Location
- `landscape--yosemite-half-dome.jpg`
- `restaurant-photo--tokyo-ramen-shop.jpg`

### 6. No Sensitive Information

**Do NOT include**:
- Personal information (names, addresses)
- Confidential data (passwords, API keys)
- Internal identifiers that shouldn't be public

**Bad**:
- `john-smith-driver-license.jpg`
- `api-key-sk-proj-abc123.png`
- `internal-project-codename-phoenix.png`

**Good**:
- `driver-license-example--blank-template.jpg`
- `api-key-screenshot--masked-example.png`
- `project-diagram--system-architecture.png`

## Rubric Version

Current rubric version: **v1**

The rubric version is embedded in cache keys. If the rubric rules change significantly, the version is bumped, invalidating old cache entries.

## Examples by Category

### Screenshots

| Original | Renamed |
|----------|---------|
| `screenshot-2024-11-02.png` | `web-app-login--username-password-form.png` |
| `Screen Shot 2024-11-02.png` | `mobile-app-dashboard--ios-metrics-view.png` |
| `IMG_2345.png` | `settings-panel--dark-mode-preferences.png` |

### Photos

| Original | Renamed |
|----------|---------|
| `DSC_0123.jpg` | `golden-retriever-puppy--running-in-park.jpg` |
| `vacation-photo.jpg` | `mountain-landscape--sunset-over-alpine-lake.jpg` |
| `photo-1.jpg` | `family-portrait--outdoor-park-setting.jpg` |

### Diagrams

| Original | Renamed |
|----------|---------|
| `diagram.png` | `architecture-diagram--microservices-api-gateway.png` |
| `flowchart.png` | `user-flow--registration-process-steps.png` |
| `system-design.png` | `database-schema--entity-relationships.png` |

### Charts and Graphs

| Original | Renamed |
|----------|---------|
| `chart.png` | `sales-chart--bar-graph-quarterly-revenue.png` |
| `graph.png` | `performance-graph--line-chart-cpu-usage.png` |
| `data-viz.png` | `user-growth--area-chart-monthly-signups.png` |

### UI/UX

| Original | Renamed |
|----------|---------|
| `mockup.png` | `homepage-mockup--hero-section-redesign.png` |
| `wireframe.png` | `checkout-flow--mobile-payment-screen.png` |
| `design.png` | `dashboard-design--dark-theme-variant.png` |

## Idempotency

If a filename **already follows the rubric**, Image Namer keeps it unchanged.

### Assessment Process

Before generating a new name, Image Namer **assesses** if the current filename is suitable:

1. **Check structure**: Does it follow `<subject>--<detail>` pattern?
2. **Check length**: Is it under 80 characters?
3. **Check format**: Is it lowercase with hyphens?
4. **Check word count**: Does it have 5-8 words?

If all checks pass, the file is marked as "already suitable" and skipped.

### Example

```bash
$ image-namer file golden-retriever--running-in-park.jpg
File already has a suitable name. No rename needed.
```

This prevents unnecessary churn and API calls.

## Rubric Prompt

Image Namer uses this prompt with AI vision models:

```
You are an expert at naming image files for clarity and organization.
Follow this strict rubric to propose a filename for the provided image:
- Compose 5–8 short words.
- Lowercase letters only; separate words with hyphens.
- Maximum total length: 80 characters.
- Prefer structure: <primary-subject>--<specific-detail>.
- Use helpful discriminators when applicable (e.g., chart-type, version, color, angle, year).
- If the current filename already follows this rubric, keep the same stem.
Return only the stem and extension components for the filename.
```

This ensures consistent results across providers and models.

## Best Practices

### ✅ Do

- Be specific (e.g., `web-dashboard--sales-metrics` not `dashboard`)
- Include discriminators (e.g., `chart--bar-graph` not just `chart`)
- Use the double hyphen (`--`) to separate subject and details
- Keep it concise (5-8 words)

### ❌ Don't

- Use generic names (e.g., `image.png`, `photo.jpg`)
- Include dates in the format `YYYYMMDD` (hard to read)
- Use underscores or capitals (breaks convention)
- Exceed 80 characters

## Customization

!!! note "Rubric is Fixed"
    The rubric is **not customizable** by design. Consistency across all renamed files is more valuable than individual preferences.

If you need different naming conventions, you can:
1. Fork Image Namer and modify `RUBRIC_PROMPT` in `src/operations/generate_name.py`
2. Bump `RUBRIC_VERSION` in `src/constants.py` to invalidate old cache

## Next Steps

- [CLI Commands](cli-commands.md) - Apply the rubric to your images
- [Cache Structure](cache-structure.md) - How rubric version affects caching
- [Configuration](configuration.md) - Provider and model settings
