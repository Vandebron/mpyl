pipeline {
    agent { node { label 'mpyl-dind-agent' } }
    options {
        ansiColor('xterm')
    }
    parameters {
        string(name: 'BUILD_PARAMS', defaultValue: '--all', description: 'Build parameters passed along with the run. Example: --help or --all')
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
                MPYL_GITHUB_APP_PRIVATE_KEY = credentials('mpyl_pipeline_github_app_private_key')
                SLACK_TOKEN = credentials('JENKINS_MPYL_APP_OAUTH_TOKEN')
                JIRA_USER_PASSWORD = credentials('JIRA_USER_PASSWORD')
            }
            steps {
                script {
                    withKubeConfig([credentialsId: 'jenkins-rancher-service-account-kubeconfig-test']) {
                    wrap([$class: 'BuildUser']) {
                        sh "pipenv clean"
                        sh "pipenv install --index https://test.pypi.org/simple/ 'mpyl==$CHANGE_ID.*'"
                        sh "pipenv install -d --skip-lock"
                        sh "pipenv requirements"
                        sh "pipenv run run-ci ${params.BUILD_PARAMS}"
                    }
                }}
            }
        }
    }
    post {
        always {
            script {
                def testResults = findFiles(glob: "tests/projects/**/*test*/*.xml")
                for (xml in testResults) {
                    touch xml.getPath()
                    junit "${xml.getPath()}"
                }
            }
        }
    }
}