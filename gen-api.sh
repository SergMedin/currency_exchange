#!/bin/sh

# Installing API-generator:
# $ brew install openapi-generator

openapi-generator generate -i api/openapi.yaml -g python-fastapi -o exchange-server
