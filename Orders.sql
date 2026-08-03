-- COMPANY
CREATE TABLE company(
	company_id SERIAL PRIMARY KEY,
	company_name VARCHAR(100) NOT NULL
);

-- CUSTOMER
CREATE TABLE customer(
	customer_id SERIAL PRIMARY KEY,
	customer_name VARCHAR(100) NOT NULL
);

-- DISPATCH
CREATE TABLE dispatch(
	dispatch_id SERIAL PRIMARY KEY,
	customer_delivery_date DATE NOT NULL,
	route VARCHAR(100) NOT NULL,
	cut_location VARCHAR(100) NOT NULL
);

-- ORDERS
CREATE TABLE orders(
	order_id SERIAL PRIMARY KEY,
	customer_id INT NOT NULL REFERENCES customer(customer_id),
	company_id INT NOT NULL REFERENCES company(company_id),
	bag VARCHAR(100) NOT NULL,
	dispatch_id INT NOT NULL REFERENCES dispatch(dispatch_id),
	wafer_quantity INT,
	chip_quantity INT,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE orders 
  ALTER COLUMN wafer_quantity SET NOT NULL,
  ALTER COLUMN chip_quantity SET NOT NULL,
  ADD CONSTRAINT wafer_qty_nonneg CHECK (wafer_quantity >= 0),
  ADD CONSTRAINT chip_qty_nonneg CHECK (chip_quantity >= 0);

-- WAFERS
CREATE TABLE wafers(
    wafer_id SERIAL PRIMARY KEY,
	wafer_number VARCHAR(100) NOT NULL,
    wafer_name VARCHAR(100),
    wafer_number_2 VARCHAR(100),
    wafer_part_id VARCHAR(100)
);

-- CHIPS
CREATE TABLE chips(
    chip_id SERIAL PRIMARY KEY,
	chip_number VARCHAR(100) NOT NULL,
    chip_name VARCHAR(100),
    chip_numb_2 VARCHAR(100),
    chip_part_id VARCHAR(100)
);

-- WAFER ORDERS
CREATE TABLE order_wafers(
    order_id INT NOT NULL REFERENCES orders(order_id),
    wafer_id INT NOT NULL REFERENCES wafers(wafer_id),
    PRIMARY KEY (order_id, wafer_id)	
);

-- CHIP ORDERS
CREATE TABLE order_chips(
    order_id INT NOT NULL REFERENCES orders(order_id),
    chip_id INT NOT NULL REFERENCES chips(chip_id),
    PRIMARY KEY (order_id, chip_id)
);

-- CLEAR DATA
TRUNCATE TABLE order_chips, order_wafers, orders, dispatch, wafers, chips, customer, company
RESTART IDENTITY CASCADE;

-- INSERT COMPANY NAMES
INSERT INTO company(company_name)
VALUES
('230'),
('4586'),
('967'),
('APPLE'),
('GlobalFoundries'),
('MSS US EXP'),
('Nvidia'),
('on semi'),
('Qualcomm'),
('Sandisk'),
('SJ'),
('Stanford'),
('TEL'),
('TEST1'),
('TEST2'),
('TEST3'),
('TEST4'),
('TEST5'),
('TEST6'),
('TEST7'),
('TEST8'),
('TSS');
--------------------------------------------------
SELECT * FROM company
SELECT * FROM customer
SELECT * FROM dispatch
SELECT * FROM orders
SELECT * FROM wafers
SELECT * FROM chips
SELECT * FROM order_wafers
SELECT * FROM order_chips

SELECT
    o.order_id,
    o.created_at,
    c.customer_name,
    co.company_name,
    o.bag,
    d.customer_delivery_date,
    d.route,
    d.cut_location,
    o.wafer_quantity,
    o.chip_quantity,
 
    -- Roll up all wafer numbers/names linked to this order into one string
    STRING_AGG(DISTINCT w.wafer_number, ', ' ORDER BY w.wafer_number) AS wafer_numbers,
    STRING_AGG(DISTINCT w.wafer_name, ', ') AS wafer_names,
 
    -- Roll up all chip numbers/names linked to this order into one string
    STRING_AGG(DISTINCT ch.chip_number, ', ' ORDER BY ch.chip_number) AS chip_numbers,
    STRING_AGG(DISTINCT ch.chip_name, ', ') AS chip_names
 
FROM orders o
JOIN customer c        ON o.customer_id = c.customer_id
JOIN company co         ON o.company_id = co.company_id
JOIN dispatch d         ON o.dispatch_id = d.dispatch_id
LEFT JOIN order_wafers ow ON o.order_id = ow.order_id
LEFT JOIN wafers w        ON ow.wafer_id = w.wafer_id
LEFT JOIN order_chips oc  ON o.order_id = oc.order_id
LEFT JOIN chips ch        ON oc.chip_id = ch.chip_id
 
GROUP BY
    o.order_id, o.created_at, c.customer_name, co.company_name,
    o.bag, d.customer_delivery_date, d.route, d.cut_location,
    o.wafer_quantity, o.chip_quantity
 
ORDER BY o.order_id;
 

SELECT * FROM order_summary;

SELECT * FROM order_summary WHERE order_id = 1;

SELECT * FROM order_summary WHERE company_name = 'Nvidia';

SELECT * FROM order_summary
WHERE customer_delivery_date BETWEEN '2026-07-01' AND '2026-07-31';
