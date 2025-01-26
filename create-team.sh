#!/bin/bash

# Dependencies: yq (YAML processor), axway CLI

# Usage: ./create_team.sh team.yaml

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <yaml_file>"
    exit 1
fi

YAML_FILE=$1

# Check if yq is installed
if ! command -v yq &> /dev/null; then
    echo "Error: yq is not installed. Install it from https://github.com/mikefarah/yq"
    exit 1
fi

# Extract values from YAML
ORG=$(yq e '.team.org' "$YAML_FILE")
NAME=$(yq e '.team.name' "$YAML_FILE")
TAGS=$(yq e '.team.tags[]' "$YAML_FILE" | awk '{print "--tag " $0}')

# Validate required fields
if [ -z "$ORG" ] || [ -z "$NAME" ]; then
    echo "Error: 'org' and 'name' must be specified in the YAML file."
    exit 1
fi

# Build and execute the CLI command
CMD="axway team create \"$ORG\" \"$NAME\" $TAGS"

echo "Executing: $CMD"
eval $CMD