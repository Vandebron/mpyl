pipeline {
    agent { node { label 'jenkins-test-dind-agent' } }
    options {
        ansiColor('xterm')
    }
    parameters {
        string(name: 'BUILD_PARAMS', defaultValue: '', description: 'Build parameters passed along with the run. Example: --help or --all')
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
                GITHUB_TOKEN = credentials('github-pat-mpyl-vandebronjenkins')
            }
            steps {
                script {
                    withKubeConfig([credentialsId: 'jenkins-rancher-service-account-kubeconfig-test']) {
                    withCredentials([file(credentialsId: '4bee8d6f-6180-4b28-89e3-8cbfc2b9e8b8', variable: 'PIPELINEKEY')]) {
                        def privateKey = sh(script: "cat $PIPELINEKEY", returnStdout: true)
                        writeFile(file: 'mpyl-pipeline.2023-02-20.private-key.pem', text: privateKey)
                        sh "pipenv install --index https://test.pypi.org/simple/ 'mpyl==$CHANGE_ID.*'"
                        sh "pipenv install -d --skip-lock"
                        sh "pipenv run run-ci ${params.BUILD_PARAMS}"
                    }
                }}
            }
        }
    }
}