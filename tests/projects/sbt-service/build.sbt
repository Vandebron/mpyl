enablePlugins(sbtdocker.DockerPlugin)
DockerSettings.microService("mpyl-services", 8082)

libraryDependencies += "org.scalatest" %% "scalatest" % "3.2.15" % "test"