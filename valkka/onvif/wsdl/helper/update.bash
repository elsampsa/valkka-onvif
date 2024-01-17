#!/bin/bash 
rm ../*
echo copyinf files to upper level directory
find . -type f ! \( -name "*.py" -o -name "*.ipynb" -o -name "*.bash" -name "*.md" \) -exec cp -v {} .. \;
