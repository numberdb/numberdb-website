#Needs to be run from numberdb-website/
#Afterwards run: sage -python data_pipeline/build-oeis.py

cd data_pipeline
mkdir oeis-data
cd oeis-data

wget https://oeis.org/stripped.gz
wget https://oeis.org/names.gz
gunzip -f *.gz

cd ../..
