# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from ujson import loads

from tornado import gen
from tornado.httpclient import HTTPError

from holmes.models import User
from holmes.handlers import BaseHandler


class AuthenticateHandler(BaseHandler):

    def get(self):
        '''
        Only returns true or false if is a valid authenticated request
        '''
        self.set_status(200)
        if self.is_authenticated()[0]:
            self.write('true')
        else:
            self.write('false')

    @gen.coroutine
    def post(self):
        '''
        Try to authenticate user if the provider and access_token POST data.
        If the `self.authenticate` method returns the user, create a JSON
        Web Token (JWT) and set a `HOLMES_AUTH_TOKEN` cookie with the encoded
        value. Otherwise returns a unauthorized request.
        '''
        post_data = loads(self.request.body)

        provider = post_data.get('provider')
        access_token = post_data.get('access_token')

        user = yield self.authenticate(provider, access_token)
        if user:

            # http://self-issued.info/docs/draft-ietf-oauth-json-web-token.html
            # #RegisteredClaimName
            payload = dict(
                sub=user.email,
                iss=user.provider,
                token=access_token,
                iat=datetime.utcnow(),
                exp=datetime.utcnow() + timedelta(
                    seconds=self.config.SESSION_EXPIRATION
                )
            )
            auth_token = self.jwt.encode(payload)

            self.set_cookie('HOLMES_AUTH_TOKEN', auth_token)
            self.write('OK')
        else:
            self.set_unauthorized()

    @gen.coroutine
    def authenticate(self, provider, access_token):
        '''
        Authenticate user with the given access_token on the specific
        provider method. If it returns the user data, try to fetch the user
        on the database or create user if it doesnt exist and then return
        the user object. Otherwise, returns None, meaning invalid
        authentication parameters.
        '''

        if provider == u'GooglePlus':
            oauth_user = yield self.authenticate_on_google(access_token)
        # elif provider == u'Facebook':
            # oauth_user = yield self.authenticate_on_facebook(access_token)
        else:
            oauth_user = None

        if oauth_user:
            db = self.application.db
            user = User.by_email(oauth_user['email'], db)
            if user:
                user.last_login = datetime.utcnow()
                db.flush()
                db.commit()
            else:
                user = User.add_user(
                    db, oauth_user['fullname'], oauth_user['email'], provider,
                    datetime.utcnow()
                )
        else:
            user = None

        raise gen.Return(user)

    # @gen.coroutine
    # def authenticate_on_facebook(self, access_token):
        # logging.info('Authenticating on Facebook...')
        # pass

    @gen.coroutine
    def authenticate_on_google(self, access_token):
        '''
        Try to get Google user info and returns it if
        the given access_token get`s a valid user info in a string
        json format. If the response was not an status code 200 or
        get an error on Json, None was returned.

        Example of return on success:
        {
            id: "1234567890abcdef",
            email: "...@gmail.com",
            fullname: "Ricardo L. Dani",
        }
        '''

        response = yield self._fetch_google_userinfo(access_token)

        if response.code == 200:
            body = loads(response.body)
            if not body.get('error'):
                raise gen.Return({
                    'email': body.get("email"),
                    'fullname': body.get("name"),
                    'id': body.get("id")
                })

        raise gen.Return(None)

    @gen.coroutine
    def _fetch_google_userinfo(self, access_token):
        google_api_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
        url = '%s?access_token=%s' % (google_api_url, access_token)

        try:
            response = yield self.application.http_client.fetch(
                url,
                proxy_host=self.application.config.HTTP_PROXY_HOST,
                proxy_port=self.application.config.HTTP_PROXY_PORT
            )
        except HTTPError, e:
            response = e.response

        raise gen.Return(response)
