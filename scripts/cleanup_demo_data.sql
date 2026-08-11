-- Borrado de datos demo APROBADO (docs/24). Transacción única: todo o nada.
-- Alcance exacto de la auditoría: 3 batches, 31 tx, 34 eventos, 0 decisiones,
-- + cuenta "Cuenta Demo (datos ficticios)" solo si queda sin dependencias.
-- Uso: type <este archivo> | docker exec -i finanzaspersonales-db-1 psql -U finanzas -d finanzas

\timing on
\set ON_ERROR_STOP on

BEGIN;

-- 1. Decisiones de clasificación (auditoría: 0 — se ejecuta igual por si acaso)
DELETE FROM classification_decisions
WHERE transaction_id IN (
  SELECT t.id FROM transactions t
  JOIN import_batches b ON b.id = t.import_batch_id
  WHERE b.filename IN ('demo_junio.csv','demo_julio.csv','demo_agosto_para_wizard.csv'));

-- 2. Eventos de dominio de transacciones y batches demo (auditoría: 34)
DELETE FROM domain_events
WHERE entity_id IN (
  SELECT t.id FROM transactions t JOIN import_batches b ON b.id = t.import_batch_id
  WHERE b.filename IN ('demo_junio.csv','demo_julio.csv','demo_agosto_para_wizard.csv')
  UNION
  SELECT b.id FROM import_batches b
  WHERE b.filename IN ('demo_junio.csv','demo_julio.csv','demo_agosto_para_wizard.csv'));

-- 3. Transacciones demo (auditoría: 31)
DELETE FROM transactions
WHERE import_batch_id IN (
  SELECT id FROM import_batches
  WHERE filename IN ('demo_junio.csv','demo_julio.csv','demo_agosto_para_wizard.csv'));

-- 4. Batches demo (auditoría: 3)
DELETE FROM import_batches
WHERE filename IN ('demo_junio.csv','demo_julio.csv','demo_agosto_para_wizard.csv');

-- 5. Cuenta demo, SOLO si quedó sin ninguna dependencia (guardas explícitas)
DELETE FROM accounts a
WHERE a.name = 'Cuenta Demo (datos ficticios)'
  AND NOT EXISTS (SELECT 1 FROM transactions t WHERE t.account_id = a.id)
  AND NOT EXISTS (SELECT 1 FROM import_batches b WHERE b.account_id = a.id);

COMMIT;

\echo '=== VERIFICACION POST-BORRADO ==='

\echo '--- V1: batches demo restantes (esperado 0) ---'
SELECT count(*) FROM import_batches
WHERE filename IN ('demo_junio.csv','demo_julio.csv','demo_agosto_para_wizard.csv');

\echo '--- V2: transacciones huerfanas de batch inexistente (esperado 0) ---'
SELECT count(*) FROM transactions t
WHERE t.import_batch_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM import_batches b WHERE b.id = t.import_batch_id);

\echo '--- V3: decisiones huerfanas de transaccion inexistente (esperado 0) ---'
SELECT count(*) FROM classification_decisions d
WHERE NOT EXISTS (SELECT 1 FROM transactions t WHERE t.id = d.transaction_id);

\echo '--- V4: transacciones o batches apuntando a cuenta inexistente (esperado 0 | 0) ---'
SELECT (SELECT count(*) FROM transactions t
        WHERE NOT EXISTS (SELECT 1 FROM accounts a WHERE a.id = t.account_id)) AS tx_sin_cuenta,
       (SELECT count(*) FROM import_batches b
        WHERE NOT EXISTS (SELECT 1 FROM accounts a WHERE a.id = b.account_id)) AS batch_sin_cuenta;

\echo '--- V5: totales finales (esperado: 0 batches, 0 tx, 0 decisiones, 0 eventos, 0 cuentas, 1 usuario) ---'
SELECT (SELECT count(*) FROM import_batches) AS batches,
       (SELECT count(*) FROM transactions) AS transacciones,
       (SELECT count(*) FROM classification_decisions) AS decisiones,
       (SELECT count(*) FROM domain_events) AS eventos,
       (SELECT count(*) FROM accounts) AS cuentas,
       (SELECT count(*) FROM users) AS usuarios;
