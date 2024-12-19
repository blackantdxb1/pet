DROP TABLE IF EXISTS chat_images;
DROP TABLE IF EXISTS chats;
DROP TABLE IF EXISTS pets;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    has_onboarded BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE pets (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    species TEXT NOT NULL,
    breed TEXT NOT NULL,
    age INTEGER NOT NULL,
    medical_history TEXT,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE chats (
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    pet_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (pet_id) REFERENCES pets (id)
);

CREATE TABLE chat_images (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    upload_timestamp TEXT NOT NULL,
    FOREIGN KEY (chat_id) REFERENCES chats (id)
);
