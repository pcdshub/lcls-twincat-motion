# MCS2 usage notes

Operational notes for the SmarAct MCS2 EtherCAT (DS402) motion stages, gathered from
bench work and the MCS2 EtherCAT Interface User Manual v1.0.4.

## Safe Direction (0x200C) is Pre-Op write-only

- The PV `SAFE_DIR` (`nSafeDir`, object `0x200C`) is read/write, but the **drive only
  accepts the write in the EtherCAT Pre-Op state**. The manual lists its access as
  `R(W)*` — "writable only when in Pre-Op" (§4.6.13, access-mode table).
- Writing `SAFE_DIR` while the drive is in OP does nothing on the drive. The value snaps
  back within a few seconds because `nSafeDir` is a shared command/read-back field: the
  cyclic reader (`FB_ReadChanParameters`) reads the drive's actual value back into it,
  overwriting the rejected write.
- To change safe direction: bring the axis to Pre-Op, change `SAFE_DIR` (the on-change
  writer in `FB_WriteChanParameters` sends it while `bInPreOp`), then return to OP.
- **Changing safe direction requires re-calibrating the end stop** (manual §4.6.13,
  and §3.3.5). The stored calibration is tied to the safe direction.

## Calibration can be re-run

- The MCS2 calibrate routine no longer skips when the drive already reports
  "Calibration Attained" (status Bit12). `FB_MCS2Calibrate` always asserts the Run bit
  and re-runs, so a safe-direction change (or any mechanical change) can be re-calibrated
  without a power cycle.
- Control bit 4 on `0x200A` is documented as "start or restart calibration"; the drive
  supports re-running natively.

## Soft range limits are enforced during referencing

- The firmware honors soft range limits during the referencing/homing move, not just
  during normal positioning. On the way to the end stop it treats a range limit like a
  stop and reverses, then reports Range Limit (`0x8500`) and raises the homing-error bit.
- Symptom: an end-stop-referenced stage fails to home with `MCS2: 0x8500` when the soft
  limits are set outside the real travel. Fix: set `SoftLimMin`/`SoftLimMax` to the
  stage's actual range so the end stop sits inside the limits and the reference completes.
- A homing failure now surfaces as `Homing failed (MCS2: 0x8500)` instead of a bare code.

## Home/calibrate wait for the NC lag-monitoring disable

- Home and calibrate are open-loop drive routines. Before they start, the PLC disables NC
  position-lag monitoring (`AxisEnPositionLagMonitoring`) via `MC_WriteParameter`, which is
  asynchronous (several NC cycles).
- The home/calibrate move now waits for that disable to actually land (`bLagClearPending`
  gate on the `fbhome`/`fbCalibrate` execute) so the drive's referencing move cannot trip an
  NC following error on residual lag monitoring. A 500 ms timeout caps the wait so a missing
  write cannot hang the routine, and stages that never had lag monitoring enabled do not wait.

## Drive-only faults propagate to bError

- MCS2 channel-state faults the NC never latches now set `bError` with
  `nErrorId = MCS2_FAULT (0x7903)` and message `MCS2 drive fault, NC did not latch
  (MCS2: 0x....)`.
- Promoted conditions: movement-failed, following-limit, positioner-overload,
  over-temperature, positioner-fault. Excluded: range-limit and end-stop (normal
  limit/homing status, never a hard fault).
- Suppressed during the drive's own home (referencing) and calibrate routines, which run
  their own failure handling. Covers closed-loop, step (open-loop) moves, and idle.
- Edge-triggered (reports once on the rising edge). A reset clears it; a still-asserted
  condition (e.g. Movement-Failed, which only clears on the next successful move) does not
  re-latch, so reset is not blocked. A fresh fault re-fires on the next rising edge.
