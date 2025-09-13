# 🐳 Portainer para RASA Chatbot

## Inicio Rápido

```bash
# Iniciar servicios
./start-rasa.sh

# Acceder a Portainer
# HTTPS: https://localhost:9443 (recomendado)
# HTTP:  http://localhost:9000
```

## Primera Configuración de Portainer

1. Accede a https://localhost:9443
2. **Acepta el certificado auto-firmado** (es normal en desarrollo)
3. Crea una cuenta de administrador:
   - Usuario: admin (o el que prefieras)
   - Contraseña: mínimo 12 caracteres
4. Selecciona **"Get Started"**
5. Elige **"Docker"** como entorno
6. ¡Ya puedes gestionar tus contenedores!

## Funciones Principales en Portainer

### 📦 Containers
- Ver estado de todos los contenedores
- Iniciar/detener/reiniciar contenedores
- Ver estadísticas de recursos
- Acceder a logs en tiempo real
- Abrir terminal dentro de contenedores

### 📊 Images  
- Ver todas las imágenes Docker
- Construir nuevas imágenes
- Eliminar imágenes no utilizadas

### 💾 Volumes
- Gestionar volúmenes de datos
- Ver uso de espacio
- Hacer backup de volúmenes

### 🌐 Networks
- Ver redes Docker
- Configurar conectividad entre contenedores

## Comandos Útiles

```bash
# Ver estado de servicios
docker-compose ps

# Ver logs de servicio específico
./logs-rasa.sh rasa-server

# Detener servicios
./stop-rasa.sh

# Ver todos los logs
./logs-rasa.sh all
```

## Puertos Utilizados

- **5005**: RASA API Server
- **5055**: RASA Action Server  
- **5432**: PostgreSQL
- **9000**: Portainer (HTTP)
- **9443**: Portainer (HTTPS)

## Solución de Problemas

### Portainer no carga
- Verifica que el puerto no esté ocupado: `sudo netstat -tulpn | grep 9443`
- Acepta el certificado auto-firmado en tu navegador

### Contenedores no aparecen
- Verifica que Docker esté ejecutándose: `docker info`
- Reinicia Portainer: `docker-compose restart portainer`

### Error de permisos
```bash
# Agregar usuario al grupo docker
sudo usermod -aG docker $USER
# Reiniciar sesión
```
