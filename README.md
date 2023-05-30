# lcls-twincat-motion
Twincat 3 Motion Control Utilities for LCLS PCDS EPICS

## Quick Start
The library is installed on the plc programming nodes as `lcls-twincat-motion`. Once installed, you can create a motion-ioc-compatible setup with default settings by declaring in `Main`:
```
M1: ST_MotionStage;
fbMotion1: FB_MotionStage;
```
And invoking as:
```
fbMotion1(stMotionStage:=M1);
```

You would then link your hardware as appropriate to `M1.Axis`, `M1.bLimitForwardEnable`, `M1.bLimitBackwardEnable`, `M1.bHome`, `M1.bBrakeRelease`, and `M1.bHardwareEnable`. It is important to set `M1.nEnableMode` the value the most fits your use case (see settings below). You also need to set `bPowerSelf` to `TRUE`, unless your device participates in LCLS's PMPS system, where it must be `FALSE`.

Note that currently, the `ST_MotionStage` instances must be named `Main.M1`, `Main.M2`... etc. due to limitations in the EPICS driver.

## Simulated Axis
If you want to try out the IOC with a simulated axes, a shortcut function block is provided as:
```
fbMotionSim: FB_MotionStageSim;
fbMotionSim(stMotionStage:=M1);
```
This block removes all hardware-related protections to get the simulated axis moving, e.g.
```
stMotionStage.bLimitBackwardEnable := TRUE;
stMotionStage.bLimitForwardEnable := TRUE;
stMotionStage.bHardwareEnable := TRUE;
stMotionStage.bPowerSelf := TRUE;
stMotionStage.nEnableMode := ENUM_StageEnableMode.ALWAYS;
fbMotionStage(stMotionStage := stMotionStage);
```

## Settings
`ST_MotionStage` has the following settings:

| Setting | Type | Usage | Default |
| --- | --- | --- | --- |
| `bPowerSelf` | `BOOL` | If `FALSE` (default), then `FB_MotionStage` will expect an external PMPS function block to call `MC_Power` appropriately. You can switch this to `TRUE` to opt out of PMPS and handle motor enabling within `FB_MotionStage`. | `FALSE` |
| `nEnableMode` | `ENUM_StageEnableMode` | Automatically enable the NC Axis `ALWAYS`, `NEVER`, or only `DURING_MOTION` (default). Switch this to `ALWAYS` if you want active position correction at all times and to `NEVER` if you're doing checkout with the TwinCAT NC GUI. | `DURING_MOTION` |
| `nBrakeMode` | `ENUM_StageBrakeMode` | Break disengage timing. Disengage the break `IF_ENABLED` (default), `IF_MOVING`, or never change the break state with `NO_BRAKE`. Note that this does nothing unless a brake is linked to `bBrakeRelease`. | `IF_ENABLED` |
| `nHomingMode` | `ENUM_EpicsHomeCmd` | Pick which switch to home to, or not to require homing (default). | `NONE` |
| `fHomePosition` | `LREAL` | The position to set at the home switch. | 0 |
| `bGantryMode` | `BOOL` | Set to `TRUE` to activate gantry EPS. | `FALSE` |
| `nGantryTol` | `LINT` | If the gantry error is greater than this number of encoder counts, trigger a virtual limit. | 0 |
| `nEncRef` | `ULINT` | Encoder count for gantry motion where the two axes are aligned. | 0 |

## Provided Resources
| Resource | Type | Usage |
| --- | --- | --- |
| `ST_MotionStage` | struct | Contains all relevant information about a single axis. You can pass this around and manipulate it inside of other function blocks. It relys on `FB_MotionStage` to provide the logic. |
| `ST_PositionState` | struct | Contains all information about a specific position state, e.g. "out" |
| `FB_MotionStage` | function block | Provides a connection to ESS's motion library for motor record functionality, as well as some standard handling of brake and auto enable/disable. |
| `FB_MotionStageSim` | function block | Shortcut to getting a simulated axis running. |
| `FB_MotionRequest` | function block | Moves an axis handled by `FB_MotionStage` to a specific position. |
| `FB_PositionStateMove` | function block | Moves an axis to a specific position state. |
| `FB_PositionStateManager` | function block | Moves an axis to any one of `MOTION_GVL.MAX_STATES` (= currently 9) preset position states. Intended for EPICS use. |
| `FB_EpicsInOut` | function block | Example usage of `FB_PositionStateManager` for a simple in/out device. |
| `FB_PositionStateLock` | function block | Allows states to be immutable if configured as such |
| `ENUM_EpicsHomeCmd ` | enum | Options for axis homing through the motor record |
| `ENUM_EpicsMotorCmd` | enum | Options for axis commands through the motor record. You can use these through TwinCAT too. |
| `ENUM_StageBrakeMode` | enum | Options for axis brake mode. Brake can be enabled at standstill or at disabled. |
| `Enum_StageEnableMode` | enum | Options for axis enable/disable handling. Axis can be enabled always, never, or only during motion. |

## Homing
To activate a homing routing, put 1 to the EPICS `:PLC:bHomeCmd` field. Note: the `.HOMF` and `.HOMR` fields work in some cases at the IOC, but are currently buggy.

To configure a homing routine, set the `fHomePosition` variable to the position to use after homing, and set the `nHomingMode` variable to pick a strategy. These strategies are stored in `ENUM_EpicsHomeCmd` enum. All homing motion strategies move towards their destinations using the "Homing Velocity (towards plc cam)" parameter , then off of the switch using the "Homing velocity (off plc cam)" parameter. The normal options are:
- `LOW_LIMIT`: Move to the low limit (backward) switch. Set home position at the first point we see as we leave the switch.
- `HIGH_LIMIT`: Move to the high limit (forward) switch. Set home position at the first point we see as we leave the switch.
- `HOME_VIA_LOW`: Move towards the low limit (backward) switch, seeking out the position where `bHome` is `TRUE`. If we reach the limit switch without finding `bHome`, reverse direction and try moving towards the high switch. Set home position to the point just above the `bHome` signal.
- `HOME_VIA_HIGH`: Move towards the high limit (forward) switch, seeking out the position where `bHome` is `TRUE`. If we reach the limit switch without finding `bHome`, reverse direction and try moving towards the low switch. Set home position to the point just below the `bHome` signal.

There are two additional special-case options:
- `ABSOLUTE_SET`: When we ask for a home, do not move the motor- simply declare the current position as "home". This is basically a manual homing routine.
- `None`: Do not home! Ever! This is actually the default value, and the only one "implemented" prior to this PR.

If the homing strategy is set to any value other than `None`, the library knows we have a motor that wants save/restore. In these cases, the last position of the motor will be saved on TwinCAT shutdown and restored on the first cycle of the PLC program. This prevents the location of your relatively encoded motor from being lost when the PLC is reconfigured.

## States Function Blocks

This library contains support for user moves among named position states. These are currently implemented up to 3 dimensions but internally there is no limit to how many motors can be associated with one state mover, so this can be trivially expanded in the future.

This includes support for EPICS moves between states. The function block will begin a move when the user caputs a new enum value, cancelling a previous move if one was in process.

This also includes support for PMPS using https://github.com/pcdshub/lcls-twincat-motion.

### States Setup

Before doing any states setup, make sure your motor is set up properly using `ST_MotionStage` and `FB_MotionStage` as above. You'll want to keep `bPowerSelf` at `FALSE` if you plan to use PMPS states, otherwise change it to `TRUE` as normal.

#### Picking the Right function block

Start by picking the function block that most closely matches your use case (number motors, PMPS or no PMPS). E.g. if you have two motors and you need PMPS, pick `FB_PositionStatePMPS2D`.

- `FB_PositionStatePMPS1D`
- `FB_PositionStatePMPS2D`
- `FB_PositionStatePMPS3D`
- `FB_PositionStatePMPS1D`
- `FB_PositionStatePMPS2D`
- `FB_PositionStatePMPS3D`

In addition, if you only have `IN` and `OUT` states, consider using one of the example function blocks, which have slighly simplified interfaces and can bypass some of the setup steps:

- `FB_PositionState1D_InOut`
- `FB_PositionState2D_InOut`
- `FB_PositionStatePMPS1D_InOut`
- `FB_PositionStatePMPS2D_InOut`

#### Set Global Parameters

Next, determine how many states you'll be using. The `lcls-twincat-general` library has `GeneralConstants.MAX_STATES` set to 15 by default, which is the maximum number of named states we can support with EPICS MBBI/MBBO records. Feel free to reduce this number to save on resources if no states device in your PLC uses that many states, or increase it if your PLC needs more states and plans to use some other record for the input/output.

If you aren't using any multidimensional states, feel free to reduce the value of `MotionConstants.MAX_STATE_MOTORS` as well, which defaults to 3.

If you aren't sure about these, leave them alone for now, the defaults are sensible. Later, you can check the values of `MOTION_GVL.nMaxStateMotorCount` and `MOTION_GVL.nMaxStates` if you want to know how many motors per state and how many states your PLC is actually using.

See https://infosys.beckhoff.com/english.php?content=../content/1033/tc3_plc_intro/3470837515.html&id= for information on parameter lists and how to set their values in your project.

#### Configure Each State Position

To configure state positions, you'll be creating an array with the following sort of declaration per motor:
```
astPositionState: ARRAY [1..GeneralConstants.MAX_STATES] of ST_PositionState;
```
Note that, for ND states, you'll match the states by their array position. That is, a move to state 2 will move all motors to state 2. Make sure to fill in the states with all the important information. Here's an overview of all the fields for each state:

| Setting | Type | Usage | Default |
| --- | --- | --- | --- |
| `sName` | `STRING` | The name associated with the state. In some contexts this will be used to identify the state. | `''` |
| `fPosition` | `LREAL` | The physical position of the state in engineering units. Either provide `fPosition` or `nEncoderCount`, but not both. | `0` |
| `nEncoderCount` | `UDINT` | The physical position of the state in encoder counts. Either provide `fPosition` or `nEncoderCount`, but not both. | `0` |
| `bUseRawCounts` | `BOOL` | Set this to `TRUE` to use `nEncoderCount` as the source of truth for positions, instead of the default `fPosition`. | `FALSE` |
| `bValid` | `BOOL` | Set this to `TRUE` to prove to the PLC that this is a real state. This starts as `FALSE` to make sure that we don't ever consider uninitialized states in any of the function blocks. | `FALSE` |
| `bMoveOk` | `BOOL` | This must be set to `TRUE` to allow moves to this state. You can set this to `FALSE` during operations to temporarily prevent unsafe moves. For devices like common components this is often set in https://github.com/lcls-twincat-common-components instead of in the project itself. | `FALSE` |
| `fDelta` | `LREAL` | The maximum allowed distance between the motor's position in engineering units and the set position where we are still considered to be "at" the state. | `0` |
| `fVelocity` | `LREAL` | The speed we move toward this state at. | `0` |
| `fAccel` | `LREAL` | Optional: the acceleration to use for moves to this state | `0` |
| `fDecel` | `LREAL` | Optional: the deceleration to use for moves to this state | `0` |
| `bLocked` | `BOOL` | Optional: set this to `TRUE` to lock the parameters in place. That is, whatever parameters we have set when we reach the first states handler will be restored on every cycle. | `FALSE` |
| `stPMPS` | `ST_DbStateParams` | Contains the PMPS lookup information associated with this state. You must set the `sPmpsState` `STRING` attribute to the database key to participate in a PMPS lookup. | |

You should leave the unused states uninitialized if you have fewer states than `GeneralConstants.MAX_STATES`.


#### Enum Setup and PyTMC

It is expected, though not required, to supply an enum to use to control the setpoint and readback as an interface to the EPICS MBBI/MBBO. You need to instantiate one enum for the readback and one enum for the setpoint. This enum must have 0 be the Unknown state and states 1 onward match the state array positions from the earlier steps. In some context, this is what is used to name each state.

For an example valid enum, see https://github.com/pcdshub/lcls-twincat-motion/blob/master/lcls-twincat-motion/Library/DUTs/ENUM_EpicsInOut.TcDUT.

You should avoid writing to this enum from PLC code, and if you do write to this enum from PLC code make sure you only write to it for a single cycle to emulate the EPICS behavior.

Here is an example of one correct way to apply pytmc pragmas to the enums and function blocks to make sure you match the expected PV structure for maximum compatibility with `pydm` screens, `typhos`, and `pcdsdevices`:

```
VAR
    {attribute 'pytmc' := '
      pv: MY:PREFIX:STATES:SET
      io: io
    '}
    eStateSet: ENUM_EpicsInOut;
    {attribute 'pytmc' := '
      pv: MY:PREFIX:STATES:GET
      io: io
    '}
    eStateGet: ENUM_EpicsInOut;
    {attribute 'pytmc' := '
      pv: MY:PREFIX
      io: io
    '}
    fbPositionState1D: FB_PositionState1D;
END_VAR
```

#### Putting it all together

Pass in your `ST_MotionStage` structs, your state arrays, and your enums to the appropriate inputs.
Make sure you also pass `bEnable := TRUE` if you want moves to be enabled.

```
fbPositionState1D(
    stMotionStage:=stMotionStage,
    astPositionState:=astPositionState,
    eEnumSet:=eStateSet,
    eEnumGet:=eStateGet,
    bEnable:=TRUE,
);
```

### States with PMPS

States with PMPS have the following additional setup:

- For at least one of the motors, set `stPMPS.sPmpsState` to the PMPS database lookup key on each state position.
- Pass in `sDeviceName` to the device name desired for the PMPS diagnostic.
- Pass in `sTransitionKey` to the beam parameter lookup needed for transition states.
- Rather than a single `bEnable`, set `bEnableMotion`, `bEnableBeamParams`, and `bEnablePositionLimits` to `TRUE` (unless you want to disable any of those features.)

### Older Versions

There have been several iterations of the states code with the intent of cleaning up the usage, enabling N-dimensional states, and other quality-of-life tweaks. Older version are kept in the library but are kept in a folder named "Deprecated" and have the "obsolete" attribute pragma, which will show warnings if you compile a project using them. These function blocks will remain unchanged but will not get bugfixes or features updates.

## Confluence links
* Flight rules: https://confluence.slac.stanford.edu/display/PCDS/Beckhoff+Flight+Rules
* Axis setup: https://confluence.slac.stanford.edu/display/PCDS/Basic+Beckhoff+Stepper+Axis+Software+Setup
* Axis tuning: https://confluence.slac.stanford.edu/display/PCDS/Beckhoff+Stepper+Axis+Tuning
