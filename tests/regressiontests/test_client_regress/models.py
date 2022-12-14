# -*- coding: utf-8 -*-
"""
Regression tests for the Test Client, especially the customized assertions.
"""
import os
from django.conf import settings

from django.test import Client, TestCase
from django.core.urlresolvers import reverse
from django.core.exceptions import SuspiciousOperation
from django.template import TemplateDoesNotExist, TemplateSyntaxError

class AssertContainsTests(TestCase):
    def setUp(self):
        self.old_templates = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates'),)

    def tearDown(self):
        settings.TEMPLATE_DIRS = self.old_templates

    def test_contains(self):
        "Responses can be inspected for content, including counting repeated substrings"
        response = self.client.get('/test_client_regress/no_template_view/')

        self.assertNotContains(response, 'never')
        self.assertContains(response, 'never', 0)
        self.assertContains(response, 'once')
        self.assertContains(response, 'once', 1)
        self.assertContains(response, 'twice')
        self.assertContains(response, 'twice', 2)

        try:
            self.assertNotContains(response, 'once')
        except AssertionError, e:
            self.assertEquals(str(e), "Response should not contain 'once'")

        try:
            self.assertContains(response, 'never', 1)
        except AssertionError, e:
            self.assertEquals(str(e), "Found 0 instances of 'never' in response (expected 1)")

        try:
            self.assertContains(response, 'once', 0)
        except AssertionError, e:
            self.assertEquals(str(e), "Found 1 instances of 'once' in response (expected 0)")

        try:
            self.assertContains(response, 'once', 2)
        except AssertionError, e:
            self.assertEquals(str(e), "Found 1 instances of 'once' in response (expected 2)")

        try:
            self.assertContains(response, 'twice', 1)
        except AssertionError, e:
            self.assertEquals(str(e), "Found 2 instances of 'twice' in response (expected 1)")

        try:
            self.assertContains(response, 'thrice')
        except AssertionError, e:
            self.assertEquals(str(e), "Couldn't find 'thrice' in response")

        try:
            self.assertContains(response, 'thrice', 3)
        except AssertionError, e:
            self.assertEquals(str(e), "Found 0 instances of 'thrice' in response (expected 3)")

    def test_unicode_contains(self):
        "Unicode characters can be found in template context"
        #Regression test for #10183
        r = self.client.get('/test_client_regress/check_unicode/')
        self.assertContains(r, u'?????????')
        self.assertContains(r, '\xe5\xb3\xa0'.decode('utf-8'))

    def test_unicode_not_contains(self):
        "Unicode characters can be searched for, and not found in template context"
        #Regression test for #10183
        r = self.client.get('/test_client_regress/check_unicode/')
        self.assertNotContains(r, u'?????????')
        self.assertNotContains(r, '\xe3\x81\xaf\xe3\x81\x9f\xe3\x81\x91'.decode('utf-8'))

class AssertTemplateUsedTests(TestCase):
    fixtures = ['testdata.json']

    def test_no_context(self):
        "Template usage assertions work then templates aren't in use"
        response = self.client.get('/test_client_regress/no_template_view/')

        # Check that the no template case doesn't mess with the template assertions
        self.assertTemplateNotUsed(response, 'GET Template')

        try:
            self.assertTemplateUsed(response, 'GET Template')
        except AssertionError, e:
            self.assertEquals(str(e), "No templates used to render the response")

    def test_single_context(self):
        "Template assertions work when there is a single context"
        response = self.client.get('/test_client/post_view/', {})

        #
        try:
            self.assertTemplateNotUsed(response, 'Empty GET Template')
        except AssertionError, e:
            self.assertEquals(str(e), "Template 'Empty GET Template' was used unexpectedly in rendering the response")

        try:
            self.assertTemplateUsed(response, 'Empty POST Template')
        except AssertionError, e:
            self.assertEquals(str(e), "Template 'Empty POST Template' was not a template used to render the response. Actual template(s) used: Empty GET Template")

    def test_multiple_context(self):
        "Template assertions work when there are multiple contexts"
        post_data = {
            'text': 'Hello World',
            'email': 'foo@example.com',
            'value': 37,
            'single': 'b',
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view_with_template/', post_data)
        self.assertContains(response, 'POST data OK')
        try:
            self.assertTemplateNotUsed(response, "form_view.html")
        except AssertionError, e:
            self.assertEquals(str(e), "Template 'form_view.html' was used unexpectedly in rendering the response")

        try:
            self.assertTemplateNotUsed(response, 'base.html')
        except AssertionError, e:
            self.assertEquals(str(e), "Template 'base.html' was used unexpectedly in rendering the response")

        try:
            self.assertTemplateUsed(response, "Valid POST Template")
        except AssertionError, e:
            self.assertEquals(str(e), "Template 'Valid POST Template' was not a template used to render the response. Actual template(s) used: form_view.html, base.html")

class AssertRedirectsTests(TestCase):
    def test_redirect_page(self):
        "An assertion is raised if the original page couldn't be retrieved as expected"
        # This page will redirect with code 301, not 302
        response = self.client.get('/test_client/permanent_redirect_view/')
        try:
            self.assertRedirects(response, '/test_client/get_view/')
        except AssertionError, e:
            self.assertEquals(str(e), "Response didn't redirect as expected: Response code was 301 (expected 302)")

    def test_lost_query(self):
        "An assertion is raised if the redirect location doesn't preserve GET parameters"
        response = self.client.get('/test_client/redirect_view/', {'var': 'value'})
        try:
            self.assertRedirects(response, '/test_client/get_view/')
        except AssertionError, e:
            self.assertEquals(str(e), "Response redirected to 'http://testserver/test_client/get_view/?var=value', expected 'http://testserver/test_client/get_view/'")

    def test_incorrect_target(self):
        "An assertion is raised if the response redirects to another target"
        response = self.client.get('/test_client/permanent_redirect_view/')
        try:
            # Should redirect to get_view
            self.assertRedirects(response, '/test_client/some_view/')
        except AssertionError, e:
            self.assertEquals(str(e), "Response didn't redirect as expected: Response code was 301 (expected 302)")

    def test_target_page(self):
        "An assertion is raised if the response redirect target cannot be retrieved as expected"
        response = self.client.get('/test_client/double_redirect_view/')
        try:
            # The redirect target responds with a 301 code, not 200
            self.assertRedirects(response, 'http://testserver/test_client/permanent_redirect_view/')
        except AssertionError, e:
            self.assertEquals(str(e), "Couldn't retrieve redirection page '/test_client/permanent_redirect_view/': response code was 301 (expected 200)")

class AssertFormErrorTests(TestCase):
    def test_unknown_form(self):
        "An assertion is raised if the form name is unknown"
        post_data = {
            'text': 'Hello World',
            'email': 'not an email address',
            'value': 37,
            'single': 'b',
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")

        try:
            self.assertFormError(response, 'wrong_form', 'some_field', 'Some error.')
        except AssertionError, e:
            self.assertEqual(str(e), "The form 'wrong_form' was not used to render the response")

    def test_unknown_field(self):
        "An assertion is raised if the field name is unknown"
        post_data = {
            'text': 'Hello World',
            'email': 'not an email address',
            'value': 37,
            'single': 'b',
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")

        try:
            self.assertFormError(response, 'form', 'some_field', 'Some error.')
        except AssertionError, e:
            self.assertEqual(str(e), "The form 'form' in context 0 does not contain the field 'some_field'")

    def test_noerror_field(self):
        "An assertion is raised if the field doesn't have any errors"
        post_data = {
            'text': 'Hello World',
            'email': 'not an email address',
            'value': 37,
            'single': 'b',
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")

        try:
            self.assertFormError(response, 'form', 'value', 'Some error.')
        except AssertionError, e:
            self.assertEqual(str(e), "The field 'value' on form 'form' in context 0 contains no errors")

    def test_unknown_error(self):
        "An assertion is raised if the field doesn't contain the provided error"
        post_data = {
            'text': 'Hello World',
            'email': 'not an email address',
            'value': 37,
            'single': 'b',
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")

        try:
            self.assertFormError(response, 'form', 'email', 'Some error.')
        except AssertionError, e:
            self.assertEqual(str(e), "The field 'email' on form 'form' in context 0 does not contain the error 'Some error.' (actual errors: [u'Enter a valid e-mail address.'])")

    def test_unknown_nonfield_error(self):
        """
        Checks that an assertion is raised if the form's non field errors
        doesn't contain the provided error.
        """
        post_data = {
            'text': 'Hello World',
            'email': 'not an email address',
            'value': 37,
            'single': 'b',
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")

        try:
            self.assertFormError(response, 'form', None, 'Some error.')
        except AssertionError, e:
            self.assertEqual(str(e), "The form 'form' in context 0 does not contain the non-field error 'Some error.' (actual errors: )")

class LoginTests(TestCase):
    fixtures = ['testdata']

    def test_login_different_client(self):
        "Check that using a different test client doesn't violate authentication"

        # Create a second client, and log in.
        c = Client()
        login = c.login(username='testclient', password='password')
        self.failUnless(login, 'Could not log in')

        # Get a redirection page with the second client.
        response = c.get("/test_client_regress/login_protected_redirect_view/")

        # At this points, the self.client isn't logged in.
        # Check that assertRedirects uses the original client, not the
        # default client.
        self.assertRedirects(response, "http://testserver/test_client_regress/get_view/")

class URLEscapingTests(TestCase):
    def test_simple_argument_get(self):
        "Get a view that has a simple string argument"
        response = self.client.get(reverse('arg_view', args=['Slartibartfast']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'Howdy, Slartibartfast')

    def test_argument_with_space_get(self):
        "Get a view that has a string argument that requires escaping"
        response = self.client.get(reverse('arg_view', args=['Arthur Dent']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'Hi, Arthur')

    def test_simple_argument_post(self):
        "Post for a view that has a simple string argument"
        response = self.client.post(reverse('arg_view', args=['Slartibartfast']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'Howdy, Slartibartfast')

    def test_argument_with_space_post(self):
        "Post for a view that has a string argument that requires escaping"
        response = self.client.post(reverse('arg_view', args=['Arthur Dent']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'Hi, Arthur')

class ExceptionTests(TestCase):
    fixtures = ['testdata.json']

    def test_exception_cleared(self):
        "#5836 - A stale user exception isn't re-raised by the test client."

        login = self.client.login(username='testclient',password='password')
        self.failUnless(login, 'Could not log in')
        try:
            response = self.client.get("/test_client_regress/staff_only/")
            self.fail("General users should not be able to visit this page")
        except SuspiciousOperation:
            pass

        # At this point, an exception has been raised, and should be cleared.

        # This next operation should be successful; if it isn't we have a problem.
        login = self.client.login(username='staff', password='password')
        self.failUnless(login, 'Could not log in')
        try:
            self.client.get("/test_client_regress/staff_only/")
        except SuspiciousOperation:
            self.fail("Staff should be able to visit this page")

class TemplateExceptionTests(TestCase):
    def setUp(self):
        self.old_templates = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = ()

    def tearDown(self):
        settings.TEMPLATE_DIRS = self.old_templates

    def test_no_404_template(self):
        "Missing templates are correctly reported by test client"
        try:
            response = self.client.get("/no_such_view/")
            self.fail("Should get error about missing template")
        except TemplateDoesNotExist:
            pass

    def test_bad_404_template(self):
        "Errors found when rendering 404 error templates are re-raised"
        settings.TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'bad_templates'),)
        try:
            response = self.client.get("/no_such_view/")
            self.fail("Should get error about syntax error in template")
        except TemplateSyntaxError:
            pass

# We need two different tests to check URLconf substitution -  one to check
# it was changed, and another one (without self.urls) to check it was reverted on
# teardown. This pair of tests relies upon the alphabetical ordering of test execution.
class UrlconfSubstitutionTests(TestCase):
    urls = 'regressiontests.test_client_regress.urls'

    def test_urlconf_was_changed(self):
        "TestCase can enforce a custom URLconf on a per-test basis"
        url = reverse('arg_view', args=['somename'])
        self.assertEquals(url, '/arg_view/somename/')

# This test needs to run *after* UrlconfSubstitutionTests; the zz prefix in the
# name is to ensure alphabetical ordering.
class zzUrlconfSubstitutionTests(TestCase):
    def test_urlconf_was_reverted(self):
        "URLconf is reverted to original value after modification in a TestCase"
        url = reverse('arg_view', args=['somename'])
        self.assertEquals(url, '/test_client_regress/arg_view/somename/')

class SessionTests(TestCase):
    fixtures = ['testdata.json']

    def test_session(self):
        "The session isn't lost if a user logs in"
        # The session doesn't exist to start.
        response = self.client.get('/test_client_regress/check_session/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'NO')

        # This request sets a session variable.
        response = self.client.get('/test_client_regress/set_session/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'set_session')

        # Check that the session has been modified
        response = self.client.get('/test_client_regress/check_session/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'YES')

        # Log in
        login = self.client.login(username='testclient',password='password')
        self.failUnless(login, 'Could not log in')

        # Session should still contain the modified value
        response = self.client.get('/test_client_regress/check_session/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'YES')

    def test_logout(self):
        """Logout should work whether the user is logged in or not (#9978)."""
        self.client.logout()
        login = self.client.login(username='testclient',password='password')
        self.failUnless(login, 'Could not log in')
        self.client.logout()
        self.client.logout()

class UnicodePayloadTests(TestCase):
    def test_simple_unicode_payload(self):
        "A simple ASCII-only unicode JSON document can be POSTed"
        # Regression test for #10571
        json = u'{"english": "mountain pass"}'
        response = self.client.post("/test_client_regress/parse_unicode_json/", json,
                                    content_type="application/json")
        self.assertEqual(response.content, json)

    def test_unicode_payload_utf8(self):
        "A non-ASCII unicode data encoded as UTF-8 can be POSTed"
        # Regression test for #10571
        json = u'{"dog": "????????????"}'
        response = self.client.post("/test_client_regress/parse_unicode_json/", json,
                                    content_type="application/json; charset=utf-8")
        self.assertEqual(response.content, json.encode('utf-8'))

    def test_unicode_payload_utf16(self):
        "A non-ASCII unicode data encoded as UTF-16 can be POSTed"
        # Regression test for #10571
        json = u'{"dog": "????????????"}'
        response = self.client.post("/test_client_regress/parse_unicode_json/", json,
                                    content_type="application/json; charset=utf-16")
        self.assertEqual(response.content, json.encode('utf-16'))

    def test_unicode_payload_non_utf(self):
        "A non-ASCII unicode data as a non-UTF based encoding can be POSTed"
        #Regression test for #10571
        json = u'{"dog": "????????????"}'
        response = self.client.post("/test_client_regress/parse_unicode_json/", json,
                                    content_type="application/json; charset=koi8-r")
        self.assertEqual(response.content, json.encode('koi8-r'))
