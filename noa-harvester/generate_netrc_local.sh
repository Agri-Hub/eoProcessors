echo "Checking required env vars"
echo "---"

env_vars="COPERNICUS_LOGIN COPERNICUS_PASSWORD EARTHDATA_LOGIN EARTHDATA_PASSWORD"
for that_var in $env_vars; do
    if [ ! -v $that_var ]; then
        echo "Warning: $that_var env var does not exist"
    fi
done

echo "---"

credentials_copernicus="machine https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token login $COPERNICUS_LOGIN password $COPERNICUS_PASSWORD"
credentials_earthdata="machine urs.earthdata.nasa.gov login $EARTHDATA_LOGIN password $EARTHDATA_PASSWORD"
file="${HOME}/.netrc"

if [ -f "$file" ]; then
    echo "$file exists."
    echo "Please append the following lines to it if needed (checking login/password keys have correct values)"
    echo "example: machine xxx login xxx password xxx"
    echo ""
    echo "$credentials_copernicus"
    echo "$credentials_earthdata"
else
    echo "Creating $file file. Please make sure your credentials are correct"
    echo "$credentials_copernicus" >> "$file"
    echo "$credentials_earthdata" >> "$file"
    chmod 600 "$file"
fi