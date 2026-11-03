-- Denominator: root pages per client.
SELECT client, COUNT(*) AS pages
FROM `httparchive.crawl.pages`
WHERE date = '2026-10-01' AND is_root_page
GROUP BY client
