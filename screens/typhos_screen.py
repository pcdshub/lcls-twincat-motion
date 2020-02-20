#!/usr/bin/env python
import argparse
import logging
import os.path
import sys

from qtpy.QtWidgets import QApplication

from pcdsdevices.epics_motor import BeckhoffAxis
import typhos

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Launch a Typhos Beckhoff'
                                                 'Motor Screen')
    parser.add_argument('pvname', help='Base motor record pv name')
    parser.add_argument('--loglevel', default=20, help='Python logging level')

    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)

    motor = BeckhoffAxis(args.pvname, name=args.pvname.replace(':', '_'))
    macros = {'name': motor.name,
              'prefix': motor.prefix}

    app = QApplication([])
    typhos.use_stylesheet()
    dirname, _ = os.path.split(os.path.abspath(__file__))
    template = dirname + '/detailed_beckhoff_motor.ui'
    suite = typhos.TyphosSuite.from_device(motor)
    suite.get_subdisplay(motor).load_template(macros=macros)
    suite.get_subdisplay(motor).force_template = template
    suite.show()
    app.exec_()
