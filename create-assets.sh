echo "Creating assets..."
axway central create -f out_yaml/Asset.yaml
echo "Assets created."

echo "Creating asset mappings..."
axway central create -f out_yaml/AssetMapping.yaml
echo "Asset mappings created."

echo "Creating asset access control list ..."
axway central create -f out_yaml/AccessControlList-Asset.yaml
echo "Asset access control list created."

echo "Creating asset release..."
axway central create -f out_yaml/ReleaseTag-Asset-aj-asset-1-cli.yaml -y
echo "Asset release created."

echo "Updating state to active..."
yq eval '.state = "active"' out_yaml/Asset.yaml > tmp.yaml && axway central apply -f tmp.yaml
rm tmp.yaml
echo "State updated to active."