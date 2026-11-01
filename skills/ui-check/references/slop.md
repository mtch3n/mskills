# Default UI rules

These rules come from the corrections that the user gave most often. The project's own
design rules win. The tag after a rule is the `ui-check` finding or smell that shows
it.

## Surfaces

- Do not put a card inside a card. `card-in-card`
- Do not put a card around one item, one line or one control.
- Do not put a colored stripe on one side of a box. `accent-stripe`
- Do not give a box a colored fill and a border. Show a status or a warning as plain
  text, or as an icon and text. `tinted-box`
- Show an empty state as one muted line.
- Use space and a heading to make a group. Do not add a box only to make a group.
- Do not give a box a full border and a wide shadow. `border-shadow`
- Do not put an icon in a tinted tile above or next to each heading. `icon-tile`
- Do not make a row of identical cards, each with an icon, a heading and a sentence.
  `card-grid`
- Do not add separators between items that space already separates.

## Color

- Use only colors from the tokens. Do not write a hex value in a component.
  `off-token`, `drift`
- Do not tint a surface with the primary color.
- Do not use a gradient, a glow or a blurred see-through surface if the design does
  not ask for it. `gradient`, `gradient-text`, `glow`, `glass`
- Do not use the stock violet or indigo accent if it is not the brand color.
  `purple`
- Use few hues: neutrals, one accent and the status colors. `hues`

## Text

- Do not put a small upper-case label above a heading. `eyebrow`
- Do not put a helper sentence under each heading. Make the UI explain itself.
  `subtitles`
- Do not add a legend if an icon and a label already tell the same thing.
- Do not use emoji in UI text. `emoji`
- Do not use marketing words, for example "seamless", "unlock" or "elevate".
  `stock-copy`
- Do not add hints, "demo data" banners, "updated just now" or success text that
  stays.
- Do not put a sentence under a heading that tells again what the heading tells.
  `restates`, `helper-text`
- Do not use filler, for example "Just to confirm", "Here you can" or "Simply".
  `filler`
- Use 3 words or fewer on a button, 4 or fewer on a tab, 3 or fewer in a table
  header. `long-label`
- Keep paragraphs to 60 words or fewer. A website is not a text book: put a
  picture, a control or a table between long parts of text. `long-paragraph`,
  `wall-of-text`, `text-heavy`, `chatty`
- Use the terms of the platform and of the product. Do not invent a label.
- Make group headings look different from the items that the user can click.
- Keep body text near 45 to 75 characters on a line. `line-length`
- Do not use text smaller than 12 px. `small-text`
- Use one type scale on all pages and in all panels: about 5 to 7 font sizes.
  `drift`, `scale`
- Give items of one kind the same font size, height, padding and radius, for example
  the chips in a row. `inconsistent`

## Components and icons

- Use the component from the library, for example its tooltip, date picker and
  select. Do not use the browser `title` tooltip. `native-tooltip`
- Use one icon set with one line weight. Do not draw icons by hand. `icon-sets`
- Do not color an icon if it does not show a status.
- Use a badge only for a real status, not for decoration. `pills`
- Use the radius token. Do not make a button more round than the token. Use about 3
  or 4 radii. `scale`
- Make each click target 24 × 24 px or larger, or keep other targets away from it.
  `target-size`
- Show a single action in a row as a button, not as a link.
- Show the pointer cursor only on items that the user can click, and use one cursor
  for all buttons. Do not use special or image cursors. `cursor-lie`,
  `cursor-mixed`, `cursor-zoo`
- Do not draw two borders that touch. `double-border`
- Give buttons and badges more padding at the sides than at the top. `cramped-padding`
- Set `font: inherit` on form controls. `control-font`
- Align a checkbox with the first line of its label. `choice-centre`
- Put more space above a heading than below it. `proximity`
- Do not add status decoration: pulsing dots, progress rings or spinners on static
  data.
- Do not add tabs, pages or screens that have no task.

## Layout

- Align the edges of items that are in one column. `edge`
- Use one gap between items of one stack or row. `gap`
- Use one height for controls that are side by side. `row-height`
- Center an icon on the line of its label. `icon-centre`
- Align a table header with its cells. `table-column`
- Use the same page width, padding and header height on all pages. `pages differ`
- Put a dialog in the center of the content area, not in the center of the window.
- Put an indicator, for example a tab underline, on a line that it belongs to.

## Motion

- Animate only opacity and transform. Do not move or resize the layout.
- Do the steps of an animation in the order that the user asked for.

## Work

- Do not change or remove a part that the user did not name.
- Show a mockup before you build a new screen.
- Make design options different in structure, not only in color. `--variants`
- Write each correction from the user into the project's rules file.
