# Deploy numberdb

Start from fresh Ubuntu 20.04 LTS distribution. 
(Set custom password for root.)

Update distribution:

    sudo apt-get update
    sudo apt-get -y upgrade
    sudo apt-get -y install make

Add user `numberdb`:

    adduser numberdb
    gpasswd -a numberdb sudo
    sudo su - numberdb
    
Clone git repository [numberdb-website](https://github.com/bmatschke/numberdb-website):

    git clone https://github.com/bmatschke/numberdb-website.git
    cd numberdb-website

Make local copy of `.env`:

    cp deploy/default-dotenv-deploy .env

Change settings in `.env` and `makefile`, especially passwords, `DEBUG=FALSE`, and if desired add server's IP address to `ALLOWED_HOSTS`:

    vim .env
    vim makefile

Run `make deploy`:

    make deploy

## Trouble shooting

If the last step `setup_certbot` fails, this might be because the DNS records for `numberdb.org` and/or `www.numberdb.org` are not yet set to the server's IP address yet.
After setting these, run the following to setup HTTPS certificates:
    
    sudo certbot --nginx
