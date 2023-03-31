""" Utilities to construct spark application yaml """


def to_spark_body(spark: dict[str, str]) -> dict:
    static_body = {
        'type': 'Scala',
        'mode': 'cluster',
        'imagePullPolicy': 'Always',
        'sparkVersion': '3.1.1',
        'restartPolicy': {
            'type': 'Never'
        },
        'sparkConfigMap': 'release-name-log4j',
        'image': 'bigdataregistry.azurecr.io/send-slack-notification:PR-1231',
        'arguments': [
            1
        ],
        'driver': {
            'cores': 1,
            'coreLimit': '1200m',
            'memory': '5G',
            'memoryOverhead': '1024',
            'labels': {
                'version': '3.1.1'
            },
            'serviceAccount': 'release-name-job',
            'envVars': {
                'DA_SLACK_BOT_TOKEN': 'xoxb-65778094515-2212272125044-E7qttf3XLQi2vaL0dGkBstLD',
                'DEPLOY_ENV': 'test'
            },
            'envSecretKeyRefs': None
        },
        'executor': {
            'cores': 1,
            'instances': 1,
            'memory': '3G',
            'memoryOverhead': '2048',
            'labels': {
                'version': '3.1.1'
            },
            'envVars': {
                'DA_SLACK_BOT_TOKEN': 'xoxb-65778094515-2212272125044-E7qttf3XLQi2vaL0dGkBstLD',
                'DEPLOY_ENV': 'test'
            },
            'envSecretKeyRefs': None
        },
        'deps': {
            'jars': [
                # pylint: disable-next=line-too-long
                'https://repo1.maven.org/maven2/com/microsoft/sqlserver/mssql-jdbc/11.2.1.jre8/mssql-jdbc-11.2.1.jre8.jar'
            ]
        },
        'sparkConf': {
            'spark.driver.extraClassPath': 'mssql-jdbc-11.2.1.jre8.jar',
            'spark.executor.extraClassPath': 'mssql-jdbc-11.2.1.jre8.jar',
            'spark.sql.legacy.timeParserPolicy': 'LEGACY',
            'spark.sql.broadcastTimeout': '600'}
    }

    return static_body | spark
