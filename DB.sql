CREATE TABLE IF NOT EXISTS backend_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    contact_no VARCHAR(20) DEFAULT '',
    gender VARCHAR(10) DEFAULT '',
    email VARCHAR(100) DEFAULT '',
    address TEXT DEFAULT '',
    usertype VARCHAR(50) DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO backend_user (username, password, contact_no, gender, email, address, usertype)
VALUES ('coach', 'coach123', '9876543210', 'Male', 'coach@cricket.com', 'Mumbai', 'Coach');
