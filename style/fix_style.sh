#!/bin/bash
style/files.sh | xargs sed -i -e 's/\t/    /g'
style/files.sh | xargs sed -i -e 's/\s\+$//g'
