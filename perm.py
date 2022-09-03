import json


class Perm:

    guild = []  # The guild(s) this bot should be active in. Only tested with two!

    active_embeds: list = []  # The currently active embeds, dont change this

    main_url = "https://xlecx.one"  #  Can be changed to accomodate for url changes

    blacklisted_tags: list = [  # Better leave it like this
        "lolicon",
        "bestiality",
        "snuff",
        "scat",
        "birth",
        "guro",
        "unbirth",
        "vore"
    ]

    paginator_timeout = 300  # How long a paginator should take inputs in seconds

    rsspath = "https://xlecx.one/rss.xml"  # Site updates

    max_loaded_comics = 10  # Yea, dont change this

    bot_updates_channel = {"": }  # The guild: channel where the bot should post updates

    bot_report_channel = {"": }  # The guild: channel where the bot should send reports to

    report_messages = {}  # "message_id": "message parameters", all active report messages

    roles = {
             "": []}  # Server roles that overwrite permissions
    everyone_roles = {  # Server roles that dont overwrite permissions
        "": [],
        "": []
    }
    # "server_id": ["role ids that are allowed"]
    guild_owners = {"": }   # Guild: Owner ID

    denied_roles = {}  # Guild: Denied role ID

    bot_updates_enabled = {"": True}  # Guild: True/False

    search_limit = 15  # Dont change unless site changes it

    fields = ["guild", "main_url", "rsspath", "bot_updates_channel", "bot_report_channel", "report_messages", "roles",
                       "max_loaded_comics", "blacklisted_tags", "paginator_timeout", "bot_updates_enabled"]

    commands = [
        {"name": "/read_comic preference (pagination, thread) comic (comic id / link)",
         "action": "Send a comic to a channel, either as a new thread or a pagination embed, which automatically "
                   "disables after 5 minutes of no interactions\n"},
        {"name": "/search object (title, tag, group, artist, parody) sitesearch",
         "action": "Search for a comic considering the given parameters! "
                   "If you do a sitesearch, there will be less data and the request takes longer!\n"},
        {"name": "/report_comic because_of (abuse, tag_missing, something else) comic (comic id / link) message (text)",
         "action": "Reports a comic using the specified reason or adds a tag to the blacklist!\n"},
        {"name": "/details comic (comic id / link)",
         "action": "Posts a comics saved data as a small embed!\n"},
        {"name": "/help",
         "action": "Shows this help message!\n"}
    ]

    def __init__(self):
        self.updateFromFile()

    def updateFromFile(self):
        with open("settings.json", "r", encoding="utf-8") as rawsettings:
            settings = json.loads(rawsettings.read())
        self.guild = settings["guild"] if settings["guild"] else self.guild
        self.main_url = settings["main_url"] if settings["main_url"] else self.main_url
        self.rsspath = settings["rsspath"] if settings["rsspath"] else self.rsspath
        self.roles = settings["roles"] if settings["roles"] else self.roles
        self.bot_updates_channel = settings["bot_updates_channel"] \
            if settings["bot_updates_channel"] else self.bot_updates_channel
        self.bot_report_channel = settings["bot_report_channel"] \
            if settings["bot_report_channel"] else self.bot_report_channel
        self.max_loaded_comics = settings["max_loaded_comics"] \
            if settings["max_loaded_comics"] else self.max_loaded_comics
        self.blacklisted_tags = settings["blacklisted_tags"] \
            if settings["blacklisted_tags"] else self.blacklisted_tags
        self.paginator_timeout = settings["paginator_timeout"] \
            if settings["paginator_timeout"] else self.paginator_timeout
        self.bot_updates_enabled = settings["bot_updates_enabled"] \
            if settings["bot_updates_enabled"] else self.bot_updates_enabled
        self.denied_roles = settings["denied_roles"] \
            if settings["denied_roles"] else self.denied_roles
        self.everyone_roles = settings["everyone_roles"] \
            if settings["everyone_roles"] else self.everyone_roles
        self.guild_owners = settings["guild_owners"] \
            if settings["guild_owners"] else self.guild_owners

    def saveToFile(self):
        with open("settings.json", "w+", encoding="utf-8") as rawsettings:
            rawsettings.write(json.dumps({
                "guild": self.guild,
                "main_url": self.main_url,
                "rsspath": self.rsspath,
                "bot_updates_channel": self.bot_updates_channel,
                "bot_report_channel": self.bot_report_channel,
                "roles": self.roles,
                "max_loaded_comics": self.max_loaded_comics,
                "blacklisted_tags": self.blacklisted_tags,
                "paginator_timeout": self.paginator_timeout,
                "bot_updates_enabled": self.bot_updates_enabled,
                "denied_roles": self.denied_roles,
                "everyone_roles": self.everyone_roles,
                "guild_owners": self.guild_owners
            }, indent=4, ensure_ascii=False))
