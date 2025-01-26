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

# Step 1: Create support contact
if prompt_user "Create support contact"; then
    echo "Creating support contact..."
    axway central create -f out_yaml/SupportContact.yaml
    echo "Support contact created."
fi

# Step 2: Create product
if prompt_user "Create product"; then
    echo "Creating product..."
    axway central create -f out_yaml/Product.yaml
    echo "Product created."
fi

# Step 3: Create product documentation
if prompt_user "Create product documentation"; then
    echo "Creating product documentation..."
    axcentral create -f out_yaml/Document.yaml
    echo "Product documentation created."
fi

# Step 4: Create product plan
if prompt_user "Create product plan"; then
    echo "Creating product plan..."
    axway central create -f out_yaml/ProductPlan.yaml -y
    echo "Product plan created."
fi

# Step 5: Create product plan quota
if prompt_user "Create product plan quota"; then
    echo "Creating product plan quota..."
    axway central create -f out_yaml/Quota.yaml -y
    echo "Product plan quota created."
fi

# Step 6: Create product release
if prompt_user "Create product release"; then
    echo "Creating product release..."
    axway central create -f out_yaml/ReleaseTag-Product-aj-product-cli.yaml -y
    echo "Product release created."
fi

echo "Script completed."