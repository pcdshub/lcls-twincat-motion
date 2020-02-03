# lcls-twincat-motion
Twincat 3 Motion Control Utilities for LCLS PCDS EPICS

## Quick Start
The library is installed on the plc programming nodes as `lcls-twincat-motion`. Once installed, you can create a motion-ioc-compatible setup with default settings by declaring in `Main`:
```
M1: DUT_MotionStage;
fbMotion1: FB_MotionStage;
```
And invoking as:
```
fbMotion1(stMotionStage:=M1);
```

You would then link your hardware as appropriate to `M1.Axis`, `M1.bLimitForwardEnable`, `M1.bLimitBackwardEnable`, `M1.bHome`, `M1.bBrakeRelease`, and `M1.bHardwareEnable`. It is important to set `M1.nEnableMode` the value the most fits your use case (see settings below). You also need to set `bPowerSelf` to `TRUE`, unless your device participates in LCLS's PMPS system, where it must be `FALSE`.

Note that currently, the `DUT_MotionStage` instances must be named `Main.M1`, `Main.M2`... etc. due to limitations in the EPICS driver.

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
`DUT_MotionStage` has the following settings:

| Setting | Type | Usage |
| --- | --- | --- |
| `bPowerSelf` | `BOOL` | If `TRUE` (default), this function block will call `MC_Power` based on the `bEnable` attribute in the struct. Otherwise, you'll have to call `MC_Power` somewhere else (perhaps for MPS) |
| `nEnableMode` | `ENUM_StageEnableMode` | Automatically enable the NC Axis always, never, or only during motion (default). Switch this to always if you want active position correction at all times and to never if you're doing checkout with the TwinCAT NC GUI. |
| `nBrakeMode` | `ENUM_StageBrakeMode` | Disable the brake when the axis is enabled (default), or when it is in the standstill state. Note that this does nothing unless a brake is linked to `bBrakeRelease`. |
| `nHomingMode` | `ENUM_EpicsHomeCmd` | Pick which switch to home to, or not to require homing (default) |
| `bGantryMode` | `BOOL` | Set to `TRUE` to activate gantry EPS |
| `nGantryTol` | `LINT` | If the gantry error is greater than this number of encoder counts, trigger a virtual limit. |
| `nEncRef` | `ULINT` | Encoder count for gantry motion where the two axes are aligned. |

## Provided Resources
| Resource | Type | Usage |
| --- | --- | --- |
| `DUT_MotionStage` | struct | Contains all relevant information about a single axis. You can pass this around and manipulate it inside of other function blocks. It relys on `FB_MotionStage` to provide the logic. |
| `DUT_PositionState` | struct | Contains all information about a specific position state, e.g. "out" |
| `FB_MotionStage` | function block | Provides a connection to ESS's motion library for motor record functionality, as well as some standard handling of brake and auto enable/disable. |
| `FB_MotionStageSim` | function block | Shortcut to getting a simulated axis running. |
| `FB_MotionRequest` | function block | Moves an axis handled by `FB_MotionStage` to a specific position. |
| `FB_PositionStateMove` | function block | Moves an axis to a specific position state. |
| `FB_PositionStateManager` | function block | Moves an axis to any one of 15 preset position states. Intended for EPICS use. |
| `FB_EpicsInOut` | function block | Example usage of `FB_PositionStateManager` for a simple in/out device. |
| `FB_PositionStateLock` | function block | Allows states to be immutable if configured as such |
| `ENUM_EpicsHomeCmd ` | enum | Options for axis homing through the motor record |
| `ENUM_EpicsMotorCmd` | enum | Options for axis commands through the motor record. You can use these through TwinCAT too. |
| `ENUM_StageBrakeMode` | enum | Options for axis brake mode. Brake can be enabled at standstill or at disabled. |
| `Enum_StageEnableMode` | enum | Options for axis enable/disable handling. Axis can be enabled always, never, or only during motion. |


