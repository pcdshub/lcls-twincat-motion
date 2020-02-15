#!/bin/bash
style/files.sh | xargs awk '/\t/' | wc -l
