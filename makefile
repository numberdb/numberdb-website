#FOR DEVELOPMENT:
# make install #only needed the first time
# make run
#Instead of `make install`, one may also run `make install_full`.

#FOR DEPLOYMENT:
# make deploy

run:
	#RUN
	sage -python manage.py runserver

fetch_data:
	#FETCH DATA REPOSITORY
	- git -C '../' clone https://github.com/bmatschke/numberdb-data.git	
	git -C '../numberdb-data/' pull

build_db_numbers:
	#BUILD DB NUMBERS
	export PYTHONPATH='./:${PYTHONPATH}'
	#sage db_builder/build.sage #problems loading utils.utils
	sage -c 'load("db_builder/build.sage")'
	
build_db_wiki:
	#BUILD DB WIKI
	export PYTHONPATH='./:${PYTHONPATH}'
	sage -c 'load("db_builder/build-wikipedia.sage")'

build_db_oeis:
	#BUILD DB OEIS
	export PYTHONPATH='./:${PYTHONPATH}'
	./db_builder/update-oeis.sh
	sage -c 'load("db_builder/build-oeis.sage")'
	
build_db_all:
	#BUILD DB ALL
	make build_db_numbers
	make build_db_wiki
	make build_db_oeis
	
update_numbers:
	#UPDATE NUMBERS
	make fetch_data
	make build_db_numbers

migrations:
	#MIGRATIONS
	sage -python manage.py makemigrations
	sage -python manage.py migrate

setup_postgres:
	#SETUP POSTGRES
	- sudo -u postgres createuser u_numberdb
	sudo -u postgres psql -c "ALTER USER u_numberdb WITH PASSWORD '214312421342134213124'"	
	- sudo -u postgres createdb numberdb --owner u_numberdb
	make migrations
	
reset_postgres:
	#RESET POSTGRES
	#sudo su postgres
	#psql
	#drop database numberdb;
	#create database numberdb with owner u_numberdb;
	#\q
	#exit
	- sudo -u postgres dropdb numberdb
	make setup_postgres
	
install_sage_ubuntu:
	#INSTALL SAGE
	#TODO
	
install_packages:
	#INSTALL PACKAGES
	sudo apt-get install git libssl-dev libncurses5-dev libsqlite3-dev libreadline-dev libtk8.5 libgdm-dev libdb4o-cil-dev libpcap-dev
	sage -pip install django
	sage -pip install django-allauth
	sage -pip install django-db
	sage -pip install requests
	sage -pip install requests-oauthlib
	sage -pip install psycopg2-binary
	sage -pip install python-decouple
	sage -pip install dj-database-url
	sage -pip install "django-anymail[mailgun]"
	#sage -pip install django-crispy-forms
	#sage -pip install django-bootstrap4
	sage -pip install django-widget-tweaks
	sage -pip install gitpython
	sage -pip install pyyaml
	sage -pip install timeout-decorator
	sage -pip install func_timeout
	sage -pip install bs4
	sage -pip install pyro5
	#sage -pip install pydriller
	sage -pip install django-extensions
	sage -python manage.py makemigrations

	#Packages for deployment:

	sudo apt-get -y install postgresql postgresql-contrib
	sudo apt-get -y install nginx
	sudo apt-get -y install supervisor

	sudo apt-get install libpq-dev
	sage -pip install psycopg2
	sage -pip install gunicorn


install:
	#INSTALL
	make install_sage_ubuntu
	make install_packages
	
	make setup_postgres
	
	make migrations	
	
	make fetch_data
	
	#make build_db_all #takes long time
	make build_db_numbers 
	
install_full:
	#INSTALL FULL
	make install
	make build_db_wiki
	make build_db_oeis


setup_supervisor:
	#SETUP SUPERVISOR
	sudo systemctl enable supervisor
	sudo systemctl start supervisor
	#TODO

setup_nginx:
	#SETUP NGINX
	#TODO
	
setup_gunicorn:
	#SETUP GUNICORN
	#TODO
	
setup_git_deploy:
	#SETUP GIT
	git config --global user.name "zeta3"
	git config --global user.email zeta3@numberdb.org
	
deploy:
	#DEPLOY
	#TODO!!!
	make install_full
	make setup_git_deploy
	make setup_gunicorn
	make setup_supervisor
	make setup_nginx
