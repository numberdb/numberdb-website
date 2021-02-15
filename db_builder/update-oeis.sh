#Needs to be run from numberdb-website/
#Afterwards run sage db_builder/build-oeis.sage

cd db_builder
mkdir oeis-data
cd oeis-data

wget https://oeis.org/stripped.gz
wget https://oeis.org/names.gz
gunzip -f *.gz

cd ../..
