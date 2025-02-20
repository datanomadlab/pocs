name := "FlinkSessionPOC"

version := "0.1"

scalaVersion := "2.12.18"

// Unificamos la versión de Flink
val flinkVersion = "1.14.6"

// Habilitar fork y configurar opciones de Java
Compile / run / fork := true
run / fork := true

// Configuración de Java para permitir la reflexión
run / javaOptions ++= Seq(
  "--add-opens=java.base/java.util=ALL-UNNAMED",
  "--add-opens=java.base/java.lang=ALL-UNNAMED",
  "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED",
  "--add-opens=java.base/java.text=ALL-UNNAMED",
  "--add-opens=java.desktop/java.awt.font=ALL-UNNAMED"
)

// Dependencias principales
libraryDependencies ++= Seq(
  "org.apache.flink" %% "flink-streaming-scala" % flinkVersion,
  "org.apache.flink" %% "flink-clients" % flinkVersion,
  "org.apache.flink" %% "flink-connector-kafka" % flinkVersion,
  "org.apache.flink" %% "flink-scala" % flinkVersion,
  "org.apache.flink" %% "flink-streaming-java" % flinkVersion,
  "org.apache.flink" % "flink-connector-base" % flinkVersion,
  "org.apache.flink" % "flink-core" % flinkVersion,
  
  // Logging
  "org.slf4j" % "slf4j-api" % "1.7.36",
  "org.slf4j" % "slf4j-log4j12" % "1.7.36",
  "log4j" % "log4j" % "1.2.17",
  
  // Otras dependencias
  "com.google.code.gson" % "gson" % "2.10.1",
  "com.influxdb" % "influxdb-client-java" % "7.0.0"
)

// Forzar versiones específicas para resolver conflictos
dependencyOverrides ++= Seq(
  "com.google.code.findbugs" % "jsr305" % "3.0.2",
  "org.slf4j" % "slf4j-api" % "1.7.36"
)

// Excluir dependencias problemáticas
excludeDependencies ++= Seq(
  ExclusionRule(organization = "org.apache.flink", name = "force-shading"),
  ExclusionRule(organization = "com.google.code.findbugs", name = "jsr305")
)

// Configuración para sbt-assembly
assembly / assemblyOption := (assembly / assemblyOption).value
  .withIncludeScala(false)
  .withIncludeDependency(true)

// Estrategia de merge más detallada
assembly / assemblyMergeStrategy := {
  case PathList("META-INF", "services", xs @ _*) => MergeStrategy.concat
  case PathList("META-INF", xs @ _*) => MergeStrategy.discard
  case "application.conf" => MergeStrategy.concat
  case "reference.conf" => MergeStrategy.concat
  case "module-info.class" => MergeStrategy.discard
  case x if x.endsWith("module-info.class") => MergeStrategy.discard
  case x if x.endsWith(".properties") => MergeStrategy.first
  case x if x.endsWith("public-suffix-list.txt") => MergeStrategy.first
  case _ => MergeStrategy.first
}

// Configuración adicional para evitar conflictos
ThisBuild / evictionErrorLevel := Level.Warn
ThisBuild / versionScheme := Some("early-semver")

// Configuración para logging
logLevel := Level.Info
