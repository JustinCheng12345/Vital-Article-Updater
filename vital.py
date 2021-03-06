#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
An incomplete sample script.

This is not a complete bot; rather, it is a template from which simple
bots can be made. You can rename it to mybot.py, then edit it in
whatever way you want.

Use global -simulate option for test purposes. No changes to live wiki
will be done.

The following parameters are supported:

&params;

-always           The bot won't ask for confirmation when putting a page

-text:            Use this text to be added; otherwise 'Test' is used

-replace:         Dont add text but replace it

-top              Place additional text on top of the page

-summary:         Set the action summary message for the edit.
"""
#
# (C) Pywikibot team, 2006-2018
#
# Distributed under the terms of the MIT license.
#
from __future__ import absolute_import, unicode_literals

import pywikibot
from pywikibot.data.api import Request
from pywikibot import pagegenerators

from pywikibot.bot import (SingleSiteBot, ExistingPageBot, NoRedirectPageBot, AutomaticTWSummaryBot)
import os, re, json, time, collections

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {
    '&params;': pagegenerators.parameterHelp
}


class BasicBot(
    # Refer pywikobot.bot for generic bot classes
    SingleSiteBot,  # A bot only working on one site
    # CurrentPageBot,  # Sets 'current_page'. Process it in treat_page method.
    #                  # Not needed here because we have subclasses
    ExistingPageBot,  # CurrentPageBot which only treats existing pages
    NoRedirectPageBot,  # CurrentPageBot which only treats non-redirects
    AutomaticTWSummaryBot,  # Automatically defines summary; needs summary_key
):

    summary_key = 'vital-modifying'

    def __init__(self, generator, **kwargs):
        """
        Constructor.

        @param generator: the page generator that determines on which pages
            to work
        @type generator: generator
        """
        # Add your own options to the bot and set their defaults
        # -always option is predefined by BaseBot class
        self.availableOptions.update({
            'internalonly': False,  # Update using only using local information
            'externalonly': None,  # Update using enwiki
        })

        # call constructor of the super class
        super(BasicBot, self).__init__(site=True, **kwargs)

        # assign the generator to the bot
        self.generator = generator
        self.sandbox = False

        # generate a dict of classes for easier determination of the quality of the article
        def map_nested_dicts(ob, func):
            if isinstance(ob, collections.Mapping):
                return {k: map_nested_dicts(v, func) for k, v in ob.items()}
            else:
                return func(ob)
        self.assessment_list, self.high_quality_list, self.former_list, self.high_quality_talk_list = {}, {}, {}, {}
        cache_file_name = "cache/vital_data.json"
        if os.path.exists(cache_file_name) and (time.time() - os.path.getmtime(cache_file_name) <= 86400):
            pywikibot.output("Cache found, loading cache.")
            with open(cache_file_name, 'r') as file:
                temp_json = json.loads(file.read())
                self.assessment_list = map_nested_dicts(temp_json["assessment"],
                                                        lambda v: [pywikibot.Category(self.site, title=s) for s in v])
                self.high_quality_list = map_nested_dicts(temp_json["high_quality"],
                                                          lambda v: [pywikibot.Page(self.site, title=s) for s in v])
                self.former_list = map_nested_dicts(temp_json["former"],
                                                    lambda v: [pywikibot.Page(self.site, title=s) for s in v])
        else:
            self.init_cat(cache_file_name)

    def init_cat(self, filename):
        pywikibot.output("Cache not exists, loading from site.")
        assessment_list = ["fa", "fl", "a", "ga", "b", "c", "start", "stub", "ua"]
        high_quality_list = ["fa", "fl", "ga"]
        former_list = ["ffa", "ffl", "dga"]
        for c in assessment_list:
            class_name = pywikibot.i18n.twtranslate(self.site.code, "vital-"+c+"-class")
            self.assessment_list[c] = list(pywikibot.Category(self.site, class_name).subcategories())
        for c in high_quality_list:
            class_name = pywikibot.i18n.twtranslate(self.site.code, "vital-"+c+"-category")
            self.high_quality_list[c] = list(pywikibot.Category(self.site, class_name).articles(namespaces=0))
            # cat_list = []
            # class_name = pywikibot.i18n.twtranslate(self.site.code, "vital-"+c+"-talk-category")
            # for talks in pywikibot.Category(self.site, class_name).articles(namespaces=1):
            #     cat_list.append(talks.toggleTalkPage())
            # self.high_quality_talk_list[c] = cat_list
        for c in former_list:
            cat_list = []
            class_name = pywikibot.i18n.twtranslate(self.site.code, "vital-"+c+"-category")
            for talks in pywikibot.Category(self.site, class_name).articles(namespaces=1):
                cat_list.append(talks.toggleTalkPage())
            self.former_list[c] = cat_list

        # import into cache
        class UserEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, pywikibot.Category):
                    return obj.title(underscore=True, withNamespace=True)
                if isinstance(obj, pywikibot.Page):
                    return obj.title(underscore=True, withNamespace=True)
                return json.JSONEncoder.default(self, obj)
        with open(filename, 'w') as file:
            file.write(json.dumps(
                {"assessment": self.assessment_list, "high_quality": self.high_quality_list,
                 "former": self.former_list}, cls=UserEncoder))

    def get_cat(self, talk_page):
        if talk_page.exists():
            for talk_cat in talk_page.categories():
                for cls in self.assessment_list:
                    if talk_cat in self.assessment_list[cls]:
                        return cls.upper()
        return "UA"

    def check_list(self):
        pass

    def treat_page(self):
        self.check_list()

        new_text = self.current_page.text
        new_text = re.sub("([#*]+).*?('*){{/?vae?2\|(.*?)}}", "\g<1> \g<2>[[\g<3>]]", new_text)

        # sorting key for status
        predefined_list = ['FA', 'FL', 'A', 'GA', 'STUB', 'VAA', 'VAB', 'VAC',
                           'B', 'C', 'START', 'STUB', 'FFA', 'FFL', 'DGA']
        ordering = {word: i for i, word in enumerate(predefined_list)}
        isExtended = self.current_page in list(pywikibot.Category(self.site, "基礎條目第四級").articles())
        pywikibot.output("Finished initializing.")
        # enumerate the whole page
        for i, page in enumerate(self.current_page.linkedPages(0), start=1):
            pywikibot.log(page)
            if not i % 25:
                pywikibot.output(str(i) + " pages have been processed,")
            if page.exists():
                status = []
                while page.isRedirectPage():
                    page = page.getRedirectTarget()
                if page in self.high_quality_list['fa']:
                    status.append('FA')
                elif page in self.high_quality_list['fl']:
                    status.append('FL')
                    pywikibot.output("FL")
                else:
                    if page in self.high_quality_list['ga']:
                        status.append('GA')
                    elif page in self.former_list['dga']:
                        status.append('DGA')
                    if page in self.former_list['ffa']:
                        status.append('FFA')
                    if page in self.former_list['ffl']:
                        status.append('FFL')
                if ("FA" not in status) and ("FL" not in status):
                    grade = self.get_cat(page.toggleTalkPage())
                    if grade == "A":
                        status.append("A")
                    elif grade != "UA" and "GA" not in status:
                        status.append(grade)
                    elif "GA" not in status:
                        # Do not use length of the article
                        # r = Request(site=self.site,
                        #             parameters={'action': 'query', 'prop': 'info', 'titles': page.title()})
                        # length = next(iter(r.submit()['query']['pages'].values()))['length']
                        # Python 2 : dict.itervalues().next()['length']
                        # Calculate length by character count times 3.7
                        length = int(len(page.text)*3.7)
                        if length < (2000 if isExtended else 3000):
                            # pywikibot.output("Page is stub while not rated: ")
                            status.append("STUB")
                        elif length < (8000 if isExtended else 10000):
                            status.append("VAC")
                        elif length < (16000 if isExtended else 30000):
                            status.append("VAB")
                        else:
                            status.append("VAA")
                status_string = ""
                status = sorted(status, key=ordering.get)
                for s in status:
                    status_string += "{{Icon|"+s+"}} "
                new_text = re.sub("([#*]+).*?('*)(\[\["+re.escape(page.title())+".*)",
                                  "\g<1> "+status_string+"\g<2>\g<3>", new_text, flags=re.IGNORECASE)
            else:
                new_text = re.sub("([#*]+).*?('*)({{tsl\|en\|.*"+re.escape(page.title())+".*)",
                                  "\g<1> {{Icon|Q}} \g<2>\g<3>", new_text, flags=re.IGNORECASE)

        self.userPut(pywikibot.Page(self.site, "Wikipedia:沙盒") if self.sandbox else self.current_page,
                     self.current_page.text, new_text,
                     summary=pywikibot.i18n.twtranslate(self.site.code, "vital-modifying"))


def main(*args):
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    @param args: command line arguments
    @type args: list of unicode
    """
    options = {}
    # Process global arguments to determine desired site
    local_args = pywikibot.handle_args(args)

    # This factory is responsible for processing command line arguments
    # that are also used by other scripts and that determine on which pages
    # to work on.
    gen_factory = pagegenerators.GeneratorFactory()

    # Parse command line arguments
    for arg in local_args:
        # Catch the pagegenerators options
        if gen_factory.handleArg(arg):
            continue  # nothing to do here

        # Now pick up your own options
        arg, sep, value = arg.partition(':')
        option = arg[1:]
        if option in ('summary', 'text'):
            if not value:
                pywikibot.input('Please enter a value for ' + arg)
            options[option] = value
        # take the remaining options as booleans.
        # You will get a hint if they aren't pre-defined in your bot class
        else:
            options[option] = True

    # The preloading option is responsible for downloading multiple
    # pages from the wiki simultaneously.
    gen = gen_factory.getCombinedGenerator(preload=True)
    if gen:
        # pass generator and private options to the bot
        bot = BasicBot(gen, **options)
        bot.run()  # guess what it does
        return True
    else:
        pywikibot.bot.suggest_help(missing_generator=True)
        return False


if __name__ == '__main__':
    main()
