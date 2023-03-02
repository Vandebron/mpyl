name := "sbt-multi-project-example"
organization in ThisBuild := "vandebron.nl"
scalaVersion in ThisBuild := "2.12.3"

lazy val mpyl = project
  .in(file("."))
  .aggregate(sbtservice)

lazy val sbtservice = (project in file("tests/projects/sbt-service")).settings(name := "sbtservice")