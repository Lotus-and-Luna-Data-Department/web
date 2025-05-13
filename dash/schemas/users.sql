CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  approved BOOLEAN NOT NULL DEFAULT FALSE,
  role TEXT NOT NULL  /* e.g. 'admin' or 'user' */
);
