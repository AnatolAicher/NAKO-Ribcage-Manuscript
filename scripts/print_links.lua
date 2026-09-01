-- Rewrites cross-page links (page.qmd#anchor) to absolute site URLs in every
-- output except HTML, where Quarto resolves them itself. The Word and PDF
-- outputs otherwise keep the relative .qmd path, which is dead outside the site.
-- The site URL is read from website.site-url in _quarto.yml.
local site_url

local function read_site_url()
  local path = quarto.project.directory .. "/_quarto.yml"
  local f = assert(io.open(path, "r"), "print_links.lua: cannot open " .. path)
  local text = f:read("a")
  f:close()
  local url = text:match("\n%s*site%-url:%s*(%S+)")
  assert(url, "print_links.lua: website.site-url is not set in _quarto.yml")
  if url:sub(-1) ~= "/" then
    url = url .. "/"
  end
  return url
end

function Link(el)
  if quarto.doc.is_format("html") then
    return nil
  end
  local page, anchor = el.target:match("^([^/#]+)%.qmd(#?.*)$")
  if not page then
    return nil
  end
  site_url = site_url or read_site_url()
  el.target = site_url .. page .. ".html" .. anchor
  return el
end
