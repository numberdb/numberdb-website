###############################
# Development & Deployment Makefile
# - Dev runs natively with Sage (`$(MANAGE)`)
# - Deployment uses Docker Compose and scripts in ./scripts
###############################

# FOR DEVELOPMENT:
#   make install        # first-time local setup
#   make run            # start Django dev server
#   make test           # run Django tests
#   make build_db_all   # build data tables (long)

# FOR DEPLOYMENT (Docker Compose):
#   make compose_up           # build and start containers
#   make compose_migrate      # run DB migrations in container
#   make compose_fetch_data   # fetch numberdb-data volume
#   make compose_logs         # tail logs
#
# Convenience wrappers around scripts/:
#   make deploy_quickstage REMOTE=user@host
#   make deploy_stage REMOTE=user@host [FLAGS="--no-build --no-wiki"]
#   make deploy_live REMOTE=user@host DOMAIN=example.org EMAIL=admin@example.org

include .env

.DEFAULT_GOAL := help

# Deploy convenience variables (can be set in .env as DEPLOY_*)
REMOTE ?= $(DEPLOY_REMOTE)
RPATH  ?= $(DEPLOY_RPATH)
DOMAIN ?= $(DEPLOY_DOMAIN)
EMAIL  ?= $(DEPLOY_EMAIL)

.PHONY: all help run test static fetch_data build_db_numbers build_db_wiki build_db_oeis build_db_all update_numbers migrations update setup_postgres reset_postgres install install_full install_packages install_sage_ubuntu compose_up compose_down compose_logs compose_migrate compose_fetch_data deploy_quickstage deploy_stage deploy_live deploy_status


all: help

help:
	@echo "Usage:"
	@echo "- Development:"
	@echo "    make install           # first-time setup"
	@echo "    make run               # Django dev server"
	@echo "    make test              # run Django tests"
	@echo "    make build_db_all      # build all data tables"
	@echo "- Docker Compose (local/server):"
	@echo "    make compose_up        # build and start containers"
	@echo "    make compose_migrate   # run migrations in container"
	@echo "    make compose_up_prod   # up with prod overrides (restart, auto-migrate)"
	@echo "    make compose_fetch_data# fetch numberdb-data"
	@echo "    make compose_logs      # tail logs"
	@echo "- Deploy scripts:"
	@echo "    make deploy_quickstage [REMOTE]            # uses DEPLOY_* from .env if set"
	@echo "    make deploy_stage [REMOTE FLAGS]           # uses DEPLOY_* from .env if set"
	@echo "    make deploy_live [REMOTE DOMAIN EMAIL]     # uses DEPLOY_* from .env if set"

run:
	#RUN
	$(MANAGE) runserver

test:
	#TEST
	$(MANAGE) test
	
run_eval:
    #RUN EVAL WORKER
    $(PYTHON) workers/eval.py

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
	- git -C '../' clone https://github.com/numberdb/numberdb-data.git	
	git -C '../numberdb-data/' pull

build_db_numbers:
    #BUILD DB NUMBERS
    $(PYTHON) data_pipeline/build.py
	
build_db_wiki:
    #BUILD DB WIKI
    $(PYTHON) data_pipeline/build-wikipedia.py

build_db_oeis:
    #BUILD DB OEIS
    ./data_pipeline/update-oeis.sh
    $(PYTHON) data_pipeline/build-oeis.py
	
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
	sudo -u postgres psql -c "ALTER USER u_numberdb WITH PASSWORD '${POSTGRES_KEY}'"	
	sudo -u postgres psql -c "ALTER USER u_numberdb CREATEDB;"	
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
	

install_sage_ubuntu:
	#INSTALL SAGE
	sudo apt-get install  sagemath sagemath-doc sagemath-jupyter
	
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
	#$(PIP) install pydriller
	$(PIP) install django-extensions
	#$(PIP) install pyhash

	sudo apt-get -y install postgresql postgresql-contrib

.env:
	cp env/.env.dev.example .env

install: .env
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

# ---- Docker Compose convenience ----
compose_up:
	# Build and start containers
	docker compose up -d --build

compose_down:
	# Stop containers
	docker compose down

compose_logs:
	# Tail logs
	docker compose logs -f

compose_migrate:
	# Run DB migrations inside container
	docker compose run --rm web sage -python manage.py migrate

compose_fetch_data:
	# Fetch/update numberdb-data into shared volume
	docker compose run --rm data-fetcher

compose_up_prod:
	# Build and start containers with production overrides
	docker compose -f docker-compose.yml -f deploy/compose/docker-compose.prod.yml up -d --build

# ---- Deployment wrappers (use scripts/) ----
deploy_quickstage:
	@if [ -z "$(REMOTE)" ]; then \
		echo "Set REMOTE or DEPLOY_REMOTE in .env"; exit 2; \
	fi
	scripts/deploy.sh quickstage $(REMOTE) $(if $(RPATH),$(RPATH),)

deploy_stage:
	@if [ -z "$(REMOTE)" ]; then \
		echo "Set REMOTE or DEPLOY_REMOTE in .env"; exit 2; \
	fi
	scripts/deploy.sh stage $(FLAGS) $(REMOTE) $(if $(RPATH),$(RPATH),)

deploy_live:
	@if [ -z "$(REMOTE)" ] || [ -z "$(DOMAIN)" ] || [ -z "$(EMAIL)" ]; then \
		echo "Set REMOTE/DOMAIN/EMAIL or DEPLOY_* in .env"; exit 2; \
	fi
	scripts/deploy.sh live $(REMOTE) $(DOMAIN) $(EMAIL) $(if $(RPATH),$(RPATH),)

deploy_status:
    @if [ -z "$(REMOTE)" ]; then \
        echo "Set REMOTE or DEPLOY_REMOTE in .env"; exit 2; \
    fi
    scripts/deploy.sh status $(REMOTE) $(if $(RPATH),$(RPATH),)
