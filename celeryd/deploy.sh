#!/bin/bash

cp celeryd.config /etc/default/celeryd
chmod 644 /etc/default/celeryd

cp celeryd /etc/init.d/
chmod 755 /etc/init.d/celeryd

