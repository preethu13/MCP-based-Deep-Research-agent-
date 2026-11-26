---
name: Obsidian Deep Research
colors:
  surface: '#131317'
  surface-dim: '#131317'
  surface-bright: '#39393e'
  surface-container-lowest: '#0e0e12'
  surface-container-low: '#1b1b20'
  surface-container: '#1f1f24'
  surface-container-high: '#2a292e'
  surface-container-highest: '#353439'
  on-surface: '#e4e1e8'
  on-surface-variant: '#c7c4d7'
  inverse-surface: '#e4e1e8'
  inverse-on-surface: '#303035'
  outline: '#908fa0'
  outline-variant: '#464554'
  surface-tint: '#c0c1ff'
  primary: '#c0c1ff'
  on-primary: '#1000a9'
  primary-container: '#8083ff'
  on-primary-container: '#0d0096'
  inverse-primary: '#494bd6'
  secondary: '#d0bcff'
  on-secondary: '#3c0091'
  secondary-container: '#571bc1'
  on-secondary-container: '#c4abff'
  tertiary: '#7bd0ff'
  on-tertiary: '#00354a'
  tertiary-container: '#009bd1'
  on-tertiary-container: '#002d40'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e1e0ff'
  primary-fixed-dim: '#c0c1ff'
  on-primary-fixed: '#07006c'
  on-primary-fixed-variant: '#2f2ebe'
  secondary-fixed: '#e9ddff'
  secondary-fixed-dim: '#d0bcff'
  on-secondary-fixed: '#23005c'
  on-secondary-fixed-variant: '#5516be'
  tertiary-fixed: '#c4e7ff'
  tertiary-fixed-dim: '#7bd0ff'
  on-tertiary-fixed: '#001e2c'
  on-tertiary-fixed-variant: '#004c69'
  background: '#131317'
  on-background: '#e4e1e8'
  surface-variant: '#353439'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.03em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  title-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: -0.011em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: -0.006em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  label-mono-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0.02em
  label-mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-ui:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0.01em
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2.5rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system targets developers, AI researchers, and technical analysts deploying autonomous Model Context Protocol (MCP) agents for recursive web synthesis and multi-hop reasoning. The aesthetic fuses **Google Stitch/Material 3 AI-native surfaces** with an ethereal, **deep-obsidian cyberpunk minimalism**. 

The interface conveys high-velocity intelligence, spatial calm, and computational authority. It rejects busy visual clutter in favor of luminous focal points, atmospheric dark surfaces, and laser-precise technical telemetry. Visual interaction centers around floating agent docks, frosted glass capsules, and shimmering energetic states that signal background inference, token generation, and deep context gathering.

## Colors

The palette relies on absolute darkness balanced with phosphorescent luminescence:
- **Base Canvas (`#08080C`):** The foundational obsidian canvas, absorbing distraction.
- **Surface Elevation Layers (`#0E0E17`, `#161626`, `#1E1F35`):** Structural layers derived by blending neutral black with faint indigo undertones.
- **Primary & Secondary (`#6366F1`, `#8B5CF6`):** Dual-spectrum violet-indigo used for interactive highlights, active computation threads, and primary actions.
- **Cyber Blue Tertiary (`#38BDF8`):** Dedicated to MCP server telemetry, protocol indicators, external tool execution, and source citations.
- **Ambient Glows:** Soft 12% to 24% opacity volumetric gradients using radial blends of `#8B5CF6` and `#38BDF8` behind active synthesis cards and the floating search dock.

## Typography

The typographic hierarchy establishes clear boundaries between narrative reasoning, synthesis results, and runtime engine metrics:
- **Headlines & Titles:** Set in **Plus Jakarta Sans** with tight tracking to evoke modern technological precision without sterility.
- **Reading & Output Text:** Rendered in **Inter** with calibrated line-height to ensure dense analytical summaries remain fatigue-free during prolonged review sessions.
- **Telemetry, Prompts & Metadata:** Exclusively formatted in **JetBrains Mono** for model parameters, vector distances, token cost, protocol hooks, and MCP JSON-RPC schemas.

## Layout & Spacing

The layout operates on a fluid 12-column dynamic grid with responsive breakpoint constraints:
- **Desktop (≥ 1280px):** 12-column layout with 24px (`1.5rem`) gutters and a centered 1440px maximum container width. Research canvases support split-pane inspection (left: live query execution trace; right: structured dynamic report).
- **Tablet (768px - 1279px):** 8-column layout with collapsible inspector rails that transition to floating slide-over panels.
- **Mobile (< 768px):** 4-column layout; gutter shifts to 16px (`1rem`). The floating search capsule docks to the bottom safe-area margin to ensure immediate thumb reachability.

## Elevation & Depth

Visual hierarchy combines Google Material 3 tonal surface tiers with ethereal ambient lighting:
- **Level 0 (Canvas):** Pure `#08080C`.
- **Level 1 (Card/Containers):** Solid `#0E0E17` with a razor-thin top border highlight (`rgba(255, 255, 255, 0.08)`).
- **Level 2 (Active Panels):** `#161626` backed by a diffuse ambient glow (`0 0 32px -8px rgba(99, 102, 241, 0.12)`).
- **Floating Capsule Tier (Glassmorphism):** Background set to `rgba(14, 14, 23, 0.65)` layered with `backdrop-filter: blur(20px) saturate(180%)`, framed by a composite border gradient transitioning from `rgba(99, 102, 241, 0.4)` to `rgba(56, 189, 248, 0.1)`.
- **Active Agent State:** Interactive elements emit localized ambient backlights rather than directional drop-shadows, matching physical phosphorescent LED behaviour.

## Shapes

The design system embraces high-curvature geometry inspired by modern AI conversational surfaces:
- **Floating Controls & Search Docks:** Curvature token `3` (full pill radius) produces sleek, aerodynamic capsule shells.
- **Insight Cards & Dynamic Windows:** Use `rounded-lg` (2rem / 32px) to softly frame complex recursive agent trees while retaining modern friendliness.
- **Tags, Protocol Badges, and Input Fields:** Use standardized `1rem` (16px) pill shapes to create visual cohesion with the central research dock.

## Components

### Floating Search Capsule & Dock
- **Structure:** Pill-shaped floating capsule centered horizontally at the viewport bottom.
- **Surface:** Glassmorphic translucent obsidian (`rgba(14, 14, 23, 0.72)`) with `24px` backdrop blur, illuminated by a bottom-anchored violet-indigo radial highlight.
- **Interactive State:** Expands vertically to reveal parameter sliders (temperature, depth count, MCP source selection) without re-routing.

### Buttons & Illuminated Selectors
- **Primary Action:** Solid `#6366F1` pill button featuring white bold text, accompanied by an animated ambient halo on hover (`box-shadow: 0 0 20px rgba(99, 102, 241, 0.45)`).
- **Secondary Action:** Glass pill with a `rgba(255, 255, 255, 0.06)` fill and subtle border stroke (`rgba(255, 255, 255, 0.12)`).

### Pill-Shaped Segmented Controls
- Continuous dark trench (`#0E0E17`) containing smooth sliding pill indicators with white text for the active state and muted gray (`#94A3B8`) for inactive options.

### MCP Technical Badges & Source Chips
- Monospace chip components featuring a pulsating 6px status LED (`#38BDF8` for connected MCP servers, `#8B5CF6` for active tool invocation).
- Background uses 8% tint of the indicator color with matching 20% border stroke.

### Input Fields & Reasoning Checkboxes
- **Inputs:** Capsule boundaries with interior dark inset surfaces; focus shifts the subtle outline to an iridescent gradient (`#6366F1` to `#38BDF8`).
- **Checkboxes & Radios:** Smooth pill-toggle switches and circular radios with glowing interior pips when checked.

### Research Cards & Knowledge Trees
- Content cards use layered elevation tiers (`#0E0E17`) with indented monospace citations that reveal interactive preview tooltips on hover.