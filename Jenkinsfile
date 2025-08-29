pipeline {
  agent any
  environment {
    DOCKER_IMAGE = "sivaranjanimahendhiren/gamutgurus_todo_app"
    DEPLOY_USER  = "ec2-user"
    DEPLOY_HOST  = "65.0.179.188"
  }
  options { timestamps() }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Test') {
      steps {
        sh '''
          echo "=== Running Python tests ==="
          python3 -m venv .venv
          . .venv/bin/activate
          pip install --upgrade pip
          pip install -r requirements.txt
          flake8 || true
          pytest -q || true
        '''
      }
    }

    stage('Build Docker Image') {
      steps {
        sh '''
          echo "=== Building Docker Image ==="
          docker build -t ${DOCKER_IMAGE}:${BUILD_NUMBER} -t ${DOCKER_IMAGE}:latest .
        '''
      }
    }

    stage('Push to Docker Hub') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          sh '''
            echo "=== Logging in to DockerHub ==="
            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
            echo "=== Pushing Image to DockerHub ==="
            docker push ${DOCKER_IMAGE}:${BUILD_NUMBER}
            docker push ${DOCKER_IMAGE}:latest
          '''
        }
      }
    }

    stage('Deploy to EC2') {
      steps {
        sshagent(credentials: ['ec2-key']) {
          withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
            sh """
              echo "=== Deploying on EC2 ==="
              ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_HOST} /bin/bash -lc '
                set -e
                echo "\$DOCKER_PASS" | sudo docker login -u "\$DOCKER_USER" --password-stdin || true
                sudo docker pull ${DOCKER_IMAGE}:${BUILD_NUMBER}
                sudo docker rm -f todo-app || true
                sudo docker run -d --name todo-app -p 80:5000 --restart unless-stopped ${DOCKER_IMAGE}:${BUILD_NUMBER}
                curl -fsS http://localhost/healthz || (echo "Health check failed" && exit 1)
              '
            """
          }
        }
      }
    }
  }

  post {
    success { echo "🎉 Successfully deployed ${DOCKER_IMAGE}:${BUILD_NUMBER} to ${DEPLOY_HOST}" }
    failure { echo "❌ Pipeline failed. Check logs." }
  }
}
