echo "Deleting product"
yq eval '.state = "archived"' out_yaml/Product.yaml > tmp.yaml && axway central apply -f tmp.yaml
rm tmp.yaml
echo "Product state set to archived"
axway central delete -f out_yaml/Product.yaml
echo "Product deleted."