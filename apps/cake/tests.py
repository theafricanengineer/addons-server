from django.contrib.auth.models import AnonymousUser

from mock import Mock
from test_utils import TestCase
from pyquery import PyQuery as pq

from cake.models import Session
from users.models import UserProfile
from cake.backends import SessionBackend
from cake.helpers import cake_csrf_token


class CakeTestCase(TestCase):

    fixtures = ['cake/sessions.json', 'base/global-stats']

    def test_login(self):
        """
        Given a known remora cookie, can we visit the homepage and appear
        logged in?
        """
        # log in using cookie -
        client = self.client
        client.cookies['AMOv3'] = "17f051c99f083244bf653d5798111216"
        response = client.get('/en-US/firefox/')
        self.assertContains(response, 'Welcome, Scott')

        # test that the data copied over correctly.
        profile = UserProfile.objects.get(pk=1)
        user = profile.user

        self.assertEqual(profile.firstname, user.first_name)
        self.assertEqual(profile.lastname, user.last_name)
        self.assertEqual(profile.email, user.username)
        self.assertEqual(profile.email, user.email)
        self.assertEqual(profile.created, user.date_joined)
        self.assertEqual(profile.password, user.password)
        self.assertEqual(profile.id, user.id)

    def test_stale_session(self):
        # what happens if the session we reference is expired
        session = Session.objects.get(pk='27f051c99f083244bf653d5798111216')
        self.assertEqual(False, self.client.login(session=session))
        # check that it's no longer in the db
        f = lambda: Session.objects.get(pk='27f051c99f083244bf653d5798111216')
        self.assertRaises(Session.DoesNotExist, f)

    def test_invalid_session_reference(self):
        self.assertEqual(False, self.client.login(session=Session(pk='abcd')))

    def test_invalid_session_data(self):
        # what happens if the session we reference refers to a missing user
        session = Session.objects.get(pk='37f051c99f083244bf653d5798111216')
        self.assertEqual(False, self.client.login(session=session))
        # check that it's no longer in the db
        f = lambda: Session.objects.get(pk='37f051c99f083244bf653d5798111216')
        self.assertRaises(Session.DoesNotExist, f)

    def test_backend_get_user(self):
        s = SessionBackend()
        self.assertEqual(None, s.get_user(12))

    def test_middleware_invalid_session(self):
        client = self.client
        client.cookies['AMOv3'] = "badcookie"
        response = client.get('/en-US/firefox/')
        assert isinstance(response.context['user'], AnonymousUser)

    def test_logout(self):
        # login with a cookie and verify we are logged in
        client = self.client
        client.cookies['AMOv3'] = "17f051c99f083244bf653d5798111216"
        response = client.get('/en-US/firefox/')
        self.assertContains(response, 'Welcome, Scott')
        # logout and verify we are logged out and our AMOv3 cookie is gone
        response = client.get('/en-US/firefox/users/logout')
        response = client.get('/en-US/firefox/')

        assert isinstance(response.context['user'], AnonymousUser)
        self.assertEqual(client.cookies.get('AMOv3').value, '')


class TestHelpers(TestCase):

    fixtures = ['cake/sessions.json']

    def test_csrf_token(self):
        mysessionid = "17f051c99f083244bf653d5798111216"

        s = SessionBackend()
        session = Session.objects.get(pk=mysessionid)
        user = s.authenticate(session=session)

        client = self.client
        client.cookies['AMOv3'] = mysessionid

        request = Mock()
        request.user = user
        request.COOKIES = client.cookies
        ctx = {'request': request}

        doc = pq(cake_csrf_token(ctx))
        self.assert_(doc.html())
        self.assert_(doc('input').attr('value'))
