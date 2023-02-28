# Deploy numberdb

Start from fresh Ubuntu 22.04 LTS distribution. 
(Set custom password for root.)

Update distribution:

    sudo apt-get update
    sudo apt-get -y upgrade
    sudo apt-get -y install make

Add user `numberdb`:

    adduser numberdb
    gpasswd -a numberdb sudo
    sudo su - numberdb
    
Clone git repository [numberdb-website](https://github.com/numberdb/numberdb-website):

    git clone https://github.com/numberdb/numberdb-website.git
    cd numberdb-website

Create default `.env`:

    make .env

Change settings in `.env`, especially passwords and paths, `DEBUG=FALSE`, and if desired: add server's IP address to `ALLOWED_HOSTS`, and add github social auth and mailgun credentials:

    vim .env
    vim makefile

Run `make deploy`:

    make deploy

## Setting up domain

- DNS records:

    Type: A record, Host: @, Value: (the IP address), TLL: Automatic
    Type: A record, Host: www, Value: (the IP address), TLL: Automatic
    or: 
    Type: CNAME record, Host: www, Value: @, TLL: Automatic

- email forwarding

## Setting up social auth via GitHub



## Trouble shooting

If the last step `setup_certbot` fails, this might be because the DNS records for `numberdb.org` and/or `www.numberdb.org` are not yet set to the server's IP address yet.
After setting these, run the following to setup HTTPS certificates:
    
    sudo certbot --nginx

