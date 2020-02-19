#!/usr/bin/env python
import os.path

import logging
from pcdsdevices.epics_motor import BeckhoffAxis
from qtpy.QtWidgets import QApplication
import typhon

logging.basicConfig(level=0)

motor = BeckhoffAxis('TST:PPM:MMS:Y', name='test_ppm')
macros = {'name': motor.name,
          'prefix': motor.prefix}

app = QApplication([])
typhon.use_stylesheet()
dirname, _ = os.path.split(os.path.abspath(__file__))
template = dirname + '/detailed_beckhoff_motor.ui'
suite = typhon.TyphonSuite.from_device(motor)
suite.get_subdisplay(motor).load_template(macros=macros)
suite.get_subdisplay(motor).force_template = template
suite.show()
app.exec_()
