import tornado.web
import tornado.escape
import Server
server = Server.Server()
from User import User
from TavernUtils import memorise
from TavernUtils import TavernCache
import TavernUtils
import urllib.parse
from bs4 import BeautifulSoup
import time


class BaseHandler(tornado.web.RequestHandler):

    """
    The BaseHandler is the baseclass for all objects in the webserver.
    It is not expected to ever be instantiated directly.
    It's main uses are:
        * Handle Cookies/logins
        * Allow modules to update just PARTS of the page
    """

    def __init__(self, *args, **kwargs):
        """Wrap the default RequestHandler with extra methods."""
        self.html = ""
        super().__init__(*args, **kwargs)

        # Set the canonical URL, if possible.
        self.canon = None

        # Ensure we don't run finish() twice.
        self._basefinish = False

        # If people are accessing a URL that isn't by the canonical URL,
        # redirect them.
        self.redirected = self.get_argument('redirected', False)

        # Is this necessary EVERY time? It's quick, I suppose...
        if server.serversettings.settings['web_url'] is None:
            server.serversettings.settings['web_url'] = self.request.protocol + "://" + \
                (self.request.host or socket.gethostbyaddr(
                    socket.gethostbyname(socket.gethostname())))
            server.serversettings.saveconfig()

        # Add in a random fortune
        self.set_header("X-Fortune", str(server.fortune.random()))
        # Do not allow the content to load in a frame.
        # Should help prevent certain attacks
        self.set_header("X-FRAME-OPTIONS", "DENY")
        # Don't try to guess content-type.
        # This helps avoid JS sent in an image.
        self.set_header("X-Content-Type-Options", "nosniff")

        # http://cspisawesome.com/content_security_policies
        # self.set_header(
        #     "Content-Security-Policy-Report-Only",
        #     "default-src 'self'; script-src 'unsafe-inline' 'unsafe-eval' data 'self'; object-src 'none'; style-src 'self'; img-src *; media-src mediaserver; frame-src " +
        #     server.serversettings.settings[
        #         'embedserver'] +
        #     " https://www.youtube.com https://player.vimeo.com; font-src 'self'; connect-src 'self'")

        self.fullcookies = {}
        for cookie in self.request.cookies:
            self.fullcookies[cookie] = self.get_cookie(cookie)

        # Get the Browser version.
        if 'User-Agent' in self.request.headers:
            ua = self.request.headers['User-Agent']
            self.browser = server.browserdetector.parse(ua)
        else:
            self.browser = server.browserdetector.parse("Unknown")

    # @memorise(parent_keys=['fullcookies', 'user.UserSettings'], ttl=server.serversettings.settings['cache']['templates']['seconds'], maxsize=server.serversettings.settings['cache']['templates']['size'])
    def render_string(self, template_name, **kwargs):
        """Overwrite the default render_string to ensure the "server" variable
        is always available to templates."""
        arguments = dict(
            server=server,
            browser=self.browser,
            request=self.request,
            user=self.user,
            serversettings=server.serversettings
        )
        arguments.update(kwargs)
        theme = 'default'
        # Only accept valid templates
        if 'theme' in self.user.UserSettings:
            if self.user.UserSettings['theme'] in server.availablethemes:
                theme = self.user.UserSettings['theme']
        return super().render_string(theme + '/' + template_name, **arguments)

    def write(self, html):
        if hasattr(html, 'decode'):
            self.html += html.decode('utf-8')
        else:
            self.html += html

    def gettext(self):
        ptext = ""
        for a in self.pagetext:
            ptext = ptext + a
        self.write(ptext)

    def get_argument(self, *args, **kwargs):
        """Overwrite the default get_argument to always HTML escape strings."""
        results = super().get_argument(*args, **kwargs)
        if type(results) in [bytes, str, None]:
            results = tornado.escape.xhtml_escape(results)
        return results

    def finish(self, divs=['wrappertable'], message=None):
        """Pulls in appropriate divs and serves them out via JS if possible.
        This saves bits, and keeps the columns as you left them.

        Finish() is a function defined by tornado, so this will be
        called automatically if not included manually.

        """

        # Don't run this function twice. If we're called a second time, get the
        # frig out.
        if self._basefinish:
            return

        self._basefinish = True

        # First off, we may be at the wrong URL. Check to see if this is the canonical version of this URL.
        # If it's not, and it's safe, go there.
        if not self.redirected:
            if self.request.method == "GET":
                if (self.canon is not None):
                    # Break apart current and canonical URLs to check to see if
                    # they match.
                    canon_scheme, canon_netloc, canon_path, canon_query_string, canon_fragment = urllib.parse.urlsplit(
                        server.serversettings.settings['web_url'] + '/' + self.canon)
                    orig_scheme, orig_netloc, orig_path, orig_query_string, orig_fragment = urllib.parse.urlsplit(
                        self.request.full_url())
                    if (orig_path != canon_path) or (orig_scheme != canon_scheme) or (orig_netloc != canon_netloc):
                        # This is not the canonical URL, bounce us.
                        # Merge canon with current url
                        query_params = urllib.parse.parse_qs(orig_query_string)
                        query_params['redirected'] = ['True']
                        fixed_query_string = urllib.parse.urlencode(
                            query_params, doseq=True)

                        newurl = urllib.parse.urlunsplit(
                            (canon_scheme,
                             canon_netloc,
                             canon_path,
                             fixed_query_string,
                             canon_fragment))
                        self.redirected = True
                        self.redirect(newurl)
                        return super().finish(message)

        # If they ask for the JS version, we'll calculate it.
        if "js" in self.request.arguments:

            if "divs" in self.request.arguments:
                # if they just want one, just give them that one.
                client_div = self.get_argument('divs')
                divs = tornado.escape.xhtml_escape(client_div).split(',')
            # Send the header information with the new name, then each div,
            # then the footer.
            super(BaseHandler, self).write(self.getjssetup())
            for div in divs:
                print("For Div - " + div)
                super(BaseHandler, self).write(self.getjselement(div))
            super(BaseHandler, self).write(self.getjsfooter())

        # GetOnly is used to request only specific divs.
        # And example is requesting the message reply inline.
        elif "getonly" in self.request.arguments:
            client_get = self.get_argument('getonly')
            get = tornado.escape.xhtml_escape(client_get)
            super(BaseHandler, self).write(self.getdiv(get))

        # If we're here, send the whole page as a regular view.
        else:
            super(BaseHandler, self).write(self.html)

        if "js" in self.request.arguments:
            self.set_header("Content-Type", "application/json")

        return super().finish(message)

    @memorise(parent_keys=['html'], ttl=server.serversettings.settings['cache']['getpagelemenent']['seconds'], maxsize=server.serversettings.settings['cache']['getpagelemenent']['size'])
    def getdiv(self, element):
        print("getting" + element)
        soup = BeautifulSoup(self.html, "html.parser")
        soupyelement = soup.find(id=element)
        soupytxt = ""
        if soupyelement is not None:
            for child in soupyelement.contents:
                soupytxt += str(child)
        return soupytxt

    @memorise(parent_keys=['request.uri', 'html'], ttl=server.serversettings.settings['cache']['templates']['seconds'], maxsize=server.serversettings.settings['cache']['templates']['size'])
    def getjssetup(self):
        # Strip out GET params we don't need to display to the user.
        urlargs = urllib.parse.parse_qs(
            self.request.query,
            keep_blank_values=True)
        print(urlargs)
        if 'timestamp' in urlargs:
            del urlargs['timestamp']
        if 'divs' in urlargs:
            del urlargs['divs']
        if 'js' in urlargs:
            del urlargs['js']
        newargs = urllib.parse.urlencode(urlargs, doseq=True)
        modifiedurl = self.request.path + newargs

        try:
            soup = BeautifulSoup(self.html, "html.parser")
        except:
            print('malformed data in BeautifulSoup')
            raise
        if soup.html is not None:
            # Need to escape, since BS4 turns this back into evil html.
            newtitle = tornado.escape.xhtml_escape(
                soup.html.head.title.string.rstrip().lstrip())
        else:
            print("No Title?!??!?!")
            print(self.html)
            newtitle = "Error"

        ret = '''
                var tavern_setup = function()
                {
                    var stateObj =
                    {
                        title: document.title,
                        url: window.location.pathname
                    };
                    document.title = "''' + newtitle + ''' ";
                    if (typeof history.pushState !== "undefined")
                    {
                        window.history.pushState(stateObj, "","''' + modifiedurl + '''");
                    }
                };
                '''

        return (ret)

    #@memorise(parent_keys=['request.uri', 'html'], ttl=server.serversettings.settings['cache']['getpagelemenent']['seconds'], maxsize=server.serversettings.settings['cache']['getpagelemenent']['size'])
    def getjselement(self, element):
        """Get the element text, remove all linebreaks, and escape it up.

        Then, send that as a document replacement Also, rewrite the
        document history in the browser, so the URL looks normal.

        """
        print("Your element is " + str(element))
        try:
            soup = BeautifulSoup(self.html, "html.parser")
        except:
            print('malformed data in BeautifulSoup')
            raise
        soupyelement = soup.find(id=element)
        soupytxt = str(soupyelement)
        escapedtext = soupytxt.replace("\"", "\\\"")
        escapedtext = escapedtext.replace("\n", "")

        return (
            ('jQuery("#' + element + '").replaceWith("' + escapedtext + '");')
        )

    def getjsfooter(self):
        # The stuff at the bottom of the JS file.
        ret = '''
                jQuery('#spinner').hide();
                jQuery('.spinner').removeClass("spinner");
                tavern_setup();
                tavern_setup =  null;
                ''' + TavernCache.cache['instance.js']
        return(ret)

    def recentauth(self, seconds=300):
        """Ensure the user has authenticated recently.

        To be used for things like change-password.

        """
        currenttime = int(time.time())

        if 'lastauth' in self.user.UserSettings:
            if currenttime - self.user.UserSettings['lastauth'] > seconds:
                print("User has not logged in recently. ;( ")
                return False
            else:
                print("Last login - " + str(currenttime -
                      self.user.UserSettings['lastauth']) + " seconds ago")
                return True
        else:
            # The user has NEVER logged in.
            print("Never Logged in Before")
            return True

    def setvars(self):
        """
        Saves out the current userid to a cookie
        These are encrypted using the built-in Tornado cookie encryption.
        """

        # If we're over https, ensure the cookie can't be read over HTTP
        if self.request.protocol == 'https':
            secure = True
        else:
            secure = False
        # Save our out passkey
        if self.user.UserSettings['status']['guest'] is False:
            if self.user.passkey is not None:
                self.set_secure_cookie(
                    "tavern_passkey",
                    self.user.passkey,
                    httponly=True,
                    expires_days=999)
        else:
            print(self.user.UserSettings['status']['guest'])

        if self.user.UserSettings['author_sha512'] is not None:
            # Delete our sensetive data before saving out.
            self.user.savemongo()
            self.set_secure_cookie(
                "tavern_settings",
                self.user.UserSettings['author_sha512'],
                httponly=True,
                expires_days=999)

        else:
            print(self.user.UserSettings['author_sha512'])

    def getvars(self, AllowGuestKey=True):
        """Retrieve the basic user variables out of your cookies."""
        self.user = User()
        # Load in our session token if we have one.
        userid = self.get_secure_cookie("tavern_settings")

        loaded = False
        if userid is not None:
            loaded = self.user.load_mongo_by_sha512(userid.decode('utf-8'))

        if loaded is False:
            # Either no cookie, or bad cookie. Either way, abort.
            self.clear_all_cookies()
            self.set_cookie("_xsrf", self.xsrf_token)
            self.user = User()

        # Get the passkey to unlock our privkey
        passkey = self.get_secure_cookie("tavern_passkey")
        if passkey is not None:
            self.user.passkey = passkey

        # Ensure our user has all expected fields
        # This method will also generate a key if necessary.
        if self.user.generate(AllowGuestKey=AllowGuestKey):
            self.setvars()

        # Check to see if we have support for datauris in our browser.
        # If we do, send the first ~10 pages with datauris.
        # After that switch back, since caching the images is likely to be
        # better, if you're a recurrent reader
        if not 'datauri' in self.user.UserSettings:
            if TavernUtils.randrange(1, 10) == 5:
                self.user.UserSettings['datauri'] = False
        if 'datauri' in self.user.UserSettings:
            self.user.datauri = self.user.UserSettings['datauri']
        elif self.browser['ua_family'] == 'IE' and self.browser['ua_versions'][0] < 8:
            self.user.datauri = False
        elif self.browser['ua_family'] == 'IE' and self.browser['ua_versions'][0] >= 8:
            self.user.datauri = True
        else:
            self.user.datauri = True
        if 'datauri' in self.request.arguments:
            if self.get_argument("datauri").lower() == 'true':
                self.user.datauri = True
            elif self.get_argument("datauri").lower() == 'false':
                self.user.datauri = False

        return self.user.UserSettings['username']

    def write_error(self, status_code, **kwargs):
        """Errors?

        We don't need no stinkin errors. Just ignore for now, redirect.

        """
        self.write(
            self.render_string(
                'header.html',
                title="Error",
                canon="/error",
                type="topic",
                rsshead=None))
        self.write(self.render_string('error.html', topic='sitecontent'))
        self.write(self.render_string('footer.html'))
