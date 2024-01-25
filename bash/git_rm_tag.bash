#!/bin/bash

VERSION_MAJOR=1
VERSION_MINOR=6
VERSION_PATCH=7

ver=$VERSION_MAJOR=1
# ver2=$VERSION_MAJOR=1

echo $ver

git push --delete origin $ver
git tag -d $ver

# # list tags:
# git ls-remote --tags origin
# git tag
