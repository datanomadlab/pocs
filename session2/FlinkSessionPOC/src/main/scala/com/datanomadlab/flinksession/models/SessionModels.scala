package com.datanomadlab.flinksession.models

// Evento individual de sesión
case class SessionEvent(
  userId: String,
  timestamp: Long,
  action: String
)

// Agregación de eventos de sesión
case class SessionAggregate(
  userId: String,
  sessionStart: Long,
  sessionEnd: Long,
  events: List[SessionEvent]
)
