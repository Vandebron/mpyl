name := "sbt-multi-project-example"
ThisBuild / organization := "vandebron.nl"
ThisBuild / scalaVersion := "2.12.3"

lazy val mpyl = project
  .in(file("."))
  .aggregate(sbtservice)

lazy val sbtservice = (project in file("tests/projects/sbt-service")).settings(name := "sbtservice")