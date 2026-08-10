"""Taking your data with you, and leaving.

A privacy policy that promises access and erasure without implementing them is
a promise to answer emails, and it will be broken the first busy week. These
are the two rights people actually exercise, so they are buttons rather than a
mailbox.

The hard part is not deletion, it is deciding what deletion means here. The
edit history is the provenance of the numbers: it is how a reader finds out
which script produced a value and what was corrected since. Erasing a person's
revisions would silently rewrite published mathematics that other people cite,
and would leave tables whose current contents nothing explains.

So an account is deleted and its **contributions are kept and re-attributed**
to a placeholder account. Everything that identifies the person -- username,
email, linked GitHub account, API keys, bio, sessions -- is destroyed. What
survives is the fact that somebody, once, changed this table in this way, which
is a statement about a number rather than about a person.

That trade is spelled out on the privacy page, before anyone presses anything.
"""

from django.contrib.auth.models import User
from django.db import transaction

__all__ = ['export_account', 'delete_account', 'tombstone', 'TOMBSTONE_NAME']

#: The account that inherits a departed user's contributions. Not a real
#: account: it has an unusable password and is inactive, so it cannot be signed
#: into, and it is not created until the first deletion needs it.
TOMBSTONE_NAME = 'deleted-user'


def tombstone():
	"""The placeholder account, made on first use.

	Found by username, which is why that username is in
	ACCOUNT_USERNAME_BLACKLIST: if somebody could register it, they would
	inherit every departed contributor's revisions and the history would
	credit them with edits they had never seen.
	"""
	user, created = User.objects.get_or_create(
		username = TOMBSTONE_NAME,
		defaults = {'is_active': False, 'email': ''},
	)
	if created:
		#Not merely unset: an unusable password can never be matched, whereas
		#an empty one is a password.
		user.set_unusable_password()
		user.save(update_fields=['password'])
	elif user.is_active or user.has_usable_password():
		#It exists but is not the inert account this returns. Registration is
		#blocked, so this means the blacklist was changed or the row predates
		#it -- either way, adopting it silently would hand somebody else's
		#account a pile of revisions.
		raise ValueError(
			'%r exists as a real account and cannot be used as the '
			'placeholder for deleted accounts' % (TOMBSTONE_NAME,))
	return user


def export_account(user):
	"""Everything this account holds, as plain JSON-able data.

	Their own data only. The tables they edited are public and are not copied
	in here -- what belongs to the person is the record of what *they* did, and
	a dump of the corpus would bury it.
	"""
	profile = getattr(user, 'profile', None)

	data = {
		'exported': _now(),
		'account': {
			'username': user.get_username(),
			'email': user.email,
			'joined': user.date_joined,
			'last_login': user.last_login,
			'bio': getattr(profile, 'bio', '') or '',
		},
		#allauth keeps addresses separately from the User row, and the two can
		#differ -- a confirmed address here and a stale one there.
		'email_addresses': [],
		'linked_accounts': [],
		'api_keys': [],
		'edits': [],
		'wanted': [],
	}

	try:
		from allauth.account.models import EmailAddress

		data['email_addresses'] = [
			{'email': row.email, 'verified': row.verified,
			 'primary': row.primary}
			for row in EmailAddress.objects.filter(user=user)]
	except Exception:
		pass

	try:
		from allauth.socialaccount.models import SocialAccount

		#Never the token: this file is downloaded, emailed and left in
		#folders, and a token in it would be a credential in all three.
		data['linked_accounts'] = [
			{'provider': row.provider, 'uid': row.uid,
			 'connected': row.date_joined}
			for row in SocialAccount.objects.filter(user=user)]
	except Exception:
		pass

	data['api_keys'] = [
		{'label': key.label, 'begins': key.prefix, 'created': key.created,
		 'last_used': key.last_used, 'expires': key.expires,
		 'revoked': key.revoked}
		for key in user.api_keys.all()]

	data['edits'] = [
		{'table': revision.table.tid if revision.table_id else None,
		 'revision': revision.digest,
		 'when': revision.created,
		 'message': revision.message}
		for revision in user.table_revisions.select_related('table')
		                    .order_by('created')]

	try:
		data['wanted'] = [{'title': row.title} for row in user.wanteds.all()]
	except Exception:
		pass

	return data


@transaction.atomic
def delete_account(user):
	"""Remove the person, keep the contributions.

	One transaction: an account half deleted -- credentials gone, identity
	still attached -- is worse than either outcome, and is what a failure part
	way through would leave.
	"""
	keeper = tombstone()
	if user.pk == keeper.pk:
		raise ValueError('the placeholder account cannot be deleted')

	moved = {}

	#Contributions, moved rather than dropped. Each of these is content other
	#people read; only the name on it changes.
	moved['edits'] = user.table_revisions.update(author=keeper)
	moved['tables_created'] = user.tables_created.update(created_by=keeper)
	try:
		moved['comments'] = user.comments.update(author=keeper)
	except Exception:
		moved['comments'] = 0
	try:
		#Requests for tables are a shared wishlist. They would cascade away
		#with the account, taking other people's reason to write a table with
		#them.
		moved['wanted'] = user.wanteds.update(user=keeper)
	except Exception:
		moved['wanted'] = 0

	#Credentials and identity, destroyed.
	user.api_keys.all().delete()
	try:
		from allauth.account.models import EmailAddress

		EmailAddress.objects.filter(user=user).delete()
	except Exception:
		pass
	try:
		from allauth.socialaccount.models import SocialAccount, SocialToken

		SocialToken.objects.filter(account__user=user).delete()
		SocialAccount.objects.filter(user=user).delete()
	except Exception:
		pass

	_drop_sessions(user)

	#The profile is a OneToOne with CASCADE, so it goes with the row below.
	user.delete()
	return moved


def _drop_sessions(user):
	"""Sign the account out everywhere.

	Otherwise a browser holding a valid session cookie stays signed in as an
	account that no longer exists, which Django resolves to AnonymousUser --
	harmless, but it means "delete my account" did not end the session it was
	pressed from.
	"""
	try:
		from django.contrib.sessions.models import Session
		from django.utils import timezone

		wanted = str(user.pk)
		for session in Session.objects.filter(expire_date__gte=timezone.now()):
			if session.get_decoded().get('_auth_user_id') == wanted:
				session.delete()
	except Exception:
		#A cache- or cookie-backed session store has no table to walk. The
		#account is still gone; the stale cookie simply cannot be reached from
		#here.
		pass


def _now():
	from django.utils import timezone

	return timezone.now()
