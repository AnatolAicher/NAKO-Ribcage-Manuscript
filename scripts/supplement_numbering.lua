-- Numbers supplement sections as S1, S1.1, … by prefixing each heading's text.
-- Replaces pandoc's number-sections (set false in supplement.qmd) so the same
-- S-numbers appear in every output format (HTML site, docx).
local counters = { 0, 0, 0 }

function Header(el)
  if el.level > #counters or el.classes:includes("unnumbered") then
    return nil
  end
  counters[el.level] = counters[el.level] + 1
  for i = el.level + 1, #counters do
    counters[i] = 0
  end
  local parts = {}
  for i = 1, el.level do
    parts[i] = tostring(counters[i])
  end
  local number = "S" .. table.concat(parts, ".")
  local span = pandoc.Span({ pandoc.Str(number) }, pandoc.Attr("", { "header-section-number" }))
  el.content:insert(1, pandoc.Space())
  el.content:insert(1, span)
  return el
end
