pipeline {
    agent { node { label 'mpyl-dind-agent' } }
    options {
        ansiColor('xterm')
    }
    environment {
        DOCKER_REGISTRY = credentials('91751de6-20aa-4b12-8459-6e16094a233a')
        GIT_CREDENTIALS = credentials('e8bc2c24-e461-4dae-9122-e8ae8bd7ec07')
        GITHUB_TOKEN = credentials('github-pat-mpyl-vandebronjenkins')
        MPYL_GITHUB_APP_PRIVATE_KEY = credentials('mpyl_pipeline_github_app_private_key')
        SLACK_TOKEN = credentials('JENKINS_MPYL_APP_OAUTH_TOKEN')
        MPYL_JIRA_TOKEN = credentials('MPYL_JIRA_TOKEN')
        AWS_ECR_ACCESS_KEY_ID = credentials('AWS_ECR_ACCESS_KEY_ID')
        AWS_ECR_SECRET_ACCESS_KEY = credentials('AWS_ECR_SECRET_ACCESS_KEY')
        SOME_CREDENTIAL = 'some-credential'
    }
    stages {
        stage('Initialize Parameters') {
            when { expression { return params.BUILD_PARAMS == null || params.BUILD_PARAMS == ""  } }
            steps {
                script {
                    properties([parameters([
                        string(name: 'BUILD_PARAMS', defaultValue: '--all', description: 'Build parameters passed along with the run. Example: --help or --all'),
                        string(name: 'MPYL_CONFIG_BRANCH', defaultValue: 'main', description: 'Branch to use for mpyl_config repository'),
                        booleanParam(name: 'MANUAL_BUILD', defaultValue: false, description: 'Enable manual project selection in the initialize phase'),
                    ])])
                    currentBuild.result = 'NOT_BUILT'
                    currentBuild.description = "Parameters can be set now"
                    currentBuild.displayName = "#${BUILD_NUMBER}-(Parameter load)"
                    echo("The build parameters have been created. Ready for real build.")
                    currentBuild.getRawBuild().getExecutor().interrupt(Result.NOT_BUILT)
                    sleep(1)
                }
            }
        }
        stage('Initialize MPyL') {
            steps {
                script {
                    def content = sh(script: "curl -s https://api.github.com/repos/Vandebron/mpyl_config/contents/mpyl_config.yml?ref=$MPYL_CONFIG_BRANCH -H 'Authorization: token $GIT_CREDENTIALS_PSW' -H 'Accept: application/vnd.github.v3.raw'", returnStdout: true)
                    writeFile(file: 'mpyl_config.yml', text: content)
                    withKubeConfig([credentialsId: 'jenkins-rancher-service-account-kubeconfig-test']) {
                        wrap([$class: 'BuildUser']) {
                            sh "pipenv clean"
                            sh "pipenv install --ignore-pipfile --skip-lock --site-packages --index https://test.pypi.org/simple/ 'mpyl==$CHANGE_ID.*'"
                            sh "pipenv install -d --skip-lock"
                            sh "pipenv run mpyl version"
                            sh "pipenv run mpyl health --ci --upgrade"
                            sh "pipenv run mpyl projects lint"
                            sh "pipenv run mpyl projects upgrade"
                            sh "pipenv run mpyl repo status"
                            sh "pipenv run mpyl repo init"
                            env.SELECTED_PROJECTS = ""
                            if (params.MANUAL_BUILD) {
                                def projects = sh(script: "pipenv run mpyl projects names", returnStdout: true)
                                def boolParams = projects.split('\n').collect { project ->
                                    booleanParam(name: project, defaultValue: false)
                                }
                                def selectedProjects = input(id: 'userInput', message: 'Select project(s)', parameters: boolParams)
                                def selectedProjectsString = selectedProjects.findAll { key, value -> value }.keySet().join(',')
                                env.SELECTED_PROJECTS = "--projects " + selectedProjectsString
                            }
                            sh "pipenv run mpyl build status ${env.SELECTED_PROJECTS} ${(env.BUILD_PARAMS.contains("--all")) ? "--all" : ""}"
                            sh "pipenv run start-github-status-check"
                        }
                    }
                }
            }
        }
        stage('Build') {
            steps {
                wrap([$class: 'BuildUser']) {
                    sh "pipenv run mpyl build run --ci --stage build ${params.BUILD_PARAMS} ${env.SELECTED_PROJECTS}"
                }
            }
        }
        stage('Test') {
            steps {
                wrap([$class: 'BuildUser']) {
                    sh "pipenv run mpyl build run --ci --stage test --sequential ${params.BUILD_PARAMS} ${env.SELECTED_PROJECTS}"
                }
            }
        }
        stage('Deploy') {
            steps {
                withKubeConfig([credentialsId: 'jenkins-rancher-service-account-kubeconfig-test']) {
                    wrap([$class: 'BuildUser']) {
                        sh "pipenv run mpyl build run --ci --stage deploy --sequential ${params.BUILD_PARAMS} ${env.SELECTED_PROJECTS}"
                    }
                }
            }
        }
        stage('Post Deploy') {
            steps {
                withKubeConfig([credentialsId: 'jenkins-rancher-service-account-kubeconfig-test']) {
                    wrap([$class: 'BuildUser']) {
                        sh "pipenv run mpyl build run --ci --stage postdeploy --sequential ${params.BUILD_PARAMS} ${env.SELECTED_PROJECTS}"
                    }
                }
            }
        }
        stage("Report") {
            steps {
                wrap([$class: 'BuildUser']) {
                    sh "pipenv run report"
                }
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
