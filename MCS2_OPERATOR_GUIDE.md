# MCS2 Stage Operator Guide

How to operate a SmarAct MCS2 stage driven over EtherCAT/DS402 by `FB_MotionStageMCS2`.

For the endstop/limit-direction limitation, see [MCS2_OPERATING_NOTES.md](MCS2_OPERATING_NOTES.md).

PV names below are suffixes on the channel prefix (for example `MCS2:01:m1:CALIBRATED`). Motor-record and stage PVs are marked with their `PLC:` prefix.

**Commissioning a new axis for the first time?** Start at §8, not §3. Sections 1–7 assume the axis has already passed checkout.

---

## 1. Concepts you need before touching anything

### 1.1 The four operating modes

The drive runs in exactly one DS402 mode at a time. `OPMODE_REQ` is the single source of truth.

| `OPMODE_REQ` | Value | DS402 mode | What it does |
| --- | --- | --- | --- |
| `CLOSED_LOOP` | 0 | CSP | Normal absolute moves through the TwinCAT NC. Default. |
| `STEP` | 1 | STEP | Open-loop piezo stepping. No encoder feedback loop. |
| `HOME` | 2 | HOME | Vendor referencing routine. |
| `CALIBRATION` | 3 | CALIBRATE | Vendor sensor calibration routine. |

Only `CLOSED_LOOP` uses the NC. The other three are "DS402 manual" modes where the PLC drives the control word directly.

### 1.2 Who sets the mode

You rarely set `OPMODE_REQ` by hand. Issuing a motion command writes it for you:

| Command | Mode written automatically |
| --- | --- |
| `PLC:bMoveCmd` (or a motor-record move) | `CLOSED_LOOP` |
| `STEP_MOVE`, `STEP_FORWARD`, `STEP_REVERSE` | `STEP` |
| `PLC:bHomeCmd` | `HOME` |
| `DO_CALIB` | `CALIBRATION` |

After homing completes and after calibration completes, the library requests `CLOSED_LOOP` again on its own.

**Step mode does not auto-return to closed loop.** This is deliberate, because you normally issue many steps in a row. When you are finished stepping, set `OPMODE_REQ` back to `CLOSED_LOOP` yourself.

### 1.3 Position feedback differs by mode

- Closed loop: position comes from the NC (`ActPos`), and following-error/position-lag monitoring is meaningful.
- Step mode: position is the scaled raw encoder value. Velocity and acceleration readbacks are **not** live, they echo the commanded values.

---

## 2. Pre-motion checklist

Work down this list. Do not skip to a move command.

### 2.1 EtherCAT and drive state

| Check | Expected | Where |
| --- | --- | --- |
| Slave in OP | Slave reached Operational | TwinCAT / EtherCAT diagnostics |
| No DS402 fault | `FAULT` = 0 | `chanState` |
| Amplifier enabled | `AMP_ENABLED` = 1 (once enabled) | `chanState` |
| No stage error | `PLC:bError` = 0, `PLC:nErrorId` = 0 | stage |

The drive is considered **operational** only when all of these are true simultaneously: ReadyToSwitchOn, SwitchedOn, OperationEnabled, VoltageEnabled, QuickStopActive, not Fault, not SwitchOnDisabled. If any one is missing, manual-mode moves (step, home, calibrate) will not start.

### 2.2 Stage enables

| Check | Expected | Notes |
| --- | --- | --- |
| `PLC:bUserEnable` | 1 | If 0, a move request raises the error "Move requested, but user enable is disabled!" |
| `PLC:bHardwareEnable` | 1 | Hardware/interlock input |
| EPS / PMPS power enable | OK | Beam-safety gating, if the device participates |
| Direction enables | Not blocking the direction you want | See §5.3 |

### 2.3 Channel readiness

| Check | PV | Expected |
| --- | --- | --- |
| Sensor present | `SENSOR_PRESENT` | 1 for any closed-loop use |
| Calibrated | `CALIBRATED` | 1 |
| Referenced (homed) | `REFERENCED` | 1 |
| Not already faulted | `FAULT`, `MOVE_FAILED`, `OVERLOAD`, `OVER_TEMP` | all 0 |
| Not already at a limit | `END_STOP`, `RANGE_LIMIT` | both 0 |

If `REFERENCED` is 0 and a homing mode is configured, a move request will post "Axis homing mode set, but homing routine pending". Home first.

### 2.4 Configuration that must be set

**Software range limits are mandatory.** Set `0x200E:1` (min) and `0x200E:2` (max), with max greater than min. The MCS2 reports only a single aggregate "limit active" bit with no direction, so the library uses these limits to work out which side is blocked during recovery. Without them, a stage that boots already sitting on a limit has both directions disabled and cannot be driven off automatically.

Also confirm before first motion:

| Item | PV | Why it matters |
| --- | --- | --- |
| Positioner type | `PTYPE` | Wrong type gives wrong scaling and travel |
| Safe direction | `SAFE_DIR` | Used by referencing; **PreOp-only write** |
| Logical scale inversion | `LSCI` | Sets which way is positive; **PreOp-only write** |
| Logical scale offset | `LSCO` | Position datum |
| Sensor power mode | `SENSOR_MODE` | Sensor must be powered for closed loop |
| Max closed-loop frequency | `MAX_CLF` | Closed-loop drive limit |
| Hold time | `HOLD_TIME` | How long position is held after a move before power drops |
| Step count / amplitude / frequency | `STEP_COUNT`, `STEP_VOLTAGE`, `STEP_FREQ` | Step-mode motion size |

`LSCI` and `SAFE_DIR` are only writable while the slave is in **PreOp**. Changing them requires taking the slave to PreOp; the library deliberately withholds those writes in OP so it does not raise SDO errors.

### 2.5 Wait for the parameter sweep

At boot the PLC writes the full parameter set to the drive in one serialized sweep. Motion is blocked until that sweep finishes. If a move seems to be ignored for the first few seconds after a PLC start, this is usually why. Wait, then retry.

---

## 3. Normal operating procedures

### 3.1 Closed-loop absolute move

1. Confirm `OPMODE_REQ` = `CLOSED_LOOP` (or just issue the move; it will be set).
2. Confirm `REFERENCED` = 1 and `PLC:bError` = 0.
3. Set target position and velocity.
4. Issue the move.
5. Watch `MOVING` and then `IN_POSITION`.

If the enable mode is `DURING_MOTION`, power is applied for the move, held for `HOLD_TIME` after it completes, then dropped. A short settle at the end of a move is expected, not a fault.

### 3.2 Open-loop stepping

1. Set `STEP_COUNT` (sign sets direction), `STEP_VOLTAGE`, `STEP_FREQ`.
2. Issue `STEP_MOVE`, or use `STEP_FORWARD` / `STEP_REVERSE` which force the sign for you.
3. Repeat as needed.
4. **When finished, set `OPMODE_REQ` back to `CLOSED_LOOP`.**

Stepping does not use the NC and does not correct position. Encoder readback still updates.

### 3.3 Homing / referencing

1. Set `HOME_MODE` to the required method.
2. Confirm `SAFE_DIR` is correct for the stage; referencing moves in that direction.
3. Issue `PLC:bHomeCmd`.
4. Watch `REFERENCING`, then `REFERENCED` = 1.

Position-lag monitoring is disabled automatically for the duration of homing and restored afterwards. On completion the library switches the drive back to closed loop by itself.

### 3.4 Calibration

1. Confirm the stage is free to move over a short range; calibration moves the positioner.
2. Confirm `CAL_OPT` is set as required.
3. Issue `DO_CALIB`.
4. Watch `CALIBRATING`, then `CALIBRATED` = 1.
5. The library returns the drive to closed loop automatically.

Calibrate before referencing if both are needed.

### 3.5 Switching mode manually

Write `OPMODE_REQ`. The drive manager switches immediately, and if the drive is in the right mode but not operational it re-runs the DS402 startup sequence (clear control word → reset fault → shutdown → switch on → enable operation).

Do not switch mode while `MOVING` is 1. Stop first.

---

## 4. Stopping and resetting

- **Stop a move:** drop the execute/move request. In manual modes the library issues a halt through the control word.
- **Reset an error:** pulse `PLC:bReset`. This clears `bError`, `nErrorId`, both error message fields, and resets the step and home sub-blocks. In manual mode it also sets the DS402 fault-reset bit.
- **Boot faults:** on the first power-on cycle, if the axis sits in CSP with a latched DS402 fault, the library issues one automatic reset. This is a one-shot per PLC start. Any fault after that needs an explicit operator reset.

---

## 5. Troubleshooting: motion requested but nothing happens

This is the most common complaint. Work through it in order; the checks are ordered by how often they are the cause.

### 5.1 Is the PLC even accepting the request?

Motion only starts when **all** of the following are true:

- `PLC:bError` = 0
- the execute/move request is actually set
- `bAllEnable` is true, which needs `PLC:bUserEnable` = 1 **and** `PLC:bHardwareEnable` = 1 **and** EPS power enable OK
- safety ready is true
- the boot parameter sweep has finished

Then, depending on mode:

| Mode | Extra condition |
| --- | --- |
| Closed loop | NC axis must be out of Undefined/Disabled/ErrorStop |
| Step / Home / Calibrate | drive must be **operational** (all DS402 status bits, §2.1) |

**and the command must match the mode.** A move-absolute request while `OPMODE_REQ` is `STEP` will not execute. This is the single most common cause of "nothing happens": the stage was left in step mode after jogging. Check `OPMODE_REQ` first.

### 5.2 Mode/command mismatch

| Symptom | Cause | Fix |
| --- | --- | --- |
| Absolute move ignored, stage was recently jogged | Left in `STEP` | Set `OPMODE_REQ` = `CLOSED_LOOP` |
| Step command ignored | Mode is `CLOSED_LOOP` | Issue `STEP_MOVE` (auto-switches) or set `OPMODE_REQ` = `STEP` |
| Nothing works after a mode change | Drive in the new mode but not operational | Re-issue the command; the startup sequence re-runs. If it persists, check `FAULT` |

### 5.3 Direction is disabled

If the stage moves one way but not the other, a direction enable is false.

The MCS2 has no separate positive/negative limit inputs, only one aggregate "internal limit active" bit. The library latches which direction was moving when the limit appeared, keeps that direction disabled, and leaves the opposite direction available so you can drive off.

| Situation | What you see | What to do |
| --- | --- | --- |
| Hit a limit moving positive | Forward disabled, message "Cannot move past positive limit." | Move negative to come off |
| Hit a limit moving negative | Backward disabled, message "Cannot move past Negative limit." | Move positive to come off |
| Booted already on a limit | Library infers the blocked side from the nearest configured software limit | Move away from the nearer limit |
| Booted on a limit, **no** soft limits configured | **Both** directions disabled | Configure `0x200E:1` / `0x200E:2`, then recover |

Also check `bOverrideDirEnable` and, on gantry axes, the gantry direction enables. Both gate direction independently of the limit logic.

Remember the retained direction can be stale if the stage was moved by hand while the PLC was off. Confirm the physical position before trusting it.

### 5.4 Stage is at a hardware or range limit

Check `END_STOP` and `RANGE_LIMIT`. If either is 1, the positioner is physically or logically against a boundary. Moving further in that direction will never succeed. Move the other way.

### 5.5 Not referenced or not calibrated

- `REFERENCED` = 0 with a homing mode configured blocks meaningful closed-loop positioning and posts a pending-homing message. Home the stage.
- `CALIBRATED` = 0 means the sensor has not been calibrated. Run `DO_CALIB`.
- `SENSOR_PRESENT` = 0 means no sensor is detected. Closed loop is impossible; this is a wiring/hardware problem, not an operator one.

### 5.6 Power dropped between attempts

With enable mode `DURING_MOTION`, the amplifier is only powered around a move plus `HOLD_TIME`. If `AMP_ENABLED` reads 0 while idle, that is normal. If a move request does not bring it up, the problem is upstream in the enable chain (§5.1), not in the power handling.

---

## 6. Troubleshooting: errors

### 6.1 Reading the error

- `PLC:bError` — error is latched
- `PLC:nErrorId` — numeric code
- error message string — decoded text

If the message is blank but a code is present, the code has no lookup entry yet. Report the raw code.

### 6.2 Common codes

| Code | Meaning | Typical cause and action |
| --- | --- | --- |
| `0x4550` | Stall / position lag monitoring | Stage could not keep up or is mechanically blocked. Check for obstruction, check load, verify velocity is sane for the stage, then reset |
| `0x4357` | Negative limit hit | Move positive off the limit |
| `0x4358` | Positive limit hit | Move negative off the limit |
| `0x4223` | No enable for controller and/or feed | Enable chain broken, see §5.1 |
| `0x4260` | Drive disabled | Drive not enabled; check DS402 status and reset |
| `0x4225` | Drive not ready during axis start | Drive not operational when the move started; re-issue after it reaches operational |
| `0x4222` | Requested set position not allowed | Target outside soft limits |
| `0x4221` / `0x4395` | Set velocity not allowed | Velocity above the configured maximum |
| `0x4466` / `0x4467` | Encoder / invalid actual position | Encoder or link problem; do not keep commanding motion |
| `0x4650` | Drive hardware not ready | Drive-side hardware issue |
| `0x4B07` | Function block timeout (6 s) | Command never completed; check drive state and mode |
| 1 | User enable disabled | Set `PLC:bUserEnable` = 1 |

Messages like "Cannot move past positive limit." are **warnings**, not latched errors. They tell you a direction is blocked.

### 6.3 Channel-state flags worth checking on any fault

| PV | Meaning if 1 | Action |
| --- | --- | --- |
| `FAULT` | Positioner fault | Reset; if it returns, stop and escalate |
| `MOVE_FAILED` | Last movement failed | Check for obstruction and limits |
| `OVERLOAD` | Positioner overload | Stop. Check load, mounting, and cabling |
| `OVER_TEMP` | Over temperature | Stop and let it cool. Repeated occurrences mean duty cycle is too high |
| `FOLLOWING_LIMIT` | Following error limit reached | Same family as `0x4550`; check mechanics and speed |
| `MOVE_DELAYED` | Move delayed | Usually transient; if persistent, check drive state |

`OVERLOAD` and `OVER_TEMP` are the two that justify stopping work and calling for support rather than resetting repeatedly.

### 6.4 Error recovery sequence

1. Read and record `PLC:nErrorId` and the message before clearing anything.
2. Remove the cause (obstruction, wrong target, disabled enable, limit).
3. Pulse `PLC:bReset`.
4. Confirm `PLC:bError` = 0 and `FAULT` = 0.
5. Confirm `OPMODE_REQ` is the mode you actually want.
6. Re-issue a small, safe move first.

Do not clear an error repeatedly without changing anything. A fault that returns immediately is telling you the cause is still present.

### 6.5 Save/restore of position

For relatively-referenced stages the last position is saved and restored across a PLC restart. If restore fails after several retries you get "Error loading previously saved position." Treat the displayed position as untrusted and re-home before relying on it.

---

## 7. When to escalate

Escalate rather than retrying if any of these apply:

- `OVERLOAD` or `OVER_TEMP` recurs
- an encoder error (`0x4466`, `0x4467`) appears
- the drive never reaches operational after mode switches and resets
- both direction enables are false and no soft limits are configured
- the stage is referenced but the reported position is clearly wrong
- an error code has no decoded message (needs a lookup entry added)

Capture before escalating: `PLC:nErrorId`, the error message, `STATE` (raw channel state), `OPMODE_REQ`, and what was commanded.

---

## 8. Motion checkout (new or reworked axis)

Run this in order. Each stage assumes the previous one passed. Do not energise a stage and command a move to find out whether the wiring is right.

### 8.1 Before power

| Check | Why it matters |
| --- | --- |
| Correct positioner type physically fitted, and it matches what will be set in `PTYPE` | Wrong type gives wrong travel, wrong scaling, and can overdrive the actuator |
| Sensor cable fitted and seated | No sensor means no closed loop at all |
| Stage free to move over its full intended range | Calibration and referencing both move the stage |
| Nothing mechanically preloaded against an endstop | Booting on a limit is the awkward recovery case |
| Correct ESI/XML revision loaded for the MCS2 module | Mismatched ESI gives wrong PDO layout, which shows up as nonsense readbacks |

### 8.2 EtherCAT bring-up

1. Scan the bus and confirm the MCS2 module appears with the expected vendor and product identity.
2. Bring the slave to **OP**. Confirm it stays there rather than cycling.
3. Confirm the ESM state readback is live in the PLC (see §9.1). This one is easy to miss because nothing obviously breaks until a PreOp-only write is needed.

If the slave will not leave PreOp or SafeOp, stop here. Nothing downstream will behave, and the PLC will report confusing secondary symptoms.

### 8.3 Process-image linking

Every `AT %I*` / `AT %Q*` variable in the drive structure must be linked to the matching PDO entry. Verify the link list rather than assuming; an unlinked variable silently reads 0.

**Inputs from the drive:**

| Variable | Consequence if unlinked or mislinked |
| --- | --- |
| status word (`stDriveStatus`) | Drive never appears operational; no fault or limit detection |
| `nModeOfOperationDisplay` | Mode readback wrong, so mode switching never completes |
| `nFollowingError` | No following-error visibility |
| `nDriveControlNC`, `nModeOfOperationNC` | Closed-loop control word/mode from the NC never reaches the drive |
| `nSlaveAddr` | Reads 0, so **every CoE read and write goes nowhere or to the wrong slave** |
| `nEcatState` | Reads 0, so PreOp is never detected and PreOp-only parameters are never written |

**Outputs to the drive:**

| Variable | Consequence if unlinked |
| --- | --- |
| `nDriveControl` | Manual modes (step, home, calibrate) can never enable the drive |
| `nModeOfOperation` | Mode switch requests never take effect |
| `nTargetPosition` | Closed-loop moves command nothing |
| profile velocity / acceleration / deceleration | Moves run at wrong or zero speed |

**Stage-side:**

| Item | Check |
| --- | --- |
| NC axis reference | Axis linked, and axis ID non-zero at runtime |
| `bHardwareEnable` | Linked to the real STO/interlock input, not forced |
| Raw encoder input | Linked to the correct channel's position entry |
| `bBrakeRelease` | Linked only if a brake exists |

> **Do not link the limit-enable inputs for an MCS2 axis.** The MCS2 function block *writes* the forward and backward limit enables in software from the drive's aggregate limit status. Linking them to physical inputs as well creates a conflict where one writer overwrites the other.

### 8.4 Per-axis CoE addressing

The MCS2 places each channel's objects 0x800 apart: channel 1 at the base index, channel 2 at base + 0x800, channel 3 at base + 0x1000. The PLC computes every object index from the module/channel number given to the axis at instantiation.

**Each axis on a controller must be given a unique channel number.** This is the highest-consequence configuration mistake in the whole system:

- Two axes given the same channel both read and write the *same* CoE objects.
- Axis B's parameter sweep silently overwrites axis A's settings.
- Readbacks look plausible, so the fault can survive checkout and appear later as drift or as one axis inexplicably changing configuration.

Verify by changing one distinctive parameter on one axis and confirming that **only** that axis's readback changes.

### 8.5 Parameter set verification

1. Let the boot parameter sweep complete.
2. Read back every parameter in §2.4 and compare against the intended values.
3. Pay specific attention to the two PreOp-only objects, `LSCI` and `SAFE_DIR`. If the slave came up straight into OP and the ESM state was not visible, these will not have been written and will silently keep whatever the drive already had.
4. Confirm the software range limits are set with max greater than min.

A readback that equals the drive default rather than your intended value means the write did not happen. Do not assume it did.

### 8.6 Direction and scaling sanity

Do this before trusting any absolute position.

1. Command a small step move in the positive direction.
2. Confirm the stage physically moves in the direction you call positive.
3. Confirm the position readback increases.

If the stage moves the wrong way, fix it with the logical scale inversion (`LSCI`) rather than by negating targets elsewhere. Remember it is a PreOp-only write.

Then check magnitude: command a known displacement and measure it. If commanded and actual differ by a constant ratio, the scaling factor or base resolution is wrong. Do not proceed to closed loop with bad scaling; the position loop will fight itself.

### 8.7 Progressive motion checkout

Work up in this order, confirming each before moving on:

1. **Step mode, small count.** Lowest risk: open loop, no position loop, no NC. Confirms drive enables, control word, and direction.
2. **Step mode, both directions.** Confirms both directions are permitted and the encoder tracks both ways.
3. **Calibration.** Confirms sensor and drive agree. Watch `CALIBRATED` go to 1.
4. **Referencing.** Confirms `SAFE_DIR` and homing parameters. Watch `REFERENCED` go to 1.
5. **Closed-loop move, small.** First use of the NC. Confirms target position, profile parameters, and following error.
6. **Closed-loop move, larger, both directions.** Confirms scaling over real travel.
7. **Approach each soft limit deliberately.** Confirms the limit reacts, the correct direction is disabled, and the stage can be driven back off.

Step 7 is the one most often skipped and the one that matters most operationally, because it is the behaviour operators will actually meet during a shift.

### 8.8 Sign-off record

Record for each axis: channel number, positioner type, soft limit min and max, scale inversion state, safe direction, measured travel, and the date checkout passed. The channel number and soft limits are the two that cause the most confusion later if undocumented.

---

## 9. Fault-finding: linking, CoE, and bad input values

Use this when behaviour is wrong in a way that the operational troubleshooting in §5 and §6 does not explain.

### 9.1 Symptoms that point at process-image linking

| Symptom | Likely cause | How to confirm |
| --- | --- | --- |
| Drive never reaches operational, no fault reported either | Status word not linked, so every status bit reads 0 | Watch the status word while power-cycling the drive; a permanently static value means it is not linked |
| Mode switch requested, readback never changes | Mode-of-operation output or display input not linked | Write the mode and watch both the request and the display |
| Closed-loop move does nothing, step mode works | NC-side control word/mode or target position not linked | Step mode bypasses the NC path, so this pattern is diagnostic |
| Step/home/calibrate do nothing, closed loop works | Manual control word output not linked | The manual path uses the control word directly |
| All CoE reads and writes fail or time out | Slave address input not linked, reading 0 | Check the slave address value at runtime; 0 is never valid |
| PreOp-only parameters never take effect | ESM state input not linked | Check the state value; it should track INIT/PREOP/SAFEOP/OP |
| Position readback frozen at 0 while the stage clearly moves | Raw encoder input not linked | Move in step mode and watch the raw count |
| Position readback jumps or is wildly out of scale | Encoder linked to the wrong channel or wrong data width | Compare against a second axis and against physical movement |

A useful general rule: **a value that never changes under any condition is usually unlinked, not broken.**

### 9.2 Symptoms that point at CoE configuration

| Symptom | Likely cause | Action |
| --- | --- | --- |
| Changing a parameter on one axis changes another axis | Duplicate channel number on two axes | Fix the channel assignment; re-verify the whole parameter set on both |
| Parameter readback always shows the drive default | Write never happened, or was rejected | Check whether it is a PreOp-only object; check the parameter sweep completed |
| `LSCI` or `SAFE_DIR` will not change | Both are PreOp-only | Take the slave to PreOp, write, return to OP |
| SDO errors at runtime | Write attempted in the wrong ESM state, or wrong object index | Confirm ESM state handling and channel offset |
| Motion blocked indefinitely after a restart | Parameter sweep did not complete | Look for a sweep error; acknowledge and let it re-run |
| Travel is right in one direction only | Soft limits asymmetric or wrong sign after inversion | Re-check limits *after* setting inversion, not before |

Order matters: set the scale inversion first, then set the soft limits, because inversion changes what min and max mean physically.

### 9.3 Symptoms that point at bad input values

| Symptom | Likely bad input | Check |
| --- | --- | --- |
| Move rejected, position-not-allowed error | Target outside the soft limits | Compare the target against min and max |
| Move rejected, velocity-not-allowed error | Velocity above the configured maximum | Compare against the NC maximum velocity |
| Stall / position-lag error on every move | Velocity or acceleration too aggressive for the stage, or load too high | Reduce speed and retry; if it only fails under load, it is mechanical |
| Step moves do nothing visible | Step count, amplitude, or frequency at or near zero | Read back all three |
| Step moves far too large or small | Step amplitude or the step scale factor wrong | Verify against the positioner type |
| Referencing runs the wrong way or never finds the mark | Safe direction wrong, or reference type/options wrong | Verify safe direction physically before re-running |
| Position drifts after power cycle | Relative encoder with save/restore, restore failed or was never valid | Re-home rather than trusting the restored value |
| Closed loop oscillates or buzzes at rest | Max closed-loop frequency or control options wrong for the positioner | Verify positioner type first, it drives the sensible defaults |

### 9.4 Isolating the layer

When it is unclear whether a problem is PLC, linking, CoE, or mechanical, use step mode as the probe:

- **Step mode works, closed loop does not** → the problem is in the NC path, its linking, or scaling. The drive, the control word, and the mechanics are fine.
- **Neither works** → the problem is drive enable, control word linking, or the drive is not operational.
- **Both work but positions are wrong** → scaling, inversion, or referencing. Motion itself is healthy.
- **Both work, positions correct, limits behave wrongly** → soft limit configuration or the limit-direction logic.

This narrows the search quickly and avoids changing parameters at random.

### 9.5 What not to do

- Do not clear faults repeatedly to "get past" a problem. A fault that returns immediately is reporting a live cause.
- Do not compensate for wrong direction by negating targets in a higher layer. Fix the inversion at the drive.
- Do not commission with the soft limits left unset, intending to add them later. The recovery behaviour depends on them.
- Do not force or override the hardware enable to make a move happen during checkout. That defeats the interlock you are supposed to be proving.
