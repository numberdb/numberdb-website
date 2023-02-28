"""
Django settings for numberdb project.
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
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent


SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL')
    )
}


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    #allauth providers:
    #'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.github',
    'anymail',
    #'userprofile.apps.UserProfileConfig',
    'db.apps.DbConfig',
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
]

ROOT_URLCONF = 'numberdb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates', 
            BASE_DIR / 'numberdb' / 'templates',
            BASE_DIR / 'db' / 'templates',
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

#allauth:
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

#### allauth ####
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = 'optional' #"mandatory"
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
ACCOUNT_SIGNUP_EMAIL_ENTER_TWICE = False
#ACCOUNT_SIGNUP_REDIRECT_URL = "welcome/"
#ACCOUNT_USER_DISPLAY #Perhaps in future
ACCOUNT_USERNAME_MIN_LENGTH = 1

SOCIALACCOUNT_AUTO_SIGNUP = ACCOUNT_EMAIL_REQUIRED
SOCIALACCOUNT_EMAIL_VERIFICATION = False #No need, as we trust that github already did thta
#SOCIALACCOUNT_FORMS #Perhaps later
SOCIALACCOUNT_QUERY_EMAIL = ACCOUNT_EMAIL_REQUIRED
SOCIALACCOUNT_STORE_TOKENS = False

LOGIN_REDIRECT_URL = '/'

ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS=7
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 86400 # 1 day in seconds

#See warning in 
# https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-SECURE_PROXY_SSL_HEADER
#SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
#SECURE_SSL_REDIRECT = True
#SESSION_COOKIE_SECURE = True
#CSRF_COOKIE_SECURE = True
#TODO: Consider last item of
# https://docs.djangoproject.com/en/3.1/topics/security/#ssl-https

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

'''
#Mailgun via SMTP:
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = False

DEFAULT_FROM_EMAIL = 'Number Database <info@numberdb.org>'
EMAIL_SUBJECT_PREFIX = '[NumberDB] '
'''

EMAIL_BACKEND = config('EMAIL_BACKEND')

if EMAIL_BACKEND == "anymail.backends.mailgun.EmailBackend":
    #Mailgun via their API:
    ANYMAIL = {
        # (exact settings here depend on your ESP...)
        "MAILGUN_API_KEY": config('EMAIL_MG_API_KEY'),
        "MAILGUN_SENDER_DOMAIN": 'mg.numberdb.org',
    }
    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"  # or sendgrid.EmailBackend, or...
    DEFAULT_FROM_EMAIL = "info@numberdb.org"  # if you don't already have this in settings
    SERVER_EMAIL = "zeta3@numberdb.org"  # ditto (default from-email for Django errors)



#elif EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend"
#    pass
#
#else:
#    raise NotImplementedError("EMAIL_BACKEND not supported")


from datetime import date
from datetime import datetime

today = date.today()
now = datetime.now()

print("Loaded settings.py.",now)

'''
from django.core.mail import send_mail

print("test email:")

try:
  send_mail('Subject here','Here is the message.',DEFAULT_FROM_EMAIL,['benjaminmatschke@googlemail.com'],fail_silently=False)
  print("email sent!")
except Exception as e:
  print("exception during sending message")
  print(e.__class__)
  print(e)
'''

CSRF_TRUSTED_ORIGINS = [#'127.0.0.1:8000', 'localhost:8000', 
'https://numberdb.org', 'https://www.numberdb.org']
