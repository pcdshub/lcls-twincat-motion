#!/bin/bash
find lcls-twincat-motion -regextype posix-extended -regex '.*\.(TcPOU|TcDUT)$' | grep -v tc_mca_std_lib
