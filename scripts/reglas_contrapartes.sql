-- Reglas de contraparte PERSONALES (ground truth del dueño, docs/24 §6.8.1).
-- Van en la BASE DE DATOS, nunca en el código: son datos personales y de terceros.
-- Idempotente: no duplica si ya existe el par (patrón, matcher).
-- Uso: type scripts\reglas_contrapartes.sql | docker exec -i finanzaspersonales-db-1 psql -U finanzas -d finanzas

-- Red de seguridad: si el contenedor aún no tiene las categorías nuevas sembradas,
-- se crean aquí (idempotente). Sin esto el INSERT de reglas fallaría EN SILENCIO.
INSERT INTO categories (id, user_id, name, kind, is_system, is_active, created_at)
SELECT gen_random_uuid(), u.id, v.nombre, v.kind, true, true, now()
FROM users u
CROSS JOIN (VALUES
    ('Aporte a Empresa Propia', 'asset'),
    ('Gastos de Negocio', 'expense')
) AS v(nombre, kind)
WHERE NOT EXISTS (SELECT 1 FROM categories c WHERE c.user_id = u.id AND c.name = v.nombre);

INSERT INTO classification_rules (id, user_id, matcher_type, pattern, category_id, origin, priority, hits_count, is_active, created_at)
SELECT gen_random_uuid(), u.id, 'description_contains', v.patron, c.id, 'user', 10, 0, true, now()
FROM users u
CROSS JOIN (VALUES
    ('CHRISTIAN NUNEZ',      'Préstamos Personales'),        -- padre: préstamos ida y vuelta
    ('JENS CHRISTIAN NUNEZ', 'Préstamos Personales'),
    ('AUTOMOTRIZ SU AUTO',   'Compra y Venta de Bienes'),    -- venta del vehículo
    ('AVICOLA LIMACHE',      'Aporte a Empresa Propia'),     -- capital a su empresa (asset)
    ('CRISTOBAL MERINO',     'Gastos de Negocio')            -- gasto del negocio, por única vez
) AS v(patron, categoria)
JOIN categories c ON c.name = v.categoria AND c.user_id = u.id
WHERE NOT EXISTS (
    SELECT 1 FROM classification_rules r
    WHERE r.user_id = u.id AND r.pattern = v.patron AND r.matcher_type = 'description_contains'
);

\echo '--- Reglas de usuario activas (prioridad 10 = ganan a las semilla) ---'
SELECT r.pattern, c.name AS categoria, c.kind AS naturaleza, r.origin, r.priority
FROM classification_rules r JOIN categories c ON c.id = r.category_id
WHERE r.origin = 'user' ORDER BY r.pattern;

\echo '--- Verificacion: reglas esperadas = 5 ---'
SELECT count(*) AS reglas_usuario FROM classification_rules WHERE origin = 'user';
