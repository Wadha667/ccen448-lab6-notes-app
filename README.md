# Lab 6 Notes App

A small dynamic website: user registration and login (server-side, hashed passwords) with private notes stored in PostgreSQL. Built with Flask and Docker Compose for CCEN 448 Lab 6.

## Run
    sudo docker compose up -d --build

Open `http://SERVER_IP:8000`. Optional: set `DB_PASSWORD` and `SECRET_KEY` in a `.env` file first.

## Inspect the database
    sudo docker compose exec db psql -U notes -d notes -c "SELECT id, username FROM users;"

## Stop
    sudo docker compose down
