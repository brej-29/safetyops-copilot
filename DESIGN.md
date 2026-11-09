---
name: "SafetyOps Copilot"
description: "A cool field journal for observations, review and next-shift follow-through."
colors:
  "blue": "#214fe0"
  "blue-deep": "#173db3"
  "paper": "#f6f8fc"
  "white": "#fff"
  "ink": "#18283c"
  "muted": "#53657b"
  "line": "#dbe2ee"
  "navy": "#142b4b"
  "ice": "#eaf0ff"
  "amber": "#f6bd4f"
  "green": "#13735a"
  "red": "#aa3346"
  "field-border": "#a9b8cd"
  "placeholder": "#627188"
  "chip-selected-border": "#a9bcff"
  "high-bg": "#fae5e9"
  "high-ink": "#9e2339"
  "medium-bg": "#fff0d0"
  "medium-ink": "#795305"
  "low-bg": "#e2f3ed"
  "low-ink": "#14644f"
  "danger-bg": "#f9e8eb"
  "rail-text": "#bdcce0"
  "rail-active": "#294362"
  "row-selected": "#f0f4ff"
  "workbench-bar": "#edf2fa"
  "output-bg": "#fbfcff"
  "error-bg": "#fff1f2"
  "error-ink": "#a52b3d"
  "proof-text": "#bfcee2"
  "proof-link": "#d2e0ff"
  "proof-line": "#3d506b"
  "proof-track": "#304661"
  "proof-fill": "#8da9ff"
  "selection": "#bfceff"
typography:
  display:
    fontFamily: "'Safety Sans', 'Segoe UI', sans-serif"
    fontSize: "clamp(44px, 6.3vw, 88px)"
    fontWeight: 650
    lineHeight: 1.12
    letterSpacing: "-.035em"
  headline:
    fontFamily: "'Safety Sans', 'Segoe UI', sans-serif"
    fontSize: "clamp(30px, 3.7vw, 48px)"
    fontWeight: 620
    lineHeight: 1.12
    letterSpacing: "-.035em"
  workspace-title:
    fontFamily: "'Safety Sans', 'Segoe UI', sans-serif"
    fontSize: "clamp(30px, 3vw, 42px)"
    fontWeight: 650
    lineHeight: 1.12
    letterSpacing: "-.035em"
  panel-title:
    fontFamily: "'Safety Sans', 'Segoe UI', sans-serif"
    fontSize: "18px"
    fontWeight: 620
    lineHeight: 1.12
    letterSpacing: "-.02em"
  body:
    fontFamily: "'Safety Sans', 'Segoe UI', sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
  working-copy:
    fontFamily: "'Safety Sans', 'Segoe UI', sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "'Safety Sans', 'Segoe UI', sans-serif"
    fontSize: "13px"
    fontWeight: 650
    lineHeight: 1.6
  metadata:
    fontFamily: "'Safety Sans', 'Segoe UI', sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.6
  score:
    fontFamily: "'Safety Sans', 'Segoe UI', sans-serif"
    fontSize: "44px"
    fontWeight: 650
    lineHeight: 1
    letterSpacing: "-.04em"
rounded:
  "status": "5px"
  "chip": "6px"
  "field": "7px"
  "control": "8px"
  "toast": "10px"
  "panel": "12px"
  "workbench": "14px"
spacing:
  "8": "8px"
  "12": "12px"
  "16": "16px"
  "20": "20px"
  "24": "24px"
  "32": "32px"
  "40": "40px"
  "48": "48px"
  "88": "88px"
components:
  button-primary:
    backgroundColor: "{colors.blue}"
    textColor: "{colors.white}"
    rounded: "{rounded.control}"
    padding: "12px 21px"
  button-primary-hover:
    backgroundColor: "{colors.blue-deep}"
  button-secondary:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "12px 21px"
  button-danger:
    backgroundColor: "{colors.danger-bg}"
    textColor: "{colors.red}"
    rounded: "{rounded.control}"
    padding: "12px 21px"
  button-text:
    backgroundColor: "transparent"
    textColor: "{colors.blue}"
    padding: "6px"
  input:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "11px 12px"
    width: "100%"
  chip:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.muted}"
    rounded: "{rounded.chip}"
    padding: "6px 10px"
  chip-selected:
    backgroundColor: "{colors.ice}"
    textColor: "{colors.blue}"
  pill:
    backgroundColor: "{colors.ice}"
    textColor: "{colors.blue}"
    rounded: "{rounded.status}"
    padding: "4px 8px"
  pill-high:
    backgroundColor: "{colors.high-bg}"
    textColor: "{colors.high-ink}"
  pill-medium:
    backgroundColor: "{colors.medium-bg}"
    textColor: "{colors.medium-ink}"
  pill-low:
    backgroundColor: "{colors.low-bg}"
    textColor: "{colors.low-ink}"
  panel:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
  rail-link:
    backgroundColor: "transparent"
    textColor: "{colors.rail-text}"
    rounded: "{rounded.field}"
    padding: "11px 14px"
  rail-link-active:
    backgroundColor: "{colors.rail-active}"
    textColor: "{colors.white}"
  observation-row:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    padding: "20px 24px"
    width: "100%"
  observation-row-selected:
    backgroundColor: "{colors.row-selected}"
---
# Design System: SafetyOps Copilot

## Overview

**Creative North Star: "The Cool Field Journal"**

The cool field journal makes safety follow-through feel steady, readable and owned. Cool paper supports dense working rows, deep navy frames navigation, and cobalt identifies the next action. Individual safety coordinators can scan observations, review a rationale and return to unfinished work without losing their place.

Humanist lettering softens a precise working interface. Thin rules, modest corners and restrained tonal fills separate records; broad whitespace belongs to the public introduction, while the workspace keeps the evidence, capture form and action queue close together. The signal illustration connects an observation to an owned action; it supplements content that is visible from the start.

**Key Characteristics:**
- Cool paper, deep ink and a cobalt action accent.
- Compact working rows with clear labels and tabular numerical evidence.
- Flat panels, thin separators and selective ambient depth.
- Visible keyboard focus and a static reduced-motion presentation.

## Colors

The palette reads as cool paper and deep blue ink, with concentrated cobalt actions and restrained semantic marks. Frontmatter values are normative; names below explain their use.

### Primary

- **Cobalt action / deep cobalt** (`blue`, `blue-deep`): primary controls, links, selected samples, progress segments and keyboard focus; the deeper shade marks primary hover.
- **Ice wash** (`ice`): sample-workspace notice, selected chips and neutral progress/status labels.

### Secondary

- **Review amber** (`amber`): the signal illustration's completed-action marker. Medium severity uses its dedicated light fill and darker readable ink, rather than the raw accent.
- **Resolution green / alert red** (`green`, `red`): semantic vocabulary. The visible low/high severity badges use the dedicated `low-*` and `high-*` pairs; overdue and destructive controls retain red meaning.

### Neutral

- **Cool paper / white** (`paper`, `white`): page canvas and working surfaces.
- **Deep ink / slate copy** (`ink`, `muted`): main text and secondary explanations.
- **Navy rail** (`navy`): workspace navigation and the public evaluation band; light text is separately tuned for those surfaces.
- **Journal rule** (`line`): panel outlines and row dividers; `field-border` gives inputs a stronger boundary.
- **Selected record wash** (`row-selected`): hover and selection in the observation register.
- **Assessment tones** (`workbench-bar`, `output-bg`): distinguish the public sample's header and output without introducing another dominant accent.
- **Semantic pairs** (`high-*`, `medium-*`, `low-*`, `error-*`): always apply foreground and background together. `danger-bg` pairs with `red`.

**The Action Ink Rule.** Use cobalt for actions, links, selection and focus. Reserve severity colors for labeled assessment and action states.

## Typography

**Display and body font:** self-hosted variable Manrope, exposed by CSS as `Safety Sans`, with Segoe UI and sans-serif fallbacks. The local WOFF2 is loaded with `font-display: swap` and supports weights (100?900). Keep the CSS alias: replacing it would bypass the shipped font declaration.

The same humanist family serves introduction and working UI. Headings use balanced wrapping, compact line-height and slightly negative tracking; records remain sentence case. There is no second display or monospace family.

### Hierarchy

- **Display:** the fluid public h1 role in frontmatter. At widths at or below (900px) the hero uses (64px), then (52px) at or below (700px).
- **Headline:** fluid public section headings. Article headings use an explicit smaller scale: h1 (clamp(38px, 5vw, 60px)), h2 (28px); mobile article h1 is (42px).
- **Workspace title:** fluid working-page h1, becoming (30px) on mobile.
- **Panel title:** compact h2 at the top of working panels. General h3 uses (22px), weight (650); action-row titles use (14px), weight (650), line-height (1.5), with normal tracking.
- **Body and working copy:** the body uses the frontmatter base; working descriptions and record titles use the smaller working-copy size. Public introductory copy is (18px), becoming (16px) on mobile, with a desktop line measure of (48ch).
- **Label and small copy:** explicit field labels are weight (650); helper copy and metadata use the small sizes. Record date/location metadata can drop to (11px).
- **Score:** the sample score is large and compact; priority values, summary counts and evaluation metrics use tabular numerals. Summary counts are (30px), becoming (26px) on mobile.

**The Reviewable Number Rule.** Keep priority and evaluation numbers tabular and beside their labels, explanations and limits.

## Layout

The public container is centered with a maximum outer width of (1280px) and side padding of (48px). Its main hero grid is (1.2fr 1fr), the sample assessment is (1.1fr 1fr), and the workflow strip has four equal cells. Public sections generally use vertical padding (88px); the journal section preserves the same container gutters. Articles use a narrower maximum width (780px).

The workspace begins with a (220px) navy rail and a flexible main area. Main padding is (28px 40px 50px). Four summary cells sit above a two-column grid of (minmax(0, 1.65fr) minmax(280px, 1fr)) with a (26px) gap. Working panels use (24px) body padding; row boundaries carry the density instead of gaps between individual cards.

Observed breakpoints, including their cascade:

- **At or above (1700px):** main workspace width caps at (1550px) and centers.
- **At or below (1150px):** public gutters become (30px), the rail becomes (190px), main padding becomes (25px), and the workspace detail column is (300px).
- **At or below (900px):** the hero becomes one column and hides the signal artwork. The rail becomes a horizontal top navigation, hides its bottom note and icons, and the working grid keeps a (320px) right column. The brand's final override uses (18px).
- **At or below (700px):** public gutters become (22px), navigation height becomes (72px), public sections use (55px), and sample/evaluation/journal grids stack. The workflow and summary strips become two-by-two. Workspace padding becomes (20px 16px); navigation wraps to a full-width row. The working content becomes a column in the visual order **capture ? observation register ? assessment detail ? next actions**. Fields and action controls stack; panel padding becomes (20px).

The spacing frontmatter captures recurring steps rather than proposing a mathematical scale. Preserve the existing contextual measurements for compact rows, controls and large public sections.

## Elevation & Depth

Working panels are flat white paper bounded by thin rules. Dark navigation, ice notices and lightly tinted selected records provide most depth. The sample assessment receives one broad ambient shadow and transient notifications receive a smaller structural shadow.

### Shadow Vocabulary

- **Sample workbench:** `0 24px 55px -35px #19345555`.
- **Toast:** `0 8px 24px #142b4b30`.

**The Quiet Surface Rule.** Keep workspace panels flat. Use borders and tonal fills to organize the work; reserve ambient shadows for the public assessment workbench and toast.

Motion is calm and supplemental. Buttons transition background and transform over (.2s); public reveal surfaces transition transform and shadow over (.8s) with `cubic-bezier(.16,1,.3,1)`, moving only (-3px) when in view. The signal illustration rotates over (65s), moves a dot over (9s) and advances dashed lines over (18s), all linearly. Contents are visible before these effects. Under `prefers-reduced-motion: reduce`, smooth scrolling, animation and transitions are disabled and reveal translation is removed. JavaScript scroll paths also honor the preference. The shared button hover translation remains an instantaneous (-1px) position change because the reduced-motion CSS suppresses its transition, not its transform. Keep the static signal-to-action meaning intact.

## Shapes

Use softly squared geometry rather than capsules. The frontmatter names the exact corners by component: status badge, chip, field, control, toast, panel and sample workbench. Panels clip their row fills inside the rounded frame; inner rows remain rectangular. Thin solid borders provide the primary edge language. Circular geometry belongs to small markers, step numbers and the signature signal illustration.

## Components

### Buttons

Confident, compact actions with sentence-case labels. Primary uses cobalt and white, weight (650), line-height (1.5), a (12px) gap and a transparent one-pixel border. Hover darkens cobalt and shifts up (-1px). Secondary uses white, ink and a journal-rule border; its source-specific fill and border remain on hover while the shared translation applies. Destructive actions use the danger tint and red text. The small variant uses padding (8px 13px) and type (14px); text actions use underlined cobalt with padding (6px). Disabled buttons reduce opacity to (.55) and use a wait cursor.

Keyboard focus uses a cobalt outline (3px) and offset (5px). Observation selection and interface rerenders preserve the active keyboard control. Preserve that behavior when extending row interactions; do not rely on a hover fill as the focus indicator.

### Chips and status badges

Sample chips are actual pressed-state controls: paper, slate and a thin rule at rest; ice and cobalt with the dedicated selected border when `aria-pressed="true"`. Status badges are compact rectangles, not interactive filters: ice/cobalt for workflow, dedicated high/medium/low foreground-background pairs for severity. Keep the text label visible with the color.

### Cards / Containers

Workspace panels use the panel radius, one-pixel journal-rule border, white background and clipped overflow. Headers use padding (20px 24px) with a lower rule and body padding (24px); mobile uses (17px 20px) and (20px), respectively. The public sample has the larger workbench radius, ambient shadow, tinted header and two input/output zones. Summary counts are one joined four-cell strip, becoming two-by-two on mobile.

### Inputs / Fields

White fields use ink text, the stronger field border, padding (11px 12px), field radius and cobalt caret. Focus shifts the border to cobalt and retains the visible outline. Placeholders use the separate placeholder color; explicit labels remain above the input. Textareas resize vertically and use line-height (1.5); base minimum height is (120px), working capture is (150px), becoming (110px) on mobile. Error messages use the dedicated error pair, padding (12px), control radius and (14px) text; empty errors are hidden.

### Navigation

Public navigation sticks above the content on paper with a thin bottom rule, and uses muted text links plus a cobalt action. On mobile the secondary links are hidden and the principal action remains. Workspace navigation is navy with light slate links; active and hovered links share the lighter navy fill and white text. Links use field-radius corners. The desktop brand has a final (16px) override with a (30px) mark, becoming (18px) at or below the (900px) breakpoint. Do not let a prior larger brand rule override this cascade.

### Observation register and action queue

The register is one divided panel, not detached cards. Full-width row buttons use (20px 24px) padding, change to the selected wash on hover or selection, show a labeled severity badge, date and location, and clamp titles to two lines. Mobile rows use (18px 20px). Next-action rows retain the same boundaries and put owner, due date and state near their controls. Assessment detail keeps explanation, score, runbook and the next-action form in one readable column.

### Signature signal and notification

The public signal artwork is a continuous observation-to-action path with a central safety mark and an amber endpoint. It is hidden at narrower widths rather than crowding the reading task. Its reduced-motion form is static. The toast is navy with white text, padding (15px 22px), toast-radius corners, a maximum width of (min(420px, 90vw)) and a fixed lower-right position. It disappears when empty.

## Do's and Don'ts

### Do:
- Do use the CSS custom properties as the source of truth and preserve the Safety Sans variable font.
- Do pair every severity or action color with a readable state label.
- Do preserve visible keyboard focus, explicit field labels and content that is visible before animation.
- Do keep capture, register, assessment detail and next actions in that mobile reading order.
- Do show scores with their rationale and human-review context.

### Don't:
- Don't turn semantic amber, green or red into general decorative accents.
- Don't add heavy shadows to working panels or replace the cool paper with a dark workspace canvas.
- Don't use motion as the only way to reveal content or communicate a state.
- Don't invent a second font family, a new breakpoint system or fully rounded pill controls.


<!-- Captured from apps/web/styles.css, PRODUCT.md, .impeccable/workspace-brief.md and desktop/mobile review renders. Refresh this record and the sidecar together after visual changes. -->
