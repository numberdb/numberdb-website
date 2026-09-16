"""An address that lost the mathematics it was about.

`slug_for` drops `$...$` from a title, because mathematics in an address reads
badly -- `Chebyshev polynomials of the first kind $T_n$` lives at
`Chebyshev_polynomials_of_the_first_kind`. Dropping it is right when the
mathematics is an ornament at the end and wrong when it is a term, and the
test for which was too narrow twice:

* `Ehrhart $h^*$-polynomials of the Birkhoff polytopes` became
  `Ehrhart-polynomials_of_the_Birkhoff_polytopes`, which differs from the
  Ehrhart table's address by one character and says nothing about $h^*$;
* `Faltings heights of elliptic curves over $\\mathbb{Q}$` became
  `Faltings_heights_of_elliptic_curves_over`, an address ending in a
  preposition with nothing after it.
"""
from django.test import TestCase

from .editing import slug_for


class AnAddressKeepsWhatTheTitleIsAbout(TestCase):

	def slug(self, title):
		return slug_for(title, taken=set())

	def test_mathematics_attached_to_a_word_is_part_of_that_word(self):
		self.assertEqual(
			self.slug('Ehrhart $h^*$-polynomials of the Birkhoff polytopes'),
			'Ehrhart_h-star-polynomials_of_the_Birkhoff_polytopes')

	def test_a_star_is_a_letter_here(self):
		#`h-polynomial` and `h*-polynomial` are different objects, so an
		#address that drops the star names the wrong one.
		self.assertIn('h-star', self.slug('Ehrhart $h^*$-polynomials of the '
		                                  'hypersimplices'))

	def test_an_address_does_not_end_in_a_preposition(self):
		for title, wanted in (
				('Faltings heights of elliptic curves over $\\mathbb{Q}$',
				 'over'),
				('Real periods of genus 2 curves over $\\mathbb{Q}$', 'over'),
				('Values of the Clausen functions $\\mathrm{Cl}_s$ at '
				 'rational multiples of $\\pi$', 'of')):
			with self.subTest(title=title):
				self.assertFalse(self.slug(title).endswith('_' + wanted))

	def test_an_ornament_at_the_end_still_drops(self):
		self.assertEqual(
			self.slug('Chebyshev polynomials of the first kind $T_n$'),
			'Chebyshev_polynomials_of_the_first_kind')

	def test_a_term_in_the_middle_still_survives(self):
		self.assertEqual(self.slug('$p$-adic logarithm of integers'),
		                 'p-adic_logarithm_of_integers')
		self.assertEqual(
			self.slug('Values of the Barnes $G$-function at rational numbers'),
			'Values_of_the_Barnes_G-function_at_rational_numbers')
