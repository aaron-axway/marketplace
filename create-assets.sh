#!/bin/bash

# Check for the --no-prompt or -y flag
NO_PROMPT=false
if [[ "$1" == "--no-prompt" || "$1" == "-y" ]]; then
    NO_PROMPT=true
fi

# Function to prompt the user
prompt_user() {
    if [[ "$NO_PROMPT" == false ]]; then
        read -p "Do you want to run '$1'? (Y/N): " response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            return 0  # Continue
        else
            return 1  # Skip
        fi
    else
        return 0  # Automatically continue if --no-prompt or -y is passed
    fi
}

# Step 1: Create assets
if prompt_user "Create assets"; then
    echo "Creating assets..."
    axway central create -f out_yaml/no-auto-release-Asset.yaml
    echo "Assets created."
fi

# Step 2: Create asset mappings
if prompt_user "Create asset mappings"; then
    echo "Creating asset mappings..."
    axway central create -f out_yaml/AssetMapping.yaml
    echo "Asset mappings created."
fi

# Step 3: Create asset access control list
if prompt_user "Create asset access control list"; then
    echo "Creating asset access control list ..."
    axway central create -f out_yaml/AccessControlList-Asset.yaml
    echo "Asset access control list created."
fi

# Step 4: Update API Service Instance
if prompt_user "Update API Service Instance"; then
    echo "Updating API Service Instance..."
    axway central apply -f out_yaml/APIServiceInstance.yaml --subresource lifecycle
    echo "API Service Instance updated."
fi

# Step 5: Update assets with auto release enabled
if prompt_user "Updating assets with auto release enabled"; then
    echo "Creating assets..."
    axway central apply -f out_yaml/Asset.yaml
    echo "Assets update to auto release."
fi

# Step 6: Create asset release
if prompt_user "Create asset release"; then
    echo "Creating asset release..."
    axway central create -f out_yaml/ReleaseTag-Asset-aj-asset-1-cli.yaml -y
    echo "Asset release created."
fi

echo "Script completed."