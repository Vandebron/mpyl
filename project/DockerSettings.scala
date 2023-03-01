import sbtassembly.AssemblyKeys
import sbt.{ Def, Task }
import sbtdocker.DockerPlugin.autoImport.{ buildOptions, docker, dockerfile, BuildOptions, ImageId, ImageName }
import sbtdocker.DockerfileBase
import DockerSettings.javaBaseImage
import sbtdocker.DockerPlugin.autoImport._

object DockerSettings {

  val javaBaseImage = "openjdk:11"

  def microService(
                    projectName: String,
                    ports: Int*
                  ): Seq[
    Def.Setting[_ >: Task[Seq[ImageName]] with Task[DockerfileBase] with BuildOptions with Task[ImageId] <: Product with Serializable]
  ] =
    Seq(
      docker := (docker dependsOn AssemblyKeys.assembly).value,
      (docker / buildOptions) := BuildOptions(
        cache = true,
        removeIntermediateContainers = BuildOptions.Remove.Always,
        pullBaseImage = BuildOptions.Pull.IfMissing
      ),
      (docker / dockerfile) := {
        val artifact = (AssemblyKeys.assembly / AssemblyKeys.assemblyOutputPath).value
        new sbtdocker.mutable.Dockerfile {
          from(javaBaseImage)
          copy(artifact, s"/app/${artifact.getName}")
          expose(ports: _*)
          entryPoint(
            "java",
            "-XX:MinRAMPercentage=30.0",
            "-XX:MaxRAMPercentage=60.0",
            "-DINTERFACE=0.0.0.0",
            s"-jar",
            s"app/${artifact.getName}"
          )
        }
      }
    )

}
