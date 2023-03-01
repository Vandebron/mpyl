name := "sbt-multi-project-example"
organization in ThisBuild := "vandebron.nl"
scalaVersion in ThisBuild := "2.12.3"

lazy val mpyl = project
  .in(file("."))
  .aggregate(sbtService)

lazy val sbtService = (project in file("tests/projects/sbt-service")).settings(name := "sbtService")