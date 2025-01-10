echo "Deleting assets"
echo "Asset state set to archived"
yq eval '.state = "archived"' out_yaml/Asset.yaml > tmp.yaml && axway central apply -f tmp.yaml
rm tmp.yaml
echo "Asset state set to archived"
axway central delete -f out_yaml/Asset.yaml
echo "Assets deleted."