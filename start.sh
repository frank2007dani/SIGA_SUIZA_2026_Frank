#!/bin/sh
if [ -f ./start_railway.sh ]; then
    exec sh ./start_railway.sh
fi
exec sh siga_backend/start_railway.sh
