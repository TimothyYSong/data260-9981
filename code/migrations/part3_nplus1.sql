CREATE TABLE IF NOT EXISTS inspection_notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    restaurant_inspection_id INT NOT NULL,
    note VARCHAR(255) NOT NULL,
    FOREIGN KEY (restaurant_inspection_id)
        REFERENCES restaurant_inspections(id)
        ON DELETE CASCADE
);