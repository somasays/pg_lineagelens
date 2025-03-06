-- Create necessary extensions
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create test tables
CREATE SCHEMA IF NOT EXISTS test;

CREATE TABLE IF NOT EXISTS test.users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS test.orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES test.users(id),
    order_date TIMESTAMP DEFAULT NOW(),
    total_amount DECIMAL(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS test.order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES test.orders(id),
    product_name VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL
);

-- Insert some sample data
INSERT INTO test.users (name, email) VALUES
    ('John Doe', 'john@example.com'),
    ('Jane Smith', 'jane@example.com'),
    ('Michael Johnson', 'michael@example.com');

INSERT INTO test.orders (user_id, total_amount) VALUES
    (1, 100.00),
    (1, 200.00),
    (2, 150.00);

INSERT INTO test.order_items (order_id, product_name, quantity, price) VALUES
    (1, 'Widget A', 2, 25.00),
    (1, 'Widget B', 1, 50.00),
    (2, 'Widget C', 4, 50.00),
    (3, 'Widget A', 3, 25.00),
    (3, 'Widget D', 1, 75.00);

-- Execute some test queries to populate pg_stat_statements
SELECT * FROM test.users;
SELECT * FROM test.orders WHERE user_id = 1;
SELECT u.name, o.order_date, o.total_amount 
FROM test.users u 
JOIN test.orders o ON u.id = o.user_id;

INSERT INTO test.users (name, email) VALUES ('Test User', 'test@example.com');

UPDATE test.orders SET total_amount = 125.00 WHERE id = 1;

SELECT u.name, o.order_date, oi.product_name, oi.quantity, oi.price
FROM test.users u
JOIN test.orders o ON u.id = o.user_id
JOIN test.order_items oi ON o.id = oi.order_id
WHERE u.id = 1;