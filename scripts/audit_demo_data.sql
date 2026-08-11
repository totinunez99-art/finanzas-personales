-- Auditoría de datos demo ANTES de borrar (docs/24). SOLO LECTURA: ningún DELETE.
-- Uso: Get-Content <este archivo> | docker exec -i finanzaspersonales-db-1 psql -U finanzas -d finanzas

\echo '=== 1. Batches demo que serian eliminados ==='
SELECT b.filename, b.created_at, a.name AS cuenta, b.rows_read, b.rows_inserted,
       (SELECT count(*) FROM transactions t WHERE t.import_batch_id = b.id) AS tx_en_db
FROM import_batches b JOIN accounts a ON a.id = b.account_id
WHERE b.filename IN ('demo_junio.csv','demo_julio.csv','demo_agosto_para_wizard.csv')
ORDER BY b.created_at;

\echo '=== 2. Decisiones de clasificacion asociadas a esas transacciones ==='
SELECT count(*) AS decisiones
FROM classification_decisions d
WHERE d.transaction_id IN (
  SELECT t.id FROM transactions t
  JOIN import_batches b ON b.id = t.import_batch_id
  WHERE b.filename IN ('demo_junio.csv','demo_julio.csv','demo_agosto_para_wizard.csv'));

\echo '=== 3. Eventos de dominio asociados (por tipo de entidad) ==='
SELECT e.entity, count(*) AS eventos
FROM domain_events e
WHERE e.entity_id IN (
  SELECT t.id FROM transactions t JOIN import_batches b ON b.id = t.import_batch_id
  WHERE b.filename IN ('demo_junio.csv','demo_julio.csv','demo_agosto_para_wizard.csv')
  UNION
  SELECT b.id FROM import_batches b
  WHERE b.filename IN ('demo_junio.csv','demo_julio.csv','demo_agosto_para_wizard.csv'))
GROUP BY e.entity;

\echo '=== 4. RIESGO FK: reglas de categoria creadas desde decisiones demo (si > 0, decidir antes de borrar) ==='
SELECT count(*) AS reglas_derivadas_de_demo
FROM classification_rules r
WHERE r.created_from_decision_id IN (
  SELECT d.id FROM classification_decisions d
  WHERE d.transaction_id IN (
    SELECT t.id FROM transactions t JOIN import_batches b ON b.id = t.import_batch_id
    WHERE b.filename IN ('demo_junio.csv','demo_julio.csv','demo_agosto_para_wizard.csv')));

\echo '=== 5. Reglas de comercio aprendidas del usuario (se CONSERVAN; posible contaminacion demo) ==='
SELECT pattern, merchant, origin, priority, hits_count
FROM merchant_rules WHERE origin IN ('user','promoted') ORDER BY merchant;

\echo '=== 6. Transacciones demo reconciliadas con NO-demo (debe ser 0) ==='
SELECT count(*) AS reconciliadas_cruzadas
FROM transactions x
WHERE x.reconciled_with_id IN (
  SELECT t.id FROM transactions t JOIN import_batches b ON b.id = t.import_batch_id
  WHERE b.filename IN ('demo_junio.csv','demo_julio.csv','demo_agosto_para_wizard.csv'))
AND (x.import_batch_id IS NULL OR x.import_batch_id NOT IN (
  SELECT id FROM import_batches
  WHERE filename IN ('demo_junio.csv','demo_julio.csv','demo_agosto_para_wizard.csv')));

\echo '=== 7. Totales actuales de la base (linea base para verificar despues) ==='
SELECT (SELECT count(*) FROM import_batches) AS batches,
       (SELECT count(*) FROM transactions) AS transacciones,
       (SELECT count(*) FROM classification_decisions) AS decisiones,
       (SELECT count(*) FROM domain_events) AS eventos,
       (SELECT count(*) FROM merchant_rules) AS reglas_comercio,
       (SELECT count(*) FROM classification_rules) AS reglas_categoria,
       (SELECT count(*) FROM categories) AS categorias,
       (SELECT count(*) FROM accounts) AS cuentas,
       (SELECT count(*) FROM users) AS usuarios;
