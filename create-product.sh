echo "Creating support contact..."
axway central create -f out_yaml/SupportContact.yaml
echo "Support contact created."

echo "Creating product..."
axway central create -f out_yaml/Product.yaml
echo "Product created."

echo "Creating product documentation..."
axcentral create -f out_yaml/Document.yaml
echo "Product documentation created."

echo "Creating product plan..."
axway central create -f out_yaml/ProductPlan.yaml -y
echo "Product plan created."

echo "Creating product plan quota..."
axway central create -f out_yaml/Quota.yaml -y
echo "Product plan quota created."

# echo "Creating product release..."
# axway central create -f out_yaml/ReleaseTag-Product-aj-product-cli.yaml -y
# echo "Product release created."

# echo "Updating state to active..."
# yq eval '.state = "active"' out_yaml/Product.yaml > tmp.yaml && axway central apply -f tmp.yaml
# rm tmp.yaml
# echo "State updated to active."