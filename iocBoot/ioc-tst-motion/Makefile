IOC_TOP = /reg/g/pcds/epics/ioc/common/ads-ioc/R0.2.1
IOC_INSTANCE_PATH := $(shell pwd)

# Set PRODUCTION_IOC to 1 to move from a testing to a production IOC:
PRODUCTION_IOC := 0

PROJECT_NAME = lcls-twincat-motion
PROJECT_PATH := ../../lcls-twincat-motion/lcls-twincat-motion.tsproj
PLC = Example

PYTMC_OPTS :=
PREFIX = PLC:TST:MOT

include $(IOC_TOP)/iocBoot/templates/Makefile.base
