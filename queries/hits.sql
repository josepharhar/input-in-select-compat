-- Root pages hitting InputParsedParentSelect (5546) or InputParsedAncestorSelect (5547).
SELECT
  client,
  page,
  rank,
  EXISTS(SELECT 1 FROM UNNEST(features) WHERE id = '5546' AND type = 'default') AS parent_select,
  EXISTS(SELECT 1 FROM UNNEST(features) WHERE id = '5547' AND type = 'default') AS ancestor_select
FROM `httparchive.crawl.pages`
WHERE date = '2026-10-01'
  AND is_root_page
  AND EXISTS(SELECT 1 FROM UNNEST(features) WHERE id IN ('5546', '5547') AND type = 'default')
