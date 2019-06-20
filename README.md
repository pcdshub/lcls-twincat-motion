# lcls-twincat-motion
Twincat 3 Motion Control Utilities

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

You would then link your hardware as appropriate to `M1.Axis`, `M1.bLimFwd`, `M1.bLimBwd`, `M1.bHome`, and `M1.bBrake`.


## Provided Resources
| Resource | Type | Usage |
| --- | --- | --- |
| `DUT_MotionStage` | struct | Contains all relevant information about a single axis. You can pass this around and manipulate it inside of other function blocks. It relys on `FB_MotionStage` to provide the logic. |
| `FB_MotionStage` | function block | Provides a connection to ESS's motion library for motor record functionality, as well as some standard handling of brake and auto enable/disable. |
| `ENUM_EpicsHomeCmd ` | enum | Options for axis homing through the motor record |
| `ENUM_EpicsMotorCmd` | enum | Options for axis commands through the motor record. You can use these through TwinCAT too. |
| `ENUM_StageBrakeMode` | enum | Options for axis brake mode. Brake can be enabled at standstill or at disabled. |
| `Enum_StageEnableMode` | enum | Options for axis enable/disable handling. Axis can be enabled always, never, or only during motion. |

## Settings
`DUT_MotionStage` has the following settings:

| Setting | Type | Usage |
| --- | --- | --- |
| `bPowerSelf` | `BOOL` | If `TRUE`, this function block will call `MC_Power` based on the `bEnable` attribute in the struct. Otherwise, you'll have to call `MC_Power` somewhere else (perhaps for MPS) |
| `nEnableMode` | `INT` | Set to desired value of `ENUM_StageEnableMode` |
| `nBrakeMode` | `INT` | Set to desired value of `ENUM_StageBrakeMode` |
| `nHomingMode` | `INT` | Set to desired value of `ENUM_EpicsHomeCmd` |
