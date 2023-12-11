#!/bin/bash 
find . -type f ! \( -name "*.py" -o -name "*.ipynb" -o -name "*.bash" -o -name "*.md" \) -exec rm {} \;
