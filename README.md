# OpenAPI Renderer Plugin for Obsidian

> **Fork note.** This is a fork of
> [Ssentiago/obsidian-openapi-renderer](https://github.com/Ssentiago/obsidian-openapi-renderer)
> maintained by [@sharavara](https://github.com/sharavara). It exists to carry one fix that is
> not yet in upstream 4.5.1:
>
> - **JSON in the Swagger preview is unreadable (dark grey on dark grey).** Obsidian's core
>   `app.css` ships an unscoped Prism rule, `code[class*="language-"] { color: var(--code-normal) }`,
>   that matches Swagger UI's `<code class="language-json">` directly and overrides the white
>   colour those code blocks inherit from their `<pre class="microlight">`. The result: JSON keys
>   and all bare punctuation (`{ } : ,`) render at roughly `rgb(92,92,92)` on `#333`. Fixed with
>   two scoped rules in `styles.css` (see the comment there for the full diagnosis).
> - **Text is unreadable wherever the preview's theme differs from Obsidian's.** The preview is
>   not an iframe, so `app.css`, the active theme and any CSS snippet all cascade into the Swagger
>   tree. Obsidian in light mode with a dark preview paints near-black onto dark backgrounds:
>   bold text, `<input>` values (server variables such as `Port` and `basePath`), placeholders and
>   headings. A handful of Swagger's own light-theme colours that `swagger-ui-dark.css` never
>   overrides are fixed too - `#9012fe` inline code, `#000` code blocks, white-on-pastel method
>   badges, the version stamps and the Execute button. Verified with a headless-Chromium contrast
>   harness across eight theme/mode combinations; see [`tools/contrast-audit`](tools/contrast-audit).
>
> Everything else is unchanged from upstream. All credit for the plugin goes to
> [@Ssentiago](https://github.com/Ssentiago); it is Apache-2.0 licensed.

## Installing this fork

Three ways, pick per person.

### 1. One command, every vault (no extra plugin)

`tools/obsidian-install-plugin.py` finds your vaults in Obsidian's own registry, so nobody
has to type paths. Python 3.9+, standard library only.

```sh
curl -fsSL https://raw.githubusercontent.com/sharavara/obsidian-openapi-renderer/main/tools/obsidian-install-plugin.py \
  | python3 - sharavara/obsidian-openapi-renderer --yes
```

Look before you leap - drop `--yes` for `--list` to see what it would touch:

```sh
curl -fsSL .../obsidian-install-plugin.py | python3 - sharavara/obsidian-openapi-renderer --list
```

```
vault                                             installed   action
---------------------------------------------------------------------------
/Users/you/Notes                                      4.5.1   upgrade 4.5.1 -> 4.5.2
/Users/you/work/api-docs                                  -   fresh install 4.5.2
```

Useful flags:

| flag | effect |
|---|---|
| `--list` | show vaults and installed versions, change nothing (fetches only `manifest.json`) |
| `--dry-run` | print every file it would write |
| `--vault PATH` | target one vault; repeatable |
| `--only-upgrade` | skip vaults that don't already have the plugin |
| `--no-enable` | don't add the id to `community-plugins.json` |
| `-y`, `--yes` | no confirmation prompt (required when piped, since stdin is the script) |

It works for **any** Obsidian plugin, not just this one, and takes any of:

```sh
obsidian-install-plugin.py owner/repo              # latest release
obsidian-install-plugin.py owner/repo@4.5.2        # a specific tag
obsidian-install-plugin.py https://host/thing.zip  # zip URL
obsidian-install-plugin.py ./thing.zip             # local zip
obsidian-install-plugin.py ./build-dir             # local directory
```

Your settings are safe: it writes only `main.js`, `manifest.json` and `styles.css`, atomically,
and never deletes the plugin folder - so `data.json` survives every upgrade.

### 2. BRAT, with a clickable link

Install [BRAT](https://github.com/TfTHacker/obsidian42-brat) once from the community store, then
open this link in a browser - it hands the repo straight to BRAT's "Add beta plugin" dialog:

```
obsidian://brat?plugin=sharavara/obsidian-openapi-renderer
```

BRAT then keeps everyone on the latest release automatically. Best option if the fork will
keep receiving fixes.

### 3. Manual

Download `main.js`, `manifest.json` and `styles.css` from the
[latest release](https://github.com/sharavara/obsidian-openapi-renderer/releases/latest)
into `<vault>/.obsidian/plugins/openapi-renderer/`, then reload Obsidian.

After any of these: reload the vault (`Cmd`/`Ctrl`-`R`), or toggle the plugin off and on under
**Settings -> Community plugins**.


Integrate OpenAPI specification management into Obsidian with features for version control,
visualization, editing, and easy navigation of API specs.

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

## Installation

1. Manual:
    1. Download the last release assets and copy them into your `.
    obsidian/plugins/openapi-renderer` 
       directory
       (create it if it doesn’t exist)
    2. Enable the plugin in Obsidian settings (Settings → Community plugins).
2. Via the Community plugins Browser:
    1. Go to `Settings` -> `Community plugins`, click on `Browse` button and search for 
       `OpenAPI Renderer`. Install it
    2. Enable the plugin in Obsidian settings (Settings → Community plugins).

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

If you encounter any bugs or unexpected behavior, please [open an issue on GitHub](https://github.com/ssentiago/openapi-renderer/issues). If you want to offer a new feature, feel free to suggest.

Your involvement makes the plugin better for everyone.

