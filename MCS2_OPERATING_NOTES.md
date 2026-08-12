# MCS2 Operating Notes

## Endstop Recovery

MCS2 piezo stages do not provide separate positive and negative limit-switch inputs. The PLC therefore uses the aggregate `stDS402Drive.stDriveStatus.InternalLimitActive` status to detect a physical endstop or configured soft limit.

Because this status does not identify the direction, `FB_MotionStageMCS2` retains the last commanded direction in persistent variables. When a limit is active, the direction associated with that last move is disabled and the opposite direction remains enabled for recovery. The retained direction is not overwritten while the limit remains active during a recovery move.

If the PLC starts with `InternalLimitActive` already set and no valid direction has ever been recorded, the library disables both directions. This is deliberate: the aggregate status alone cannot safely distinguish which direction is blocked. The operator must resolve the condition using an approved manual recovery procedure or provide direction information before re-enabling motion.

The retained direction can be stale if the stage was moved while the PLC was off. Treat the automatic recovery direction as a safety aid, not as a substitute for checking the stage and the drive state.

A future MCS2 operating guide should document the project-specific manual recovery and reset procedure, including how to establish a known direction when the persisted direction is unavailable or suspect.
