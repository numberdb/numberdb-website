"""Account behaviour that differs from allauth's defaults.

Currently one thing: where replies to account email should go.

Mail is sent from ``noreply@mg.numberdb.org``, which is right for the envelope
(the sending domain is the one Mailgun has verified, and DKIM has to align with
it), but wrong as a destination. ``mg.numberdb.org`` exists to send. A person
who receives a confirmation message and replies to it is writing to a human,
and without a Reply-To that reply goes to the sending subdomain and is
discarded in silence.

So the From stays on the verified domain and the Reply-To points at the address
the site actually advertises.
"""

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings

__all__ = ['AccountAdapter']


class AccountAdapter(DefaultAccountAdapter):
	"""Adds a Reply-To to every message allauth sends."""

	def render_mail(self, template_prefix, email, context, headers=None):
		message = super().render_mail(template_prefix, email, context,
		                              headers=headers)
		reply_to = getattr(settings, 'ACCOUNT_REPLY_TO', '')
		#Set on the message rather than passed as a header, because Django
		#refuses a Reply-To given both ways and raises rather than choosing.
		if reply_to and not message.reply_to:
			message.reply_to = [reply_to]
		return message
