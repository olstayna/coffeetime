CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(160) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    role ENUM('customer', 'admin') NOT NULL DEFAULT 'customer',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(60) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    image_data LONGBLOB,
    image_mime VARCHAR(50),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_product_price CHECK (price > 0)
);

CREATE TABLE IF NOT EXISTS coupons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(40) NOT NULL UNIQUE,
    discount_type ENUM('percentage', 'fixed') NOT NULL,
    discount_value DECIMAL(10,2) NOT NULL,
    minimum_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    expires_at DATETIME NULL,
    first_order_only BOOLEAN NOT NULL DEFAULT FALSE,
    once_per_user BOOLEAN NOT NULL DEFAULT FALSE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_coupon_value CHECK (discount_value > 0)
);

CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    status ENUM('recebido', 'em preparo', 'em rota', 'entregue') NOT NULL DEFAULT 'recebido',
    payment_method ENUM('pix', 'cartao', 'dinheiro') NOT NULL,
    street VARCHAR(160) NOT NULL,
    number VARCHAR(20) NOT NULL,
    district VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    postal_code VARCHAR(10) NOT NULL,
    notes VARCHAR(300),
    coupon_code VARCHAR(40),
    discount DECIMAL(10,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    product_name VARCHAR(120) NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    quantity INT NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT chk_item_quantity CHECK (quantity > 0)
);

CREATE TABLE IF NOT EXISTS order_status_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    status VARCHAR(30) NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

INSERT IGNORE INTO products (id, name, description, category, price) VALUES
(1, 'Espresso da Casa', 'Café encorpado, extraído na hora com grãos selecionados.', 'Cafés', 7.00),
(2, 'Cappuccino Cremoso', 'Espresso, leite vaporizado, espuma e um toque de canela.', 'Cafés', 13.90),
(3, 'Mocha de Chocolate', 'Café, leite cremoso e chocolate meio amargo.', 'Cafés', 15.50),
(4, 'Croissant Artesanal', 'Massa folhada amanteigada, assada diariamente.', 'Salgados', 12.00),
(5, 'Cheesecake de Frutas', 'Cheesecake com calda artesanal de frutas vermelhas.', 'Doces', 16.90),
(6, 'Pão de Queijo', 'Porção com quatro unidades, crocantes por fora e macias por dentro.', 'Salgados', 11.50),
(7, 'Latte Baunilha', 'Espresso suave, leite vaporizado e baunilha natural.', 'Cafés', 14.90),
(8, 'Americano', 'Espresso duplo alongado com água quente.', 'Cafés', 9.50),
(9, 'Cookie de Chocolate', 'Cookie macio com gotas generosas de chocolate.', 'Doces', 9.90),
(10, 'Brownie Intenso', 'Brownie úmido de chocolate meio amargo.', 'Doces', 12.90),
(11, 'Croissant de Presunto', 'Croissant artesanal recheado com presunto e queijo.', 'Salgados', 17.90),
(12, 'Combo Café da Manhã', 'Cappuccino, croissant e pão de queijo para começar bem o dia.', 'Combos', 29.90);

INSERT IGNORE INTO coupons (code, discount_type, discount_value, minimum_amount, expires_at, first_order_only) VALUES
('BEMVINDO10', 'percentage', 10.00, 20.00, '2030-12-31 23:59:59', TRUE),
('CAFE5', 'fixed', 5.00, 30.00, '2030-12-31 23:59:59', FALSE);
UPDATE coupons SET first_order_only=TRUE WHERE code='BEMVINDO10';

INSERT IGNORE INTO products (id, name, description, category, price) VALUES
(13, 'Flat White', 'Dose dupla de espresso com leite microvaporizado e textura aveludada.', 'Cafés', 14.50),
(14, 'Macchiato Caramelo', 'Espresso intenso, espuma cremosa e fio de caramelo.', 'Cafés', 16.50),
(15, 'Cold Brew', 'Café extraído a frio por 18 horas, leve e naturalmente doce.', 'Gelados', 15.90),
(16, 'Croissant de Amêndoas', 'Massa folhada com creme de amêndoas e lâminas tostadas.', 'Salgados', 18.90),
(17, 'Toast Caprese', 'Pão artesanal, tomate, muçarela, pesto e folhas frescas.', 'Salgados', 22.90),
(18, 'Combo Brunch', 'Cappuccino, croissant artesanal e doce do dia.', 'Combos', 34.90);

UPDATE products SET description='Espresso encorpado de 60 ml, extraído na hora com grãos selecionados.' WHERE id=1;
UPDATE products SET description='Espresso, leite vaporizado e espuma cremosa, 240 ml, com toque de canela.' WHERE id=2;
UPDATE products SET description='Café, leite cremoso e chocolate meio amargo, 300 ml.' WHERE id=3;
UPDATE products SET description='Espresso suave, leite vaporizado e baunilha natural, 300 ml.' WHERE id=7;
UPDATE products SET description='Espresso duplo de 120 ml alongado com água quente.' WHERE id=8;
UPDATE products SET description='Dose dupla de espresso com leite microvaporizado, 200 ml.' WHERE id=13;
UPDATE products SET description='Espresso intenso, espuma cremosa e caramelo, 240 ml.' WHERE id=14;
UPDATE products SET description='Café de 350 ml extraído a frio por 18 horas, leve e naturalmente doce.' WHERE id=15;

INSERT IGNORE INTO products (id, name, description, category, price) VALUES
(19, 'Grãos Serra da Mantiqueira', 'Pacote de 250 g, torra média, notas de caramelo, chocolate e castanhas.', 'Grãos', 38.90),
(20, 'Grãos Cerrado Mineiro', 'Pacote de 500 g, torra média-clara, notas de frutas amarelas e mel.', 'Grãos', 64.90);
