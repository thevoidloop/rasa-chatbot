#!/bin/bash
echo "🚀 Iniciando servicios RASA con Portainer..."

# Verificar Docker
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker no está ejecutándose"
    exit 1
fi

# Iniciar servicios
docker compose up -d

echo "⏳ Esperando que los servicios estén listos..."
sleep 15

# Mostrar estado
echo ""
echo "📊 Estado de servicios:"
docker compose ps

echo ""
echo "✅ Servicios iniciados correctamente!"
echo ""
echo "🔗 Accesos disponibles:"
echo "   📊 Portainer:     https://localhost:9443 (HTTPS - recomendado)"
echo "   📊 Portainer:     http://localhost:9000  (HTTP - alternativo)"  
echo "   🤖 RASA API:      http://localhost:5005"
echo "   ⚙️  Action Server: http://localhost:5055/health"
echo ""
echo "💡 Tip: En Portainer, ve a 'Containers' para gestionar tus servicios"
