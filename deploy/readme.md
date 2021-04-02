#Deploy numberdb

Start from fresh Ubuntu 20.04 LTS distribution. 
(Set custom password for root.)

Update distribution:

    sudo apt-get update
    sudo apt-get -y upgrade
    sudo apt-get -y install make

Add user numberdb:

    adduser numberdb
    gpasswd -a numberdb sudo
    sudo su - numberdb
    
Clone numberdb-website git repository:

    git clone https://github.com/bmatschke/numberdb-website.git
    cd numberdb-website

Run `make deploy`:

    make deploy

## Trouble shooting

If the last step `setup_certbot` fails, this might be because the DNS records for numberdb.org and/or www.numberdb.org are not yet set to the server's IP address yet.
After setting these, run the following to setup HTTPS certificates:
    
    sudo certbot --nginx
