"""
This module contains the Spark job CRD class.
"""
from typing import Optional

from kubernetes.client import V1ObjectMeta

from .. import CustomResourceDefinition


def to_spark_body(
    project_name: str,
    env_vars: dict,
    spark: dict,
    image: str,
    command: Optional[list[str]],
    env_secret_key_refs: dict,
    num_replicas: int,
) -> dict:
    static_body = {
        "type": "Scala",
        "mode": "cluster",
        "imagePullPolicy": "Always",
        "sparkVersion": "3.1.1",
        "restartPolicy": {"type": "Never"},
        "sparkConfigMap": project_name,
        "image": image,
        "driver": {
            "cores": 1,
            "coreLimit": "1200m",
            "memory": "5G",
            "memoryOverhead": "1024",
            "labels": {"version": "3.1.1"},
            "serviceAccount": project_name,
            "envVars": env_vars,
            "envSecretKeyRefs": env_secret_key_refs,
        },
        "executor": {
            "cores": 1,
            "instances": num_replicas,
            "memory": "3G",
            "memoryOverhead": "2048",
            "labels": {"version": "3.1.1"},
            "envVars": env_vars,
            "envSecretKeyRefs": env_secret_key_refs,
        },
        "deps": {
            "jars": [
                "https://repo1.maven.org/maven2/com/microsoft/sqlserver/"
                "mssql-jdbc/11.2.1.jre8/mssql-jdbc-11.2.1.jre8.jar"
            ]
        },
        "sparkConf": {
            "spark.driver.extraClassPath": "mssql-jdbc-11.2.1.jre8.jar",
            "spark.executor.extraClassPath": "mssql-jdbc-11.2.1.jre8.jar",
            "spark.sql.legacy.timeParserPolicy": "LEGACY",
            "spark.sql.broadcastTimeout": "600",
        },
    } | ({"arguments": command} if command else {})

    return static_body | spark


def get_spark_config_map_data() -> dict:
    return {
        "log4j.properties": "#\n"
        "# Licensed to the Apache Software Foundation (ASF) under one or more\n"
        "# contributor license agreements.  See the NOTICE file distributed with\n"
        "# this work for additional information regarding copyright ownership.\n"
        "# The ASF licenses this file to You under the Apache License, Version 2.0\n"
        '# (the "License"); you may not use this file except in compliance with\n'
        "# the License.  You may obtain a copy of the License at\n"
        "#\n"
        "#    http://www.apache.org/licenses/LICENSE-2.0\n"
        "#\n"
        "# Unless required by applicable law or agreed to in writing, software\n"
        '# distributed under the License is distributed on an "AS IS" BASIS,\n'
        "# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n"
        "# See the License for the specific language governing permissions and\n"
        "# limitations under the License.\n"
        "#\n"
        "#log everything to file at the beginning\n"
        "log4j.rootCategory=INFO, console, sparklog\n"
        "#afterwards log only our messages to the console\n"
        "log4j.logger.nl.vandebron.sparkplug=INFO, console\n"
        "#configure ConsoleAppender\n"
        "log4j.appender.console=org.apache.log4j.ConsoleAppender\n"
        "log4j.appender.console.target=System.out\n"
        "log4j.appender.console.layout=org.apache.log4j.PatternLayout\n"
        "log4j.appender.console.layout.ConversionPattern=%d{yy/MM/dd HH:mm:ss} %p %c{1}: %m%n\n"
        "log4j.appender.sparklog=org.apache.log4j.FileAppender\n"
        "#this must be overwritten programmatically when setting the appender\n"
        "log4j.appender.sparklog.File=/dev/null\n"
        "log4j.appender.sparklog.layout=org.apache.log4j.PatternLayout\n"
        "log4j.appender.sparklog.layout.ConversionPattern=%d %-5p [%c{1}] %m%n\n"
        "log4j.appender.sparklog.Threshold=INFO\n"
        "log4j.appender.sparklog.Append=true\n"
        "# Set the default spark-shell log level to WARN. When running the spark-shell, the\n"
        "# log level for this class is used to overwrite the root logger's log level, so that\n"
        "# the user can have different defaults for the shell and regular Spark apps.\n"
        "log4j.logger.org.apache.spark.repl.Main=WARN\n"
        "# Settings to quiet third party logs that are too verbose\n"
        "log4j.logger.org.spark_project.jetty=WARN\n"
        "log4j.logger.org.spark_project.jetty.util.component.AbstractLifeCycle=ERROR\n"
        "log4j.logger.org.apache.spark.repl.SparkIMain$exprTyper=INFO\n"
        "log4j.logger.org.apache.spark.repl.SparkILoop$SparkILoopInterpreter=INFO\n"
        "log4j.logger.org.apache.parquet=ERROR\n"
        "log4j.logger.parquet=ERROR\n"
        "# SPARK-9183: Settings to avoid annoying messages when looking up "
        "nonexistent UDFs in SparkSQL with Hive support\n"
        "log4j.logger.org.apache.hadoop.hive.metastore.RetryingHMSHandler=FATAL\n"
        "log4j.logger.org.apache.hadoop.hive.ql.exec.FunctionRegistry=ERROR",
    }


class V1SparkApplication(CustomResourceDefinition):
    def __init__(self, metadata: V1ObjectMeta, schedule: Optional[str], body: dict):
        if schedule:
            super().__init__(
                api_version="sparkoperator.k8s.io/v1beta2",
                kind="ScheduledSparkApplication",
                metadata=metadata,
                schema="sparkoperator.k8s.io_scheduledsparkapplications.schema.yml",
                spec={
                    "concurrencyPolicy": "Forbid",
                    "schedule": schedule,
                    "template": body,
                },
            )
        else:
            super().__init__(
                api_version="sparkoperator.k8s.io/v1beta2",
                kind="SparkApplication",
                metadata=metadata,
                schema="sparkoperator.k8s.io_sparkapplications.schema.yml",
                spec={"spec": body},
            )
