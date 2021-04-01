# numberdb-website

Website and database builder for [numberdb.org](https://numberdb.org).

The raw data comes from a separate data repository [numberdb-data](https://github.com/bmatschke/numberdb-data).

## Installation for development

The following was tested in Ubuntu 20.
It will install various packages globally, see `makefile`.
Additionally it will install the git repository `numberdb-data` into the same parent folder.
You need to have [SageMath](sagemath.org) installed and `sage` in your path.

    git clone https://github.com/bmatschke/numberdb-website.git
    cd numberdb-website
    make install

After installation, run the local server via

    make run
    
and open http://localhost:8000/.

### Email backend and social logins

If functionality for sending emails and social logins via GitHub is needed, edit `.env` accordingly.
