#!/bin/sh

docker-compose --env-file .env.prod -f docker-compose.prod.yml down
docker-compose --env-file .env.prod -f docker-compose.prod.yml up -d --build