"""
Base Django settings for NumberDB.

Environment-specific overrides live in `dev.py` and `prod.py`.
"""

from pathlib import Path
from decouple import config, Csv
import dj_database_url
import os
from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-secondary',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}


# Build paths inside the project like this: BASE_DIR / 'subdir'.
# This settings module lives at `numberdb/settings/`, so the repository root is
# three levels up: `numberdb/settings/base.py` -> `numberdb/settings` -> `numberdb` -> repo root.
BASE_DIR = Path(__file__).resolve(strict=True).parents[2]


SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL')
    )
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    #allauth providers:
    #'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.github',
    'anymail',
    #'userprofile.apps.UserProfileConfig',
    'numberdb_app.apps.NumberdbAppConfig',
    #'db',
    #'crispy_forms',
    #'bootstrap4',
    'widget_tweaks',
]

#CRISPY_TEMPLATE_PACK = 'uni_form'
#CRISPY_TEMPLATE_PACK = 'bootstrap4'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'numberdb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'numberdb' / 'templates',
            BASE_DIR / 'numberdb_app' / 'templates',
            BASE_DIR / 'userprofile' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request', #allauth
            ],
        },
    },
]

WSGI_APPLICATION = 'numberdb.wsgi.application'
ASGI_APPLICATION = 'numberdb.asgi.application'


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

# allauth:
SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'APP': {
            'client_id': config('SOCIALACCOUNT_GITHUB_ID'),
            'secret': config('SOCIALACCOUNT_GITHUB_SECRET'),
            'key': ''
        },
        #'SCOPE': [
        #    'user',
        #],
    },
}

#### email ####
#
# Three separate things had to be wrong at once for mail to be as broken as it
# was, and all three were:
#
#   * anymail was installed with no configuration block and no key;
#   * production set EMAIL_BACKEND to the console backend explicitly, which
#     would have overridden a key even if one had been present;
#   * env/.env.prod.example documented EMAIL_MG_API_KEY, which no code has ever
#     read, so filling it in would have changed nothing.
#
# The provider is now chosen by which key is present, so setting the key is the
# whole configuration. Mailgun is preferred because numberdb.org's sending
# domain is already verified there; Resend works identically if it is ever
# swapped. With neither key, mail goes to the console, which is correct in
# development and honest about delivering nothing.
#
# EMAIL_BACKEND still overrides everything, which is a footgun worth knowing
# about rather than removing: it is what a developer needs to silence mail
# locally, and it is exactly how production came to deliver nothing.

#EMAIL_MG_* is the spelling env/.env.prod.example has always used; the
#MAILGUN_* names are accepted too, since that is what Anymail's own
#documentation says and the difference is otherwise a puzzle.
MAILGUN_API_KEY = (config('EMAIL_MG_API_KEY', default='')
                   or config('MAILGUN_API_KEY', default=''))
#Only needed for the EU region, where the host is api.eu.mailgun.net. Sending
#to the wrong region fails authentication with a message that does not say so.
MAILGUN_API_URL = (config('EMAIL_MG_API_BASE_URL', default='')
                   or config('MAILGUN_API_URL', default='')
                   or 'https://api.mailgun.net/v3')
#The verified sending domain, which is not necessarily the site's domain.
MAILGUN_SENDER_DOMAIN = (config('EMAIL_MG_SENDER_DOMAIN', default='')
                         or config('MAILGUN_SENDER_DOMAIN', default=''))

RESEND_API_KEY = config('RESEND_API_KEY', default='')

ANYMAIL = {}
if MAILGUN_API_KEY:
    ANYMAIL['MAILGUN_API_KEY'] = MAILGUN_API_KEY
    ANYMAIL['MAILGUN_API_URL'] = MAILGUN_API_URL
    if MAILGUN_SENDER_DOMAIN:
        ANYMAIL['MAILGUN_SENDER_DOMAIN'] = MAILGUN_SENDER_DOMAIN
if RESEND_API_KEY:
    ANYMAIL['RESEND_API_KEY'] = RESEND_API_KEY

if MAILGUN_API_KEY:
    _default_email_backend = 'anymail.backends.mailgun.EmailBackend'
elif RESEND_API_KEY:
    _default_email_backend = 'anymail.backends.resend.EmailBackend'
else:
    _default_email_backend = 'django.core.mail.backends.console.EmailBackend'

EMAIL_BACKEND = config('EMAIL_BACKEND', default=_default_email_backend)

#Sent from the verified sending domain. A subdomain is preferable to the apex,
#so that a deliverability problem cannot damage the reputation of the domain
#the website itself is served from.
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL',
                            default='NumberDB <noreply@mg.numberdb.org>')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

#### allauth ####
#Spelled in the modern settings; the older ACCOUNT_AUTHENTICATION_METHOD,
#ACCOUNT_EMAIL_REQUIRED, ACCOUNT_SIGNUP_EMAIL_ENTER_TWICE and
#ACCOUNT_LOGIN_ATTEMPTS_* are deprecated in allauth 65 and were each raising a
#warning on every start.
ACCOUNT_LOGIN_METHODS = {'username', 'email'}

#: Whether an address must be confirmed before the account can be used.
#: Read from the environment so it can be turned on the moment mail is known to
#: be delivering, and not a moment before: making it mandatory while mail is
#: broken locks every new user out of the account they just created.
ACCOUNT_EMAIL_VERIFICATION = config('ACCOUNT_EMAIL_VERIFICATION',
                                    default='optional')

#: An address is collected at signup but not required, matching the previous
#: behaviour. The trailing '*' marks a field required; add one to 'email' when
#: accounts start owning content.
ACCOUNT_SIGNUP_FIELDS = ['email', 'username*', 'password1*', 'password2*']

#Not named ACCOUNT_EMAIL_REQUIRED: allauth warns on that name even when the
#value agrees with ACCOUNT_SIGNUP_FIELDS. Kept as a plain local because the
#social settings below are derived from it.
_email_required = 'email*' in ACCOUNT_SIGNUP_FIELDS
ACCOUNT_CONFIRM_EMAIL_ON_GET = True #email providers commonly use GET
ACCOUNT_DEFAULT_HTTP_PROTOCOL = config('ACCOUNT_DEFAULT_HTTP_PROTOCOL')
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[NumberDB]"
#ACCOUNT_FORMS #Perhaps adjust in the future
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False #Don't need to login if user immediately confirms their email address
ACCOUNT_LOGOUT_ON_GET = False #Not fully safe, as users may get logged out by trolls in certain ways, but it should be fine.
ACCOUNT_LOGOUT_REDIRECT_URL ='/'
ACCOUNT_USERNAME_MAX_LENGTH = 20
ACCOUNT_SESSION_REMEMBER = True #Always remember session
#ACCOUNT_SIGNUP_FORM_CLASS #Perhaps in future, for additional input fields
#ACCOUNT_SIGNUP_REDIRECT_URL = "welcome/"
#ACCOUNT_USER_DISPLAY #Perhaps in future
ACCOUNT_USERNAME_MIN_LENGTH = 1

SOCIALACCOUNT_AUTO_SIGNUP = _email_required
SOCIALACCOUNT_EMAIL_VERIFICATION = False #No need, as we trust that github already did thta
#SOCIALACCOUNT_FORMS #Perhaps later
SOCIALACCOUNT_QUERY_EMAIL = _email_required
SOCIALACCOUNT_STORE_TOKENS = False

LOGIN_REDIRECT_URL = '/'

ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS=7
#Five failures per day per account, as before, in the modern spelling.
ACCOUNT_RATE_LIMITS = {
    'login_failed': '5/24h',
}

# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static'), ]


# Search by number answers "I measured this, is it known?", so a value known
# too weakly to identify anything is left out of it -- see
# numberdb_app/search.py. This is the relative precision required: 1e-5 is
# about five significant digits.
#
# Applied at query time against a stored measurement, so it can be changed
# freely without rebuilding anything; only which rows are returned changes.
# Values excluded by it are marked in the tables, so a reader can see why a
# number cannot be found.
NUMBERDB_MAX_RELATIVE_WIDTH = float(
    os.environ.get('NUMBERDB_MAX_RELATIVE_WIDTH', '1e-5'))


# API rate limits, per caller per window. Anonymous callers are limited so that
# one script cannot monopolise the sandboxed evaluator, which is the most
# expensive thing the server does; an API key raises the limit and makes the
# caller identifiable, which is the point of having one.
#
# Only /api/* is limited: the site's own pages never call it.
NUMBERDB_ANONYMOUS_RATE_LIMIT = int(
    os.environ.get('NUMBERDB_ANONYMOUS_RATE_LIMIT', '60'))
NUMBERDB_IDENTIFIED_RATE_LIMIT = int(
    os.environ.get('NUMBERDB_IDENTIFIED_RATE_LIMIT', '1000'))
NUMBERDB_RATE_LIMIT_WINDOW = int(
    os.environ.get('NUMBERDB_RATE_LIMIT_WINDOW', '3600'))
