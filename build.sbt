name := "sbt-multi-project-example"
ThisBuild / organization := "vandebron.nl"

lazy val mpyl = project
  .in(file("."))
  .aggregate(sbtservice)

lazy val sbtservice = (project in file("tests/projects/sbt-service")).settings(name := "sbtservice")