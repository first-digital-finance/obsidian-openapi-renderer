# OpenAPI Renderer by FDFC

Edit, preview and version OpenAPI specifications inside Obsidian, rendered with Swagger UI.

This is a fork of [**Ssentiago/obsidian-openapi-renderer**](https://github.com/Ssentiago/obsidian-openapi-renderer)
maintained by [First Digital Finance](https://github.com/first-digital-finance). The plugin is
[@Ssentiago](https://github.com/Ssentiago)'s work and all credit belongs to them; this fork exists
only to carry rendering fixes, and it tracks upstream otherwise.

---

## Why this fork exists

We write our API documentation in Obsidian vaults, so the Swagger preview is something the team
looks at every day. It had a class of bug that made it hard to read, and upstream has been quiet
since its 4.5.1 release in November 2024. Rather than wait, we fixed it here.

All of the problems share one root cause worth understanding, because it explains why they show up
for some people and not others:

> **The preview is not an iframe.** `render-controller.ts` injects Swagger UI's stylesheets as a
> `<style>` element *inside the Obsidian view*, so the entire Swagger tree lives in Obsidian's own
> document. Every unscoped colour rule in Obsidian's `app.css`, in your active theme, and in any CSS
> snippet you have enabled cascades straight into it — and Swagger UI's stylesheets, written for a
> standalone page, leak back out.

That is invisible as long as the preview's theme matches Obsidian's. The moment they differ — which
is the default, since the plugin ships `syncOpenAPIPreviewTheme: false` — Obsidian paints its
light-mode near-black text onto Swagger's dark backgrounds.

## What changed

Everything below is contained in `styles.css`. No source file is modified, which is deliberate:
rollup copies `styles.css` into `dist/` **verbatim** rather than bundling it into `main.js`, so
these fixes need no rebuild and stay trivial to audit and to offer upstream.

### Unreadable JSON in the preview (4.5.2)

Obsidian's `app.css` ships an unscoped Prism rule:

```css
code[class*="language-"], pre[class*="language-"] { color: var(--code-normal); }
```

Swagger UI renders code blocks as `<pre class="microlight" style="color:white"><code
class="language-json">`. Obsidian's rule matches that `<code>` **directly**, and a direct match beats
the white colour merely *inherited* from the `<pre>`. Every token the `agate` highlighter does not
colour inline — JSON keys and all bare punctuation `{ } : ,` — rendered dark grey on dark grey.

### Unreadable text wherever the preview's theme differs from Obsidian's (4.5.3)

Two independent groups of causes, both found by measurement rather than by reading selectors:

| what was wrong | where it came from |
| --- | --- |
| **Bold text** invisible | `app.css`: `b, strong { color: var(--bold-color) }`. Obsidian sets that variable to `inherit`, but **themes give it a real colour** — Blue Topaz and Things both do. |
| **Input values** invisible — server variables such as `Port` and `basePath` | `app.css` colours the whole `input[type=…]` family with `var(--text-normal)`. Server variables render as `<select>` when they declare an `enum` and `<input>` when they don't, so it hit the enum-less ones. |
| **Placeholders** invisible | same, via `var(--text-faint)` |
| **Headings** mistinted | themes colour `h1`–`h6` through their own `--h1..--h6-color` variables |
| **Inline code** purple on dark | Swagger's *own* `#9012fe`, which `swagger-ui-dark.css` never overrides |
| **Fenced code blocks** black on dark | Swagger's own `#000`, likewise never overridden |
| **POST / PUT / PATCH badges** white on pastel (~2:1) | Swagger's own `#fff` over `#49cc90` / `#fca130` / `#50e3c2` |
| **Version stamps**, **Execute button** | Swagger's own white-on-light-blue, 3.2:1 |

The Obsidian-side fixes are all `color: inherit`, so the preview follows whichever theme it is
actually displaying instead of hard-coding one. They are scoped through a doubled
`.swagger-ui.swagger-ui` selector, which sets up the precedence we want:

```
Swagger's deliberate colours  >  our neutralisers  >  Obsidian and theme colours
```

`!important` is used exactly once, for bold, and the reason is documented in `styles.css`: Blue Topaz
ships `:not(font)>strong { color: var(--accent-strong) !important }`, which no specificity can beat.
It is safe to force because neither Swagger stylesheet sets a colour on `b`/`strong` at all.

### Tooling

- **[`tools/obsidian-install-plugin.py`](tools/obsidian-install-plugin.py)** — installs this or any
  Obsidian plugin into every vault at once, discovered from Obsidian's own registry so nobody types
  a path. Python 3 standard library only.
- **[`tools/contrast-audit/`](tools/contrast-audit)** — the harness the fixes were verified with.

## How this was verified

Guessing at CSS selectors is how you end up with a `styles.css` full of speculative `!important`.
Instead, `tools/contrast-audit` renders the real Swagger UI in headless Chrome with the exact
stylesheet stack Obsidian produces — extracted `app.css`, the active theme, `styles.css`, then
Swagger's own CSS injected in the view, in Obsidian's real load order — against a specification that
deliberately exercises server variables, markdown in every description slot, all six parameter
kinds, every auth scheme and nested schemas. It then walks every visible text node and computes its
WCAG contrast ratio against the composited background.

Failing elements out of ~405 measured, including a **stock Swagger UI control** so that Swagger's
own shortcomings are not credited to Obsidian:

| combination | stock Swagger UI | before | after |
| --- | --- | --- | --- |
| Obsidian dark + preview dark | 11 | 11 | **2** |
| Obsidian light + preview dark | 11 | 16–42 | **2** |
| Obsidian dark + preview light | 61 | 92 | **56** |
| Obsidian light + preview light | 61 | 62 | **56** |

Every dark-preview combination now measures identically regardless of theme or Obsidian mode, which
was the actual goal: **the preview no longer depends on its host.** A before/after diff of every
element confirmed nothing that passed previously fails now.

## Known limitations

- **Two elements in a dark preview** — numeric literals in JSON examples, at 3.45:1.
  `react-syntax-highlighter` applies `agate` token colours as inline `style` attributes on unclassed
  `<span>`s, so no stylesheet can reach them without an `!important` broad enough to flatten every
  other token colour. Left alone deliberately.
- **56 in a light preview** — Swagger UI's own stock palette: muted `.prop-type` / `.property`
  greys, white-on-pastel GET and deprecated badges, the `#ff6060` Cancel button. Stock Swagger UI
  measures 61 in the same test, so this fork is marginally better than upstream Swagger rather than
  worse. Fixing them means restyling Swagger's light theme, which is a larger and more opinionated
  change than fixing leaks.
- **Opening a preview tints the whole Obsidian window.** Both Swagger theme files carry unscoped
  `html { background: … !important }` and `body { … }` rules. Those live in a bundled asset rather
  than in `styles.css`, so fixing them properly requires a rebuild.
- **Updating the bundled Swagger theme would not help.** We checked: the latest `swagger-themes`
  (1.4.3) differs from the bundled copy by exactly one selector, and the change *adds*
  `overflow-y: scroll` to that same unscoped `html` rule.

## Install

The plugin id is unchanged (`openapi-renderer`), so this installs as an in-place upgrade over the
community-store build and keeps your existing settings in `data.json`.

### One command, every vault

```sh
curl -fsSL https://raw.githubusercontent.com/first-digital-finance/obsidian-openapi-renderer/main/tools/obsidian-install-plugin.py \
  | python3 - first-digital-finance/obsidian-openapi-renderer --yes
```

Swap `--yes` for `--list` first to see what it would touch, or add `--only-upgrade` to skip vaults
that don't already have the plugin:

```
vault                                             installed   action
---------------------------------------------------------------------------
/Users/you/Notes                                      4.5.1   upgrade 4.5.1 -> 4.5.4
/Users/you/work/api-docs                                  -   fresh install 4.5.4
```

| flag | effect |
| --- | --- |
| `--list` | show vaults and versions, change nothing |
| `--dry-run` | print every file it would write |
| `--vault PATH` | target one vault; repeatable |
| `--only-upgrade` | skip vaults that don't already have the plugin |
| `--no-enable` | don't add the id to `community-plugins.json` |
| `-y`, `--yes` | no confirmation prompt (required when piped, since stdin is the script) |

It writes only `main.js`, `manifest.json` and `styles.css`, atomically, and never deletes the plugin
folder — so `data.json` survives every upgrade.

### BRAT, with a clickable link

Install [BRAT](https://github.com/TfTHacker/obsidian42-brat) once from the community store, then open:

```
obsidian://brat?plugin=first-digital-finance/obsidian-openapi-renderer
```

BRAT keeps everyone on the latest release automatically. This is the best option for teammates,
because the other two routes go stale silently.

### Manual

Download `main.js`, `manifest.json` and `styles.css` from the
[latest release](https://github.com/first-digital-finance/obsidian-openapi-renderer/releases/latest)
into `<vault>/.obsidian/plugins/openapi-renderer/`.

After any of these, reload the vault (`Cmd`/`Ctrl`-`R`) or toggle the plugin off and on.

## Relationship to upstream

This fork tracks [Ssentiago/obsidian-openapi-renderer](https://github.com/Ssentiago/obsidian-openapi-renderer)
and carries no feature changes — only the rendering fixes above, plus the two tools. The branch
`fix/json-preview-contrast` holds the first fix as a standalone commit against upstream, ready to
offer as a pull request.

Licensed Apache-2.0, as upstream is. If upstream picks these fixes up, this fork should stop
existing.

---

*Everything below this line is the original project documentation, by
[@Ssentiago](https://github.com/Ssentiago).*

## Why? 
I once wrote documentation for my small project directly in Obsidian while working on the 
database. Later, I needed to work with API documentation, so I started looking for suitable 
solutions among Obsidian plugins. Not finding any good options, I decided to create a plugin 
that allows writing Swagger UI documentation directly in Obsidian, without the need to switch 
between different applications. I hope I’ve managed to create something useful. If you have any 
suggestions for improvement, feel free to leave any issues here!


## Key features

- Edit and view OpenAPI specifications using Swagger UI
- Manage specification versions: create, view, restore, and delete
- Access all tracked OpenAPI specifications in your vault through a single user-friendly view 
  interface

## What this plugin can do?

**Note: You need to enable the `Detect all file extension` option in Settings -> Files and Links.**

By default, this plugin processes all files with `.yaml` or `.json` extensions as OpenAPI specifications. When you open any YAML or JSON file in Explorer, it will open in OpenAPI View and be treated as an OpenAPI specification. You can configure this behavior in plugin settings: OpenAPI View -> `Register YAML and JSON for processing by default?`.

The plugin has 4 main functions:
1. Edit specification files
2. Render them in Swagger UI
3. Version control
4. Overview of all specifications "registered" for versioning

Versioning and overview are optional features - you don't have to use them if you don't need them. The core functionality is editing and rendering.

### Edit and Preview

There are two ways to open the view for editing or previewing specifications:
1. Select a specification file in Explorer (works when `Register YAML and JSON for processing by default?` is enabled)
2. Right-click the file and select `Open in OpenAPI View`
3. Through other views (Version and Entry)

Both methods will open the OpenAPI View, which has two modes:
- Source mode: A CodeMirror-based editor for file editing
- Preview mode: Renders specification in Swagger UI, with $ref resolution support (this functionality hasn't been widely tested)

How it looks:

- Source mode:  
  ![source](https://github.com/user-attachments/assets/d6e74610-6df6-49f6-8f4c-e28df1f92329)
- Preview mode:  
  ![preview](https://github.com/user-attachments/assets/526a9347-353c-4e6f-b004-eb9455f0da70)

Available actions in the top actions bar:

- View:
    - Change mode (source / preview)
    - Open OpenAPI Version view for this file in the new tab
- Source mode:
    - Anchors (opens a modal with available anchors for this file)
    - Extensions (you can enable or disable some extensions for the source mode. This applies locally)
    - Format content
    - Convert between yaml / json
    - Change theme mode (dark / light)
- Preview mode:
    - Mode indicator (shows current rendering mode: "fast" when view is linked with another 
      OpenAPI View and \$ref resolving is disabled, or "full" in non-linked mode with \$ref 
      resolving enabled)
    - Rerender the preview
    - Change theme mode (dark / light)

### Versioning

You can access this mode in two ways:
1. Via action button in OpenAPI View
2. Via action button for the file in Entry View

This mode allows you to save and roll back to any version of your specifications. You can export versions as HTML and view differences between any two versions of a file.

The Version View interface is divided into two parts:
1. Draft version
2. Version list

How it looks:
![version](https://github.com/user-attachments/assets/523016f1-243d-4119-9f84-b3960c467c66)

Draft version is your current "raw" version from the file, not yet saved. You can save it to the Version list, preview it, and open it in OpenAPI View.

Version list shows your specification versions and groups your specification versions by time 
periods like "today", "yesterday", etc. 

Available actions for each version:
- Preview
- Restore to... (restores the file to selected version)
- Diff (compare two selected versions)
- Delete (soft delete - version won't be used in restore operations)
- Restore (recovers a soft-deleted version)
- Delete permanently (removes all data about selected version)
- Export (exports selected version as HTML file for sharing or browser viewing)

Top bar actions:
- View:
    - Export (exports all versions in one zip file as HTML)

### Overview

Access this view by clicking the "Open OpenAPI Entry View" button on the ribbon panel.

This view provides a convenient interface to manage all specifications registered for tracking.

How it looks:
![entry](https://github.com/user-attachments/assets/64db46f5-b631-422e-a53b-597de37fb1e0)


When you open the view, you'll see the "Home" page. Click the "Browse" button in the top navigation bar to see your files.


The browse page displays specification files as cards in a grid layout. Each card shows the last update time and number of registered versions for that file.

Available actions for each card (click the 'Plus' button to open):
- Open in OpenAPI View
- Open in Version View
- Export (all data as HTML files in a zip)
- Restore last file version (restores file in vault to last version, works even if file was 
  deleted from the vault)
- Remove file from tracking (removes all saved versions but keeps file in vault)

Top bar actions:
- View:
    - Export all files and their versions as a zip file

## Credits

Special thanks to [mnaoumov](https://github.com/mnaoumov/) for valuable insights and contributions, which greatly supported the development of this plugin.

## Reporting Issues

- **Rendering, contrast or theming problems** — these are most likely ours:
  [open an issue on this fork](https://github.com/first-digital-finance/obsidian-openapi-renderer/issues).
- **Anything about the plugin's actual features** — editing, versioning, the entry view, $ref
  resolution: [upstream](https://github.com/Ssentiago/obsidian-openapi-renderer/issues) is the right
  place, and a fix there benefits everyone rather than just us.

