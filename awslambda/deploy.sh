#!/bin/bash
set -e

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

cd $DIR

rm -f thumbnailer.zip

zip -r thumbnailer.zip CreateThumbnail.js node_modules

aws lambda update-function-code \
	--function-name CreateThumbnail \
	--zip-file fileb://$(pwd)/thumbnailer.zip
