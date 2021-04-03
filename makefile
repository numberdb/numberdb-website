#FOR DEVELOPMENT:
# make install #only needed the first time
# make run
#Instead of `make install`, one may also run `make install_full`.

#FOR DEPLOYMENT:
# make deploy

SAGE=export PYTHONPATH=./:${PYTHONPATH}; sage
PYTHON=$(SAGE) -python
PIP=$(SAGE) -pip
MANAGE=$(PYTHON) manage.py

.PHONY: all help run static fetch_data build_db_numbers build_db_wiki build_db_oeis build_db_all update_numbers migrations update setup_postgres reset_postgres setup_gunicorn setup_nginx setup_supervisor setup_git_deploy install install_full install_packages install_sage_ubuntu20 deploy


all: help

help:
	@echo "Usage:"
	@echo "- For development:"
	@echo "    make install (only needed once)"
	@echo "    make run (run local server, after make install)"
	@echo "- For production:"
	@echo "    make deploy (using gunicorn and nginx)"

run:
	#RUN
	$(MANAGE) runserver

static:
	#STATIC
	$(MANAGE) collectstatic --noinput	

migrations:
	#MIGRATIONS
	$(MANAGE) makemigrations
	$(MANAGE) migrate

update: migrations static

fetch_data:
	#FETCH DATA REPOSITORY
	- git -C '../' clone https://github.com/bmatschke/numberdb-data.git	
	git -C '../numberdb-data/' pull

build_db_numbers:
	#BUILD DB NUMBERS
	$(SAGE) -c 'load("db_builder/build.sage")'
	#sage db_builder/build.sage #problems loading utils.utils
	
build_db_wiki:
	#BUILD DB WIKI
	$(SAGE) -c 'load("db_builder/build-wikipedia.sage")'

build_db_oeis:
	#BUILD DB OEIS
	./db_builder/update-oeis.sh
	$(SAGE) -c 'load("db_builder/build-oeis.sage")'
	
build_db_all:
	#BUILD DB ALL
	$(MAKE) build_db_numbers
	$(MAKE) build_db_wiki
	$(MAKE) build_db_oeis
	
update_numbers:
	#UPDATE NUMBERS
	$(MAKE) fetch_data
	$(MAKE) build_db_numbers

setup_postgres:
	#SETUP POSTGRES
	- sudo -u postgres createuser u_numberdb
	sudo -u postgres psql -c "ALTER USER u_numberdb WITH PASSWORD 'password2_to_be_changed'"	
	- sudo -u postgres createdb numberdb --owner u_numberdb
	$(MAKE) migrations
	
reset_postgres:
	#RESET POSTGRES
	#sudo su postgres
	#psql
	#drop database numberdb;
	#create database numberdb with owner u_numberdb;
	#\q
	#exit
	- sudo -u postgres dropdb numberdb
	$(MAKE) setup_postgres
	
../sage.tar.bz2:
	wget -O ../sage.tar.bz2 http://mirrors.mit.edu/sage/linux/64bit/sage-9.2-Ubuntu_20.04-x86_64.tar.bz2
	

install_sage_ubuntu20: ../sage.tar.bz2
	#INSTALL SAGE
	tar -C ../ -xjf ../sage.tar.bz2
	- sudo ln -s /usr/bin/python3 /usr/bin/python
	../SageMath/sage --version #Test sage
	- sudo ln -s /home/numberdb/SageMath/sage /usr/bin/sage
	
install_packages:
	#INSTALL PACKAGES
	sudo apt-get install git libssl-dev libncurses5-dev libsqlite3-dev libreadline-dev libtk8.6 libgdm-dev libdb4o-cil-dev libpcap-dev


install_django:
	export PATH='${HOME}/SageMath/:${PATH}'
	
	#wget https://bootstrap.pypa.io/get-pip.py
	#sudo $(PYTHON) get-pip.py
	#sudo $(PIP) install virtualenv
	
	$(PIP) install django
	$(PIP) install django-allauth
	$(PIP) install django-db
	$(PIP) install requests
	$(PIP) install requests-oauthlib
	$(PIP) install psycopg2-binary
	$(PIP) install python-decouple
	$(PIP) install dj-database-url
	$(PIP) install "django-anymail[mailgun]"
	#$(PIP) install django-crispy-forms
	#$(PIP) install django-bootstrap4
	$(PIP) install django-widget-tweaks
	$(PIP) install gitpython
	$(PIP) install pyyaml
	$(PIP) install timeout-decorator
	$(PIP) install func_timeout
	$(PIP) install bs4
	$(PIP) install pyro5
	#$(PIP) install pydriller
	$(PIP) install django-extensions

	#Packages for deployment:

	sudo apt-get -y install postgresql postgresql-contrib
	sudo apt-get -y install nginx
	sudo apt-get -y install supervisor

	$(PIP) install gunicorn
	sudo apt-get install libpq-dev
	$(PIP) install psycopg2


install:
	#INSTALL
	#$(MAKE) install_sage_ubuntu20 #Actually: Don't install sage here! Let user install it by themselves.

	$(MAKE) install_packages
	$(MAKE) install_django
	
	$(MAKE) setup_postgres
	
	$(MAKE) migrations	
	
	$(MAKE) fetch_data
	
	#$(MAKE) build_db_all #takes long time
	$(MAKE) build_db_numbers 
	
install_full:
	#INSTALL FULL
	$(MAKE) install
	$(MAKE) build_db_wiki
	$(MAKE) build_db_oeis


setup_supervisor:
	#SETUP SUPERVISOR
	sudo systemctl enable supervisor
	sudo systemctl start supervisor
	sudo cp deploy/supervisor/conf.d/pyro.conf /etc/supervisor/conf.d/pyro.conf
	sudo cp deploy/supervisor/conf.d/eval.conf /etc/supervisor/conf.d/eval.conf
	sudo cp deploy/supervisor/conf.d/numberdb.conf /etc/supervisor/conf.d/numberdb.conf
	sudo supervisorctl reread
	sudo supervisorctl update
	sudo supervisorctl restart pyro
	sudo supervisorctl restart eval
	sudo supervisorctl restart numberdb

setup_nginx:
	#SETUP NGINX
	- sudo rm /etc/nginx/sites-available/numberdb
	- sudo rm /etc/nginx/sites-enabled/numberdb
	sudo cp deploy/nginx/sites-available/numberdb /etc/nginx/sites-available/numberdb
	- sudo ln -s /etc/nginx/sites-available/numberdb /etc/nginx/sites-enabled/numberdb
	- sudo rm /etc/nginx/sites-enabled/default
	sudo service nginx restart
	
setup_dirs:
	#SETUP DIRS
	- mkdir ../logs
	- mkdir ../run
	- sudo chown numberdb ../run
	- touch ../logs/gunicorn.log
	
setup_git_deploy:
	#SETUP GIT
	git config --global user.name "zeta3"
	git config --global user.email zeta3@numberdb.org
	
setup_certbot:
	#SETUP CERTBOT
	sudo apt-get update
	#sudo apt-get install software-properties-common
	#sudo add-apt-repository ppa:certbot/certbot
	#sudo apt-get update
	#sudo apt-get install python-certbot-nginx
	
	sudo apt install snapd
	sudo snap install core
	sudo snap refresh core
	sudo apt-get remove certbot
	sudo snap install --classic certbot
	- sudo ln -s /snap/bin/certbot /usr/bin/certbot
	#sudo certbot --nginx #bad: changes nginx configuration file
	#sudo certbot certonly --nginx
	
	#OLD:
	sudo certbot --nginx
	#sudo crontab -e #add at the end of the file: 0 4 * * * /usr/bin/certbot renew --quiet

production_restart_server:
	sudo supervisorctl restart pyro
	sudo supervisorctl restart eval
	sudo supervisorctl restart numberdb
	sudo service nginx restart

deploy:
	#DEPLOY
	#TODO!!!

	#sudo apt-get update
	#sudo apt-get -y upgrade
	
	#adduser numberdb
	#gpasswd -a numberdb sudo
	
	#virtualenv venv -p sage
	#source venv/bin/activate
	
	#$(MAKE) install_packages
	$(MAKE) install_sage_ubuntu20
	
	$(MAKE) install_full
	$(MAKE) static
	#$(MANAGE) createsuperuser
	$(MAKE) setup_git_deploy
	
	$(MAKE) setup_dirs
	$(MAKE) setup_supervisor
	sleep 1
	$(MAKE) setup_nginx
	$(MAKE) setup_certbot

status:
	sudo supervisorctl status
