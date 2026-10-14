-- =====================================================
-- Base de datos: Gerencia de Costos de Produccion
-- Sistema: PostgreSQL
-- Opcion de costeo: A (automatico)
-- =====================================================

-- IMPORTANTE: ejecutar este script estando conectado a la base de datos destino.
-- Ejemplo:
--   psql -U postgres -d gerencia_costos -f database_gerencia_costos.sql

-- =====================================================
-- 1. TABLAS PRINCIPALES
-- =====================================================

CREATE TABLE unidades_medida (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    abreviatura VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE proveedores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    contacto VARCHAR(200),
    telefono VARCHAR(50),
    email VARCHAR(100),
    direccion TEXT
);

CREATE TABLE insumos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    unidad_medida_id INTEGER NOT NULL REFERENCES unidades_medida(id),
    proveedor_id INTEGER REFERENCES proveedores(id),
    precio_compra DECIMAL(12,2) NOT NULL DEFAULT 0 CHECK (precio_compra >= 0),
    stock_actual DECIMAL(12,4) NOT NULL DEFAULT 0 CHECK (stock_actual >= 0)
);

CREATE TABLE productos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT
);

CREATE TABLE recetas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    version VARCHAR(50) NOT NULL DEFAULT '1.0',
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Relacion N:M: un producto puede tener varias recetas y viceversa
CREATE TABLE productos_recetas (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    receta_id INTEGER NOT NULL REFERENCES recetas(id) ON DELETE CASCADE,
    UNIQUE(producto_id, receta_id)
);

CREATE TABLE recetas_insumos (
    id SERIAL PRIMARY KEY,
    receta_id INTEGER NOT NULL REFERENCES recetas(id) ON DELETE CASCADE,
    insumo_id INTEGER NOT NULL REFERENCES insumos(id) ON DELETE CASCADE,
    cantidad DECIMAL(12,4) NOT NULL CHECK (cantidad > 0),
    UNIQUE(receta_id, insumo_id)
);

CREATE TABLE compras (
    id SERIAL PRIMARY KEY,
    proveedor_id INTEGER REFERENCES proveedores(id),
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total DECIMAL(12,2) NOT NULL DEFAULT 0 CHECK (total >= 0)
);

CREATE TABLE compras_detalle (
    id SERIAL PRIMARY KEY,
    compra_id INTEGER NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
    insumo_id INTEGER NOT NULL REFERENCES insumos(id),
    cantidad DECIMAL(12,4) NOT NULL CHECK (cantidad > 0),
    precio_unitario DECIMAL(12,4) NOT NULL CHECK (precio_unitario >= 0),
    subtotal DECIMAL(12,2) NOT NULL DEFAULT 0 CHECK (subtotal >= 0)
);

CREATE TABLE lotes_produccion (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(50) NOT NULL DEFAULT 'ABIERTO' CHECK (estado IN ('ABIERTO', 'CERRADO')),
    costo_real_total DECIMAL(12,2) NOT NULL DEFAULT 0 CHECK (costo_real_total >= 0)
);

CREATE TABLE lotes_productos (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER NOT NULL REFERENCES lotes_produccion(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    receta_id INTEGER REFERENCES recetas(id),
    cantidad DECIMAL(12,4) NOT NULL CHECK (cantidad > 0)
);

CREATE TABLE lotes_insumos (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER NOT NULL REFERENCES lotes_produccion(id) ON DELETE CASCADE,
    insumo_id INTEGER NOT NULL REFERENCES insumos(id),
    cantidad DECIMAL(12,4) NOT NULL CHECK (cantidad > 0)
);

CREATE TABLE gastos (
    id SERIAL PRIMARY KEY,
    categoria VARCHAR(100) NOT NULL,
    descripcion TEXT,
    monto DECIMAL(12,2) NOT NULL CHECK (monto >= 0),
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE gastos_lotes (
    id SERIAL PRIMARY KEY,
    gasto_id INTEGER NOT NULL REFERENCES gastos(id) ON DELETE CASCADE,
    lote_id INTEGER NOT NULL REFERENCES lotes_produccion(id) ON DELETE CASCADE,
    monto_asignado DECIMAL(12,2) NOT NULL CHECK (monto_asignado >= 0)
);

CREATE TABLE costos_historicos (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER NOT NULL REFERENCES lotes_produccion(id),
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cantidad_fabricada DECIMAL(12,4) NOT NULL CHECK (cantidad_fabricada > 0),
    costo_total DECIMAL(12,2) NOT NULL CHECK (costo_total >= 0),
    costo_unitario DECIMAL(12,4) NOT NULL CHECK (costo_unitario >= 0)
);

-- =====================================================
-- 2. FUNCIONES Y TRIGGERS
-- =====================================================

-- 2.1 Al insertar detalle de compra: calcular subtotal, actualizar stock y precio del insumo
CREATE OR REPLACE FUNCTION trf_procesar_detalle_compra_insert()
RETURNS TRIGGER AS $$
BEGIN
    NEW.subtotal := ROUND(NEW.cantidad * NEW.precio_unitario, 2);

    UPDATE insumos
    SET stock_actual = stock_actual + NEW.cantidad,
        precio_compra = NEW.precio_unitario
    WHERE id = NEW.insumo_id;

    UPDATE compras
    SET total = total + NEW.subtotal
    WHERE id = NEW.compra_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_compras_detalle_insert
BEFORE INSERT ON compras_detalle
FOR EACH ROW
EXECUTE FUNCTION trf_procesar_detalle_compra_insert();

-- 2.2 Al actualizar/eliminar detalle de compra: reajustar stock y total
CREATE OR REPLACE FUNCTION trf_procesar_detalle_compra_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.subtotal := ROUND(NEW.cantidad * NEW.precio_unitario, 2);

    -- Revertir stock anterior y aplicar nuevo
    UPDATE insumos
    SET stock_actual = stock_actual - OLD.cantidad + NEW.cantidad,
        precio_compra = NEW.precio_unitario
    WHERE id = NEW.insumo_id;

    -- Reajustar total de la compra
    UPDATE compras
    SET total = total - OLD.subtotal + NEW.subtotal
    WHERE id = NEW.compra_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_compras_detalle_update
BEFORE UPDATE ON compras_detalle
FOR EACH ROW
EXECUTE FUNCTION trf_procesar_detalle_compra_update();

CREATE OR REPLACE FUNCTION trf_procesar_detalle_compra_delete()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE insumos
    SET stock_actual = stock_actual - OLD.cantidad
    WHERE id = OLD.insumo_id;

    UPDATE compras
    SET total = total - OLD.subtotal
    WHERE id = OLD.compra_id;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_compras_detalle_delete
AFTER DELETE ON compras_detalle
FOR EACH ROW
EXECUTE FUNCTION trf_procesar_detalle_compra_delete();

-- 2.3 Al insertar insumo en lote: verificar stock y descontar
CREATE OR REPLACE FUNCTION trf_procesar_lote_insumo_insert()
RETURNS TRIGGER AS $$
DECLARE
    v_stock DECIMAL(12,4);
BEGIN
    SELECT stock_actual INTO v_stock FROM insumos WHERE id = NEW.insumo_id;

    IF v_stock < NEW.cantidad THEN
        RAISE EXCEPTION 'Stock insuficiente para el insumo ID % (disponible: %, requerido: %)',
            NEW.insumo_id, v_stock, NEW.cantidad;
    END IF;

    UPDATE insumos
    SET stock_actual = stock_actual - NEW.cantidad
    WHERE id = NEW.insumo_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lotes_insumos_insert
BEFORE INSERT ON lotes_insumos
FOR EACH ROW
EXECUTE FUNCTION trf_procesar_lote_insumo_insert();

-- 2.4 Al actualizar/eliminar insumo de lote: reajustar stock
CREATE OR REPLACE FUNCTION trf_procesar_lote_insumo_update()
RETURNS TRIGGER AS $$
DECLARE
    v_stock DECIMAL(12,4);
BEGIN
    SELECT stock_actual INTO v_stock FROM insumos WHERE id = NEW.insumo_id;

    IF (v_stock + OLD.cantidad) < NEW.cantidad THEN
        RAISE EXCEPTION 'Stock insuficiente para actualizar el insumo ID %', NEW.insumo_id;
    END IF;

    UPDATE insumos
    SET stock_actual = stock_actual + OLD.cantidad - NEW.cantidad
    WHERE id = NEW.insumo_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lotes_insumos_update
BEFORE UPDATE ON lotes_insumos
FOR EACH ROW
EXECUTE FUNCTION trf_procesar_lote_insumo_update();

CREATE OR REPLACE FUNCTION trf_procesar_lote_insumo_delete()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE insumos
    SET stock_actual = stock_actual + OLD.cantidad
    WHERE id = OLD.insumo_id;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lotes_insumos_delete
AFTER DELETE ON lotes_insumos
FOR EACH ROW
EXECUTE FUNCTION trf_procesar_lote_insumo_delete();

-- 2.5 Al cerrar un lote: calcular costos y generar costos_historicos
CREATE OR REPLACE FUNCTION trf_cerrar_lote()
RETURNS TRIGGER AS $$
DECLARE
    v_costo_insumos DECIMAL(12,2);
    v_costo_gastos DECIMAL(12,2);
    v_costo_total DECIMAL(12,2);
    v_total_unidades DECIMAL(12,4);
    rec RECORD;
BEGIN
    IF NEW.estado = 'CERRADO' AND OLD.estado != 'CERRADO' THEN
        -- Costo por insumos usados (cantidad * ultimo precio de compra)
        SELECT COALESCE(SUM(li.cantidad * i.precio_compra), 0)
        INTO v_costo_insumos
        FROM lotes_insumos li
        JOIN insumos i ON li.insumo_id = i.id
        WHERE li.lote_id = NEW.id;

        -- Costo por gastos asignados al lote
        SELECT COALESCE(SUM(monto_asignado), 0)
        INTO v_costo_gastos
        FROM gastos_lotes
        WHERE lote_id = NEW.id;

        v_costo_total := v_costo_insumos + v_costo_gastos;
        NEW.costo_real_total := v_costo_total;

        -- Total de unidades fabricadas en el lote
        SELECT COALESCE(SUM(cantidad), 0)
        INTO v_total_unidades
        FROM lotes_productos
        WHERE lote_id = NEW.id;

        IF v_total_unidades = 0 THEN
            RAISE EXCEPTION 'No se puede cerrar un lote sin productos fabricados';
        END IF;

        -- Limpiar registros previos si se reabriera (no aplicable aqui, pero seguro)
        DELETE FROM costos_historicos WHERE lote_id = NEW.id;

        -- Generar costos historicos por producto (distribucion proporcional)
        FOR rec IN
            SELECT lp.producto_id, lp.cantidad
            FROM lotes_productos lp
            WHERE lp.lote_id = NEW.id
        LOOP
            INSERT INTO costos_historicos (
                lote_id, producto_id, cantidad_fabricada,
                costo_total, costo_unitario
            ) VALUES (
                NEW.id, rec.producto_id, rec.cantidad,
                ROUND((rec.cantidad / v_total_unidades) * v_costo_total, 2),
                ROUND(v_costo_total / v_total_unidades, 4)
            );
        END LOOP;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lotes_produccion_cerrar
BEFORE UPDATE ON lotes_produccion
FOR EACH ROW
EXECUTE FUNCTION trf_cerrar_lote();

-- =====================================================
-- 3. INDICES PARA MEJOR RENDIMIENTO
-- =====================================================

CREATE INDEX idx_insumos_unidad_medida ON insumos(unidad_medida_id);
CREATE INDEX idx_insumos_proveedor ON insumos(proveedor_id);
CREATE INDEX idx_compras_detalle_compra ON compras_detalle(compra_id);
CREATE INDEX idx_compras_detalle_insumo ON compras_detalle(insumo_id);
CREATE INDEX idx_recetas_insumos_receta ON recetas_insumos(receta_id);
CREATE INDEX idx_recetas_insumos_insumo ON recetas_insumos(insumo_id);
CREATE INDEX idx_lotes_productos_lote ON lotes_productos(lote_id);
CREATE INDEX idx_lotes_insumos_lote ON lotes_insumos(lote_id);
CREATE INDEX idx_gastos_lotes_lote ON gastos_lotes(lote_id);
CREATE INDEX idx_costos_historicos_producto ON costos_historicos(producto_id);
CREATE INDEX idx_costos_historicos_lote ON costos_historicos(lote_id);

-- =====================================================
-- 4. DATOS DE EJEMPLO
-- =====================================================

INSERT INTO unidades_medida (nombre, abreviatura) VALUES
('Kilogramo', 'kg'),
('Litro', 'L'),
('Unidad', 'u'),
('Metro', 'm'),
('Centimetro', 'cm');

INSERT INTO proveedores (nombre, contacto, telefono, email) VALUES
('Maderas del Norte', 'Juan Perez', '555-0101', 'juan@maderasnorte.com'),
('Ferreteria Industrial', 'Maria Lopez', '555-0202', 'maria@ferreind.com'),
('Plásticos Sur', 'Carlos Ruiz', '555-0303', 'carlos@plasticossur.com');

INSERT INTO insumos (nombre, unidad_medida_id, proveedor_id, precio_compra, stock_actual) VALUES
('Madera pino', 4, 1, 2.50, 0),
('Tornillo 1/4"', 3, 2, 0.10, 0),
('Pegamento industrial', 2, 3, 5.00, 0),
('Pintura blanca', 2, 3, 8.00, 0),
('Lija gruesa', 3, 2, 0.50, 0);

INSERT INTO productos (nombre, descripcion) VALUES
('Silla de madera', 'Silla rustica de pino'),
('Mesa de comedor', 'Mesa para 4 personas'),
('Banquito', 'Banquito de cocina');

INSERT INTO recetas (nombre, version, activa) VALUES
('Receta silla estandar', '1.0', TRUE),
('Receta mesa estandar', '1.0', TRUE),
('Receta banquito estandar', '1.0', TRUE);

INSERT INTO productos_recetas (producto_id, receta_id) VALUES
(1, 1),
(2, 2),
(3, 3);

-- Receta silla: 2.5 m madera, 8 tornillos, 0.2 L pegamento
INSERT INTO recetas_insumos (receta_id, insumo_id, cantidad) VALUES
(1, 1, 2.5),
(1, 2, 8),
(1, 3, 0.2);

-- Receta mesa: 6 m madera, 16 tornillos, 0.4 L pegamento
INSERT INTO recetas_insumos (receta_id, insumo_id, cantidad) VALUES
(2, 1, 6),
(2, 2, 16),
(2, 3, 0.4);

-- Receta banquito: 1.5 m madera, 6 tornillos, 0.1 L pegamento
INSERT INTO recetas_insumos (receta_id, insumo_id, cantidad) VALUES
(3, 1, 1.5),
(3, 2, 6),
(3, 3, 0.1);

-- =====================================================
-- 5. VISTAS UTILES
-- =====================================================

-- Vista de recetas con sus insumos y costos estimados
CREATE OR REPLACE VIEW v_recetas_costos AS
SELECT
    r.id AS receta_id,
    r.nombre AS receta,
    p.id AS producto_id,
    p.nombre AS producto,
    i.id AS insumo_id,
    i.nombre AS insumo,
    ri.cantidad,
    um.abreviatura AS unidad,
    i.precio_compra,
    ROUND(ri.cantidad * i.precio_compra, 2) AS costo_insumo
FROM recetas r
JOIN productos_recetas pr ON r.id = pr.receta_id
JOIN productos p ON pr.producto_id = p.id
JOIN recetas_insumos ri ON r.id = ri.receta_id
JOIN insumos i ON ri.insumo_id = i.id
JOIN unidades_medida um ON i.unidad_medida_id = um.id;

-- Vista de costo total estimado por receta
CREATE OR REPLACE VIEW v_recetas_costo_total AS
SELECT
    receta_id,
    receta,
    producto_id,
    producto,
    SUM(costo_insumo) AS costo_total_estimado
FROM v_recetas_costos
GROUP BY receta_id, receta, producto_id, producto;

-- Vista de evolucion historica de costos por producto
CREATE OR REPLACE VIEW v_evolucion_costos AS
SELECT
    p.id AS producto_id,
    p.nombre AS producto,
    ch.fecha,
    ch.cantidad_fabricada,
    ch.costo_unitario,
    ch.costo_total,
    lp.id AS lote_id
FROM costos_historicos ch
JOIN productos p ON ch.producto_id = p.id
JOIN lotes_produccion lp ON ch.lote_id = lp.id
ORDER BY p.nombre, ch.fecha;
