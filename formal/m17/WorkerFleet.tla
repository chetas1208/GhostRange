---- MODULE WorkerFleet ----
(* Abstraction for GhostShield P2: worker count never exceeds MaxWorkers.
   Not a line-for-line production model. *)

EXTENDS Naturals

VARIABLES active, max, pending

Init ==
  /\ active = 0
  /\ max = 2
  /\ pending = 0

CreateWorker ==
  /\ active < max
  /\ active' = active + 1
  /\ UNCHANGED <<max, pending>>

CreateWorkerBlocked ==
  /\ active >= max
  /\ UNCHANGED <<active, max, pending>>

TerminateWorker ==
  /\ active > 0
  /\ active' = active - 1
  /\ UNCHANGED <<max, pending>>

Next ==
  \/ CreateWorker
  \/ CreateWorkerBlocked
  \/ TerminateWorker

Spec == Init /\ [][Next]_<<active, max, pending>>

NeverExceedMax ==
  active <= max

====
