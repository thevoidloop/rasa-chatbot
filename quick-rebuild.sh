#!/bin/bash

# quick-rebuild.sh - Reconstrucción rápida para desarrollo
# Solo para cambios de código, mantiene datos de BD si es posible

set -e

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🔄 Reconstrucción rápida RASA Chatbot${NC}"
echo ""

# Opción de preservar base de datos
echo -e "${YELLOW}¿Quieres preservar los datos de la base de datos? (y/n):${NC}"
read -r preserve_db

echo -e "${BLUE}📦 Deteniendo servicios...${NC}"
docker compose down

if [[ $preserve_db =~ ^[Nn]$ ]]; then
    echo -e "${BLUE}🗑️  Eliminando volúmenes...${NC}"
    docker compose down -v
    docker volume prune -f
fi

echo -e "${BLUE}🔨 Reconstruyendo imágenes...${NC}"
docker compose build --no-cache

echo -e "${BLUE}🚀 Iniciando servicios...${NC}"
docker compose up -d

echo -e "${BLUE}⏳ Esperando servicios...${NC}"
sleep 20

echo ""
echo -e "${GREEN}✅ Reconstrucción completada${NC}"
echo ""
echo "📊 Estado:"
docker compose ps

echo ""
echo "🔗 Accesos:"
echo "   Portainer: https://localhost:9443"
echo "   RASA API:  http://localhost:5005"
echo ""

# Test rápido
echo -e "${BLUE}🧪 Probando API...${NC}"
sleep 5
if curl -s http://localhost:5005/version >/dev/null 2>&1; then
    echo -e "${GREEN}✅ API funcionando${NC}"
else
    echo -e "${YELLOW}⚠️  API aún iniciando...${NC}"
fi