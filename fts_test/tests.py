from django.utils import unittest
from fts_test.models import *
from pprint import pprint

class FTSTestCase(unittest.TestCase):
    def test_fts(self):
        b1 = Blog.objects.create(title='Berlusconi government abducted by aliens', body='In an unusual turn of events, the 34th government headed by now bicentenial italian playboy Silvio Berlusconi was abducted during an orgy at the royal palace')
        b2 = Blog.objects.create(title='bunga-bunga-bunga', body='A new game has been developed in the highest circles of the italian ruling class. It\'s an applied version of the famous "aristocrats" line of jokes. The use of alien costumes is optional.')
        b3 = Blog.objects.create(title='underage alien scandal', body='shocking developments in the so called "abduction". It seems it was all organized by Lele Mora. Dozens of underage girls dressed in "Shreck" costumes where simply participating to an erotic sharade. The so called "aliens" took Silvio Berlusconi in a hot-air baloon and started to undress while the national anthem was blasting from a perfectly configured hi-fi setup.')

        q1 = Blog.search_objects.search('abduction')
        self.assertIn(b1, q1)
        self.assertIn(b3, q1)
        self.assertEqual(len(q1), 2)

        q2 = Blog.search_objects.search('aliens')
        self.assertIn(b1, q2)
        self.assertIn(b2, q2)
        self.assertIn(b3, q2)
        self.assertEqual(len(q2), 3)
        
        # different order, word distance, and ranking
        q3 = Blog.search_objects.search('berlusconi alien', rank_field='rank')
        self.assertEqual(q3[0], b3)
        self.assertEqual(q3[1], b1)
        self.assertEqual(len(q3), 2)
        
        q4 = Blog.search_objects.search('italian', rank_field='rank')
        self.assertEqual(q4[0], b1)
        self.assertEqual(q4[1], b2)
        self.assertEqual(len(q4), 2)

        q5 = Blog.search_objects.search('alien', rank_field='rank', highlight_field='body')
        self.assertIn('<span>aliens</span>', q5[0].body_highlight)
        #for b in q5:
            #pprint(b.__dict__)

