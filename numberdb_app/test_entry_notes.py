"""What a table says about one value should be visible under that value.

Every entry row has carried `extra_info` since the beginning, and the template
showed it only in the branch for entries with no number -- that is, only when
there was nothing to say it about. Nine thousand two hundred and fifty-two
comments across thirteen tables were stored and never displayed, including
"Value is only a heuristic estimate" on the Hausdorff dimensions and a link to
the curve in LMFDB on every elliptic curve entry.
"""

from django.test import TestCase

from .editing import create_table, publish_table


def a_table(**sections):
	document = {'Title': sections.pop('title', 'Notes probe'),
	            'Data properties': {'type': 'R'},
	            'Parameters': {'n': {'type': 'Z'}},
	            'Numbers': sections.pop('Numbers',
	                                    [{'params': {'n': '1'},
	                                      'number': '1.5',
	                                      'comment': 'only an estimate'}])}
	document.update(sections)
	table = create_table(document, via='orm')
	publish_table(table)
	return table


def rendered(body):
	"""The page as a reader sees it.

	The page ends with the whole table document inside an HTML comment, so an
	assertion against the raw body finds anything the table contains whether
	it was rendered or not -- the first version of these tests passed that
	way, before they tested anything. Everything from that dump on is cut.
	"""
	cut = body.find('<!--')
	while cut >= 0:
		closing = body.find('-->', cut)
		if closing < 0:
			break
		body = body[:cut] + body[closing + 3:]
		cut = body.find('<!--')
	return body


class AnEntrysOwnNoteIsShown(TestCase):

	def test_a_comment_appears_under_the_value(self):
		table = a_table()
		shown = rendered(self.client.get('/%s' % table.url).content.decode())
		self.assertIn('1.5', shown)
		self.assertIn('only an estimate', shown)

	def test_a_caveat_about_rigour_is_not_hidden(self):
		#The case that made this worth fixing: a value the author marked as an
		#estimate displayed as a bare number.
		table = a_table(
			title='Estimated things',
			Numbers=[{'params': {'n': '1'}, 'number': '2.5',
			          'comment': 'Value is only a heuristic estimate'}])
		shown = rendered(self.client.get('/%s' % table.url).content.decode())
		self.assertIn('heuristic estimate', shown)

	def test_a_table_may_ask_for_them_to_be_hidden(self):
		table = a_table(title='Quiet table',
		                **{'Display properties': {'entry notes': 'hidden'}})
		shown = rendered(self.client.get('/%s' % table.url).content.decode())
		self.assertIn('1.5', shown)
		self.assertNotIn('only an estimate', shown)

	def test_they_are_shown_unless_asked_otherwise(self):
		#Shown by default: an author who wrote something about a value meant
		#a reader to see it.
		table = a_table(title='Loud by default',
		                **{'Display properties': {'number-header': 'value'}})
		shown = rendered(self.client.get('/%s' % table.url).content.decode())
		self.assertIn('only an estimate', shown)

	def test_an_entry_that_points_elsewhere_still_shows_its_note(self):
		#The behaviour that already existed, which must not regress. An entry
		#with no number of its own is required to say where the number is --
		#the schema refuses one with neither a number nor an `equals` -- so
		#this is the shape that branch was written for.
		table = a_table(
			title='One value and one pointer',
			Numbers=[{'params': {'n': '1'}, 'number': '1.5'},
			         {'params': {'n': '2'}, 'equals': 'HREF{Pi}',
			          'comment': 'the same number, under its own name'}])
		shown = rendered(self.client.get('/%s' % table.url).content.decode())
		self.assertIn('the same number, under its own name', shown)
