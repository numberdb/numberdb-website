"""Startup checks for configuration that fails quietly.

Both checks here exist because of a real failure, not a hypothetical one.

GitHub login was configured, advertised on the login page, and could never have
worked: ``SOCIALACCOUNT_GITHUB_ID`` and ``SOCIALACCOUNT_GITHUB_SECRET`` were
empty in the server's environment, so allauth sent GitHub an empty client id.
The user sees a failed redirect and has no way to tell that from a network
problem, and the server logs nothing at all.

Mail was in the same state: ``anymail`` installed, no key, and production
running the console backend, so every confirmation message was written to the
container log and delivered to nobody. Nothing distinguished that from working.

Both are configuration absent rather than configuration wrong, which is the
kind of fault a system check is for.
"""

from django.conf import settings
from django.core.checks import Warning, register

__all__ = ['check_social_providers', 'check_email_can_be_delivered']

#Login is advertised only for providers that are actually installed, so an
#empty credential is always a mistake rather than a deliberate opt-out.
_CREDENTIAL_FIELDS = ('client_id', 'secret')


@register()
def check_social_providers(app_configs, **kwargs):
	"""A configured provider with no credentials cannot log anyone in."""
	problems = []
	providers = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {}) or {}
	for name, config in providers.items():
		app = (config or {}).get('APP') or {}
		missing = [f for f in _CREDENTIAL_FIELDS if not (app.get(f) or '').strip()]
		if not missing:
			continue
		problems.append(Warning(
			'Social login provider %r has no %s.'
			% (name, ' and no '.join(missing)),
			hint=('Set SOCIALACCOUNT_%s_ID and SOCIALACCOUNT_%s_SECRET in the '
			      'environment, or remove the provider from '
			      'SOCIALACCOUNT_PROVIDERS and INSTALLED_APPS. As it stands the '
			      'login button is shown and the redirect fails with nothing '
			      'logged.' % (name.upper(), name.upper())),
			id='numberdb.W001',
		))
	return problems


@register()
def check_email_can_be_delivered(app_configs, **kwargs):
	"""Account email that goes nowhere is worse than no account email.

	Only a warning: the console backend is the right thing in development, and
	this check runs there too. It becomes serious when verification is required,
	which is the one case where undelivered mail locks people out, so that
	combination is reported separately.
	"""
	problems = []
	backend = getattr(settings, 'EMAIL_BACKEND', '')
	delivers = not backend.endswith(
		('console.EmailBackend', 'locmem.EmailBackend', 'dummy.EmailBackend'))
	verification = getattr(settings, 'ACCOUNT_EMAIL_VERIFICATION', 'optional')

	if not delivers and not settings.DEBUG:
		problems.append(Warning(
			'EMAIL_BACKEND is %r, so no mail leaves this server.' % (backend,),
			hint=('Set RESEND_API_KEY in the environment. Note that an explicit '
			      'EMAIL_BACKEND in .env overrides the key, which is how '
			      'production came to run the console backend with account '
			      'email switched on.'),
			id='numberdb.W002',
		))

	if not delivers and verification == 'mandatory':
		problems.append(Warning(
			'Email verification is mandatory but EMAIL_BACKEND (%r) delivers '
			'nothing, so nobody can complete a signup.' % (backend,),
			hint='Configure delivery first, then set '
			     'ACCOUNT_EMAIL_VERIFICATION=mandatory.',
			id='numberdb.W003',
		))
	return problems
