#!/bin/bash
pyinstaller --onefile \
    --add-data=index.html:. \
    --add-data=login.html:. \
    --add-data=folder.svg:. \
    --add-data=unknown.svg:. \
    --add-data=upload.svg:. \
    share.py