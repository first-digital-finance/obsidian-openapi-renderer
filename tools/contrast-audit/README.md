# Preview contrast audit

Renders the real Swagger UI in headless Chrome with the exact CSS stack Obsidian
produces, walks every visible text node, and reports WCAG contrast for each one.
This is how the `styles.css` preview fixes were found and verified, rather than
by eyeballing selectors.

Why it is needed: the preview is not an iframe. `render-controller.ts` injects
Swagger's CSS as a `<style>` inside the view, so Obsidian's `app.css`, the active
theme and any CSS snippet all cascade into the Swagger tree. Whether that is
visible depends on whether the preview's theme matches Obsidian's - which is why
the bugs only appear in some combinations.

## Staging

The harness needs files this repo does not ship. From the repo root:

```sh
cd tools/contrast-audit
cp ../../src/assets/swagger-ui/swagger-ui-{base,dark,light}.css .
cp ../../src/assets/swagger-ui/swagger-ui-bundle.js .
cp ../../styles.css plugin-styles.css

# Obsidian's core stylesheet lives inside obsidian.asar, not on disk.
# Extract /app.css from it (parse the asar header: bytes 12-15 are the JSON
# header length as a LE uint32; payloads start at 16 + jsonLen) and save it
# here as app.css.

# optional, to reproduce a specific user's setup
cp "$VAULT/.obsidian/themes/<Theme>/theme.css" theme-<name>.css
```

## Running

`audit.html` has two placeholders: `__MODE__` is the preview theme
(`dark`/`light`) and `__BODYCLASS__` is Obsidian's mode (`theme-dark`/
`theme-light`). Generate the combination you want, then measure it:

```sh
sed -e 's/__MODE__/dark/' -e 's/__BODYCLASS__/theme-light/' \
    -e 's|<!--THEME-->|<link rel="stylesheet" href="theme-bluetopaz.css">|' \
    audit.html > case.html
python3 one.py case.html case.json
```

`one.py` prints `measured=N failing=N worst=RATIO` and writes the full per-element
rows to the JSON file. A useful control is a page with `app.css`, the theme and
`plugin-styles.css` links deleted: that measures stock Swagger UI, so you can tell
Swagger's own contrast problems apart from Obsidian pollution.

## Reference numbers

Measured against the bundled swagger-ui-dist 5.x and Obsidian 1.x app.css, with
the spec in `spec.json` (which deliberately exercises server variables, markdown
in every description slot, all parameter kinds, every auth scheme and nested
schemas):

| combination                     | stock Swagger | before the fix | after |
| ------------------------------- | ------------- | -------------- | ----- |
| Obsidian dark  + preview dark   | 11            | 11             | 2     |
| Obsidian light + preview dark   | 11            | 16-42          | 2     |
| Obsidian dark  + preview light  | 61            | 92             | 56    |
| Obsidian light + preview light  | 61            | 62             | 56    |

The two that remain in a dark preview are numeric literals in JSON example
blocks. `react-syntax-highlighter` applies the `agate` token colours as inline
`style` attributes on unclassed `<span>`s, so no stylesheet can reach them
without an `!important` broad enough to flatten every other token colour too.

The 56 in a light preview are Swagger UI's own stock palette - muted greys such
as `.prop-type` and `.property`, white-on-pastel method badges, and the
`#ff6060` Cancel button. They are present in every Swagger UI deployment and are
not caused by Obsidian; fixing them means restyling Swagger's light theme.
