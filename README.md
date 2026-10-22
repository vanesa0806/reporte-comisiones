Aquí tienes la propuesta completa para el archivo **`README.md`**, redactada de forma estructurada, profesional y lista para ser integrada en tu repositorio.

---

# 🚀 Guía de Despliegue CI/CD: Azure, Jenkins, Docker y GitHub Webhook

Este proyecto documenta el proceso paso a paso para la infraestructura y automatización de un pipeline CI/CD de cálculo de comisiones. Incluye la creación de la máquina virtual en **Azure**, la instalación y configuración de **Jenkins** sobre **Docker**, el registro de un agente de ejecución (`azure_agent`), la integración con **GitHub** mediante **Webhooks** y las pruebas de ejecuciones automáticas.

---

## 📋 Tabla de Contenidos

1. [Creación de la Máquina Virtual en Azure]
2. [Configuración Inicial de Jenkins]
3. [Configuración del Agente (`azure_agent`)]
4. [Estructura del Proyecto y Repositorio GitHub]
5. [Configuración del Pipeline en Jenkins]
6. [Configuración del Webhook en GitHub]
7. [Pruebas de Ejecución CI/CD Automática]

---

## 1. Creación de la Máquina Virtual en Azure

Para desplegar la infraestructura en Azure se ejecuta el script automatizado en Bash.

### 🛠️ Características de la Infraestructura

* **OS:** Ubuntu 22.04 LTS.
* **Tamaño:** `Standard_B2s` (2 vCPU, 4GB RAM).
* **Puertos Abiertos (NSG):** `22` (SSH) y `80` (Jenkins Web).
* **Entorno de Contenedores:** Docker CE + Docker Compose Plugin + Java 21 OpenJDK.
* **Jenkins:** Imagen `jenkins/jenkins:2.574-slim-jdk21` corriendo en puerto 80 mediante Docker Compose.

### 📜 Script de Despliegue

Ejecuta el siguiente script en la CLI de Azure:

```bash
#!/bin/bash

# =======================================================
# Script de Despliegue de Laboratorio Azure
# Docker + Jenkins v2.574 (JDK 21) en Puerto 80
# =======================================================

echo "--------------------------------------------------------"
echo "  Despliegue de Laboratorio Azure: Docker + Jenkins v2.574"
echo "--------------------------------------------------------"

# 1. Solicitar iniciales y sanitizar texto
read -p "Ingresa las iniciales del estudiante (ej. jmd): " RAW_INITIALS
INITIALS=$(echo "$RAW_INITIALS" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9')

if [ -z "$INITIALS" ]; then
    echo "Error: Debes ingresar al menos una inicial válida."
    exit 1
fi

# 2. Variables de entorno
LOCATION="eastus"
RESOURCE_GROUP="rg-lab-$INITIALS"
VM_NAME="vm-jenkins-$INITIALS"
ADMIN_USER="azureuser"
VM_SIZE="Standard_B2s"             # 2 vCPU, 4GB RAM

# 3. Generar contraseña segura de 20 caracteres
ADMIN_PASSWORD=$(tr -dc 'A-Za-z0-9@#%*+=-_' < /dev/urandom | head -c 20)

echo ""
echo "Configuración asignada:"
echo " - Grupo de Recursos: $RESOURCE_GROUP"
echo " - Nombre de la VM:   $VM_NAME"
echo " - Región de Azure:   $LOCATION"
echo " - Tamaño de la VM:   $VM_SIZE"
echo ""

# 4. Crear Grupo de Recursos y Máquina Virtual
echo "--> [1/4] Creando Grupo de Recursos '$RESOURCE_GROUP'..."
az group create --name $RESOURCE_GROUP --location $LOCATION --output table

echo ""
echo "--> [2/4] Creando Máquina Virtual Ubuntu 22.04..."
az vm create \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --image Ubuntu2204 \
  --size $VM_SIZE \
  --admin-username $ADMIN_USER \
  --admin-password "$ADMIN_PASSWORD" \
  --authentication-type password \
  --public-ip-sku Standard \
  --output table

echo ""
echo "--> [3/4] Apertura de puertos en el Network Security Group (22 SSH, 80 Jenkins Web)..."
az vm open-port --resource-group $RESOURCE_GROUP --name $VM_NAME --port 22 --priority 1001 --output table
az vm open-port --resource-group $RESOURCE_GROUP --name $VM_NAME --port 80 --priority 1002 --output table

# 5. Ejecutar script de instalación con Java 21 y Jenkins 2.574
echo ""
echo "--> [4/4] Instalando Java 21, Docker y Jenkins v2.574 (espera ~2 minutos)..."

INSTALL_SCRIPT=$(cat << 'EOF'
export DEBIAN_FRONTEND=noninteractive

# Esperar a que los bloqueos iniciales de APT se liberen
while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do sleep 5; done

# 1. Desinstalar dependencias antiguas
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do 
  apt-get remove -y $pkg
done

# 2. Configurar repositorio oficial de Docker e instalar Java 21
apt-get update -qq
apt-get install -y -qq ca-certificates curl openjdk-21-jdk git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -qq
apt-get -y -qq install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 3. Configurar usuario y habilitar servicios
groupadd -f docker
usermod -aG docker azureuser
systemctl enable docker.service
systemctl enable containerd.service

# 4. Crear estructura y docker-compose.yml con Jenkins v2.574 y JDK 21
mkdir -p /home/azureuser/jenkins
cat << 'DOCKER_COMPOSE' > /home/azureuser/jenkins/docker-compose.yml
services:
  jenkins:
    container_name: jenkins
    image: jenkins/jenkins:2.574-slim-jdk21
    restart: unless-stopped
    ports:
      - 80:8080
    volumes:
      - jenkins_home:/var/jenkins_home/
volumes:
  jenkins_home:
DOCKER_COMPOSE

chown -R azureuser:azureuser /home/azureuser/jenkins

# 5. Levantar el contenedor
cd /home/azureuser/jenkins
docker compose up -d
EOF
)

az vm run-command invoke \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --command-id RunShellScript \
  --scripts "$INSTALL_SCRIPT" \
  --output table

# 6. Obtener la IP pública
PUBLIC_IP=$(az vm show -d -g $RESOURCE_GROUP -n $VM_NAME --query publicIps -o tsv)

echo ""
echo "=========================================================="
echo " ¡Despliegue Finalizado con Éxito!"
echo "=========================================================="
echo "  CREDENCIALES VM / SSH:"
echo "    - Usuario:     $ADMIN_USER"
echo "    - Contraseña:  $ADMIN_PASSWORD"
echo "    - Conexión:    ssh $ADMIN_USER@$PUBLIC_IP"
echo ""
echo "  ACCESO A JENKINS v2.574 (Puerto 80):"
echo "    - URL Web:     http://$PUBLIC_IP"
echo "    - URL WebHook: http://$PUBLIC_IP/github-webhook/"
echo ""
echo "  OBTENER CLAVE INICIAL DE JENKINS:"
echo "    ssh $ADMIN_USER@$PUBLIC_IP 'sudo docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword'"
echo "=========================================================="

```

### 🔑 Obtención de Clave Inicial de Jenkins

Una vez finalizada la instalación automatizada, recupera la clave de administrador SSH:

```bash
ssh azureuser@<IP_PUBLICA_VM> 'sudo docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword'

```

---

## 2. Configuración Inicial de Jenkins

1. Ingresa desde el navegador web a la IP pública de tu servidor:
`http://<IP_PUBLICA_VM>`
2. Pega el **contraseña inicial de administrador** obtenida en el paso anterior.
3. Selecciona **Install suggested plugins** (Instalar plugins recomendados).
4. Crea el primer usuario administrador y finaliza la configuración inicial.

---

## 3. Configuración del Agente (`azure_agent`)

Para aislar las ejecuciones del máster de Jenkins, configuraremos un agente dedicado llamado `azure_agent`.

1. Ve a **Administrar Jenkins** (*Manage Jenkins*) $\rightarrow$ **Nodos** (*Nodes / Agents*).
2. Haz clic en **Nuevo Nodo** (*New Node*):
* **Nombre del nodo:** `azure_agent`
* **Tipo:** *Permanent Agent*


3. Configura las propiedades del nodo:
* **Número de ejecutores:** `2`
* **Directorio raíz remoto:** `/home/azureuser/jenkins`
* **Etiquetas (*Labels*):** `azure_agent`
* **Método de lanzamiento:** *Launch agents via SSH* o *Launch agent by connecting it to the controller*.


4. Guarda y verifica que el nodo esté en estado **En línea** (*Online*).

---

## 4. Estructura del Proyecto y Repositorio GitHub

El código fuente de la aplicación y la canalización se alojan en GitHub:

`[https://github.com/xxxxxxxxxx/repositorio.git](https://github.com/xxxxxxxxxx/repositorio.git)`

### 📂 Estructura del Repositorio

```text
├── app/
│   ├── ComisionEmpleados_V1_202607.csv
│   ├── config.json
│   ├── main.py
│   └── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── Jenkinsfile
└── README.md

```

### 📄 Jenkinsfile

```groovy
pipeline {
    agent {
        label 'azure_agent'
    }

    environment {
        COMPOSE_PROJECT_NAME = 'reporte_comisiones'
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {
        stage('1. Preparar Entorno') {
            steps {
                echo "> Validando herramientas"
                sh 'docker --version'
                sh 'docker compose version'
            }
        }

        stage('2. Construir Imagen Docker') {
            steps {
                echo "> Construyendo la imagen de la aplicación"
                sh 'docker compose -p ${COMPOSE_PROJECT_NAME} build --no-cache'
            }
        }
        
        stage('3. Ejecutar Cálculo y Envío de Reporte') {
            steps {
                echo "> Ejecutando proceso dentro del contenedor"
                sh 'docker compose -p ${COMPOSE_PROJECT_NAME} up --abort-on-container-exit --exit-code-from app'
            }
        }
    }

    post {
        always {
            echo "> Limpieza de recursos y contenedores"
            sh 'docker compose -p ${COMPOSE_PROJECT_NAME} down --volumes --remove-orphans || true'
        }
        success {
            echo 'El reporte fue generado y enviado exitosamente.'
        }
        failure {
            echo 'Ocurrió un error durante la ejecución del proceso.'
        }
    }
}

```

---

## 5. Configuración del Pipeline en Jenkins

1. En el panel principal de Jenkins, haz clic en **Nueva Tarea** (*New Item*).
2. Ingresa el nombre del Job (ej. `pipeline-git`) y selecciona **Pipeline**.
3. En la sección **Configuración**:
* Activa la casilla **GitHub hook trigger for GSoC SCM polling**.


4. En la sección **Pipeline**:
* **Definition:** `Pipeline script from SCM`
* **SCM:** `Git`
* **Repository URL:** `[https://github.com/xxxxxxxxxx/repositorio.git](https://github.com/xxxxxxxxxx/repositorio.git)`
* **Branch Specifier:** `*/main`
* **Script Path:** `Jenkinsfile`


5. Haz clic en **Guardar**.

---

## 6. Configuración del Webhook en GitHub

Para que cada `git push` dispare automáticamente la ejecución en Jenkins:

1. Ve a tu repositorio en GitHub $\rightarrow$ **Settings** $\rightarrow$ **Webhooks**.
2. Haz clic en **Add webhook**.
3. Configura los valores:
* **Payload URL:** `http://<IP_PUBLICA_VM>/github-webhook/`
* **Content type:** `application/json`
* **Secret:** (Dejar en blanco si no se configuró en Jenkins)
* **Which events would you like to trigger this webhook?:** *Just the push event*.


4. Haz clic en **Add webhook** y confirma el check verde de entrega correcta.

---

## 7. Pruebas de Ejecución CI/CD Automática

### Pasos para probar la automatización:

1. Realiza una modificación local en el código (ej. actualiza el `README.md` o `main.py`).
2. Envía los cambios al repositorio remoto:
```bash
git add .
git commit -m "ci: prueba de ejecucion automatica via webhook"
git push origin main

```



### Verificación del Pipeline:

* GitHub enviará una petición POST HTTP al endpoint `/github-webhook/` de Jenkins.
* Jenkins iniciará inmediatamente la construcción (ej. `Build #3`).
* **Verificación de logs de salida esperada:**

```text
Started by GitHub push by xxxxxxxxxx
Obtained Jenkinsfile from git https://github.com/xxxxxxxxxx/repositorio.git
Running on azure_agent in /home/azureuser/jenkins/workspace/pipeline-git

[Stage 1. Preparar Entorno]
> Validando herramientas (Docker y Docker Compose)
Docker version 29.6.2
Docker Compose version v5.3.1

[Stage 2. Construir Imagen Docker]
> Building image reporte_comisiones-app...
Successfully tagged reporte_comisiones-app:latest

[Stage 3. Ejecutar Cálculo y Envío de Reporte]
> Ejecutando app/main.py dentro del contenedor...

[Declarative: Post Actions]
> Limpieza de recursos y contenedores
El reporte fue generado y enviado exitosamente.
Finished: SUCCESS

```# reporte-comisiones
