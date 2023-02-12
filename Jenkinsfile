pipeline {
    agent { node { label 'jenkins-test-dind-agent' } }
    options {
        ansiColor('xterm')
    }
    stages {
        stage('Initialise') {
            steps {
                checkout scm
            }
        }
        stage('Build') {
           environment {
                DOCKER_REGISTRY = credentials('91751de6-20aa-4b12-8459-6e16094a233a')
            }
            steps {
                script {
                    withKubeConfig([credentialsId: 'jenkins-rancher-service-account-kubeconfig-test']) {
                        echo "Running dagster..."
                        sh "pipenv install -d --skip-lock"
                        sh "pipenv run run"
                    }
                }
            }
        }
    }
}