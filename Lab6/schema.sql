CREATE DATABASE IF NOT EXISTS filemanager
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE filemanager;

CREATE TABLE IF NOT EXISTS users (
    id             INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username       VARCHAR(50)  NOT NULL UNIQUE,
    password       VARCHAR(256) NOT NULL,
    remember_token VARCHAR(64)  DEFAULT NULL,
    token_expires  DATETIME     DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS files (
    id            INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    filename      VARCHAR(255) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    user_id       INT          NOT NULL,
    uploaded_at   DATETIME     NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
