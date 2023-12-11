#!/bin/bash 
rm ../*
find . -type f ! \( -name "*.py" -o -name "*.ipynb" -o -name "*.bash" \) -exec cp {} .. \;
