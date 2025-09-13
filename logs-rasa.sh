#!/bin/bash
if [ -z "$1" ]; then
    echo "📋 Servicios disponibles:"
    echo "   - rasa-server"
    echo "   - rasa-action-server"
    echo "   - postgres" 
    echo "   - portainer"
    echo ""
    echo "Uso: ./logs-rasa.sh [servicio]"
    echo "Para todos: ./logs-rasa.sh all"
else
    if [ "$1" = "all" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$1"
    fi
fi
