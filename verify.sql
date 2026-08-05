-- Run these read-only checks in the Lakebase SQL Editor after deployment.

SELECT COUNT(*) AS ticket_count
FROM support_app.tickets;

SELECT ticket_id, COUNT(*) AS message_count
FROM support_app.ticket_messages
GROUP BY ticket_id
ORDER BY ticket_id;

SELECT COUNT(DISTINCT status) AS status_count
FROM support_app.tickets;

SELECT
    tc.constraint_name,
    tc.constraint_type
FROM information_schema.table_constraints AS tc
WHERE tc.table_schema = 'support_app'
  AND tc.table_name = 'ticket_messages'
ORDER BY tc.constraint_type, tc.constraint_name;

SELECT
    t.ticket_id,
    t.title,
    t.status,
    m.author,
    m.message_text,
    m.created_at
FROM support_app.tickets AS t
JOIN support_app.ticket_messages AS m
    ON m.ticket_id = t.ticket_id
ORDER BY t.ticket_id, m.created_at;
