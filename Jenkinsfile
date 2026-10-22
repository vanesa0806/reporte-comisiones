pipeline {
    agent {
		label 'azure_agent'
	}

    environment {
        // Variables de entorno para el proceso
        IMAGE_NAME = 'tst_calculo_app'
        COMPOSE_PROJECT_NAME = 'reporte_comisiones'
    }

    options {
        // Limpia ejecuciones antiguas y establece tiempo límite
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        
        // NOTA: Si instalas el plugin "AnsiColor", descomenta la siguiente línea:
        // ansiColor('xterm')
    }

    stages {
        stage('1. Preparar Entorno') {
            steps {
                echo "--------------------------------------------------"
                echo "> Validando herramientas (Docker y Docker Compose)"
                echo "--------------------------------------------------"
                sh 'docker --version'
                sh 'docker compose version'
            }
        }

        stage('2. Construir Imagen Docker') {
            steps {
                echo "--------------------------------------------------"
                echo "> Construyendo la imagen con las dependencias Python"
                echo "--------------------------------------------------"
                sh 'docker compose -p ${COMPOSE_PROJECT_NAME} build --no-cache'
            }
        }
        
		stage('3. Ejecutar Cálculo y Envío de Reporte') {
			steps {
				echo "--------------------------------------------------"
				echo "> Ejecutando app/main.py dentro del contenedor"
				echo "--------------------------------------------------"
				// Cambiamos 'calculo_app' por 'app'
				sh 'docker compose -p ${COMPOSE_PROJECT_NAME} up --abort-on-container-exit --exit-code-from app'
			}
		}
    }

    post {
        always {
            echo "--------------------------------------------------"
            echo "> Limpieza de recursos y contenedores"
            echo "--------------------------------------------------"
            sh 'docker compose down --volumes --remove-orphans || true'
        }
        success {
            echo 'El reporte fue generado y enviado exitosamente por correo.'
        }
        failure {
            echo 'Ocurrió un error durante la ejecución del reporte o envío del correo.'
        }
    }
}