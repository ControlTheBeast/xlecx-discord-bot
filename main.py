import asyncio
import datetime
import json
import logging
import os
import socket
import sqlite3
import time
from contextlib import suppress
from sqlite3 import Error

import aiohttp
import discord
import feedparser
import requests as requests
from bs4 import BeautifulSoup
from dinteractions_Paginator import Paginator
from discord import ChannelType
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_choice, create_permission
from dotenv import load_dotenv

import perm

logging.basicConfig(level=logging.INFO, filename="xlecx-bot-1.log", filemode="w+")
# logging.basicConfig(level=logging.DEBUG)

load_dotenv()
Perm = perm.Perm()


class Periodic:
    def __init__(self, func: callable, interval: int):
        self.func = func
        self.time = interval
        self.is_started = False
        self._task = None

    async def start(self):
        if not self.is_started:
            self.is_started = True
            # Start task to call func periodically:
            self._task = asyncio.ensure_future(self._run())

    async def stop(self):
        if self.is_started:
            self.is_started = False
            # Stop task and await it stopped:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    async def _run(self):
        while True:
            await asyncio.sleep(self.time)
            try:
                await self.func()
            except Exception as e:
                logging.warning(e, exc_info=True)


class DataController:
    database = None
    databasename = None

    keys = ["ID", "available", "name", "artist", "tags", "parodies", "groups", "description", "meta_description",
            "comments", "ratio", "access_date", "requested", "url", "views", "votes",
            "images", "upload_date", "author", "allowed"]

    def __init__(self, databasename: str = "identifier"):
        self.databasename = f"{databasename}.sqlite"
        logging.log(logging.DEBUG, self.databasename)

    def create_connection(self):
        connection = None
        try:
            connection = sqlite3.connect(self.databasename)
        except Error as e:
            logging.log(logging.WARNING, f"The error '{str(e)}' occurred")
        return connection

    @staticmethod
    def execute_command(conn: sqlite3.Connection = None, command: str = None, params: list = None):
        cursor = conn.cursor()
        result = cursor.execute(command) if not params else cursor.execute(command, params)
        conn.commit()
        return result.fetchall(), cursor.lastrowid

    def searchDatabase(self, title: str = None, tag: str = None, group: str = None, artist: str = None,
                       parody: str = None, newest: bool = False):
        base_command, add_commands = """SELECT * FROM main.comics WHERE""", []
        if title and len(title) > 0:
            add_commands.append(fr""" name LIKE '%{title.lower()}%' ESCAPE '\' """)
        if tag and len(tag) > 0:
            add_commands.append(fr""" tags LIKE '%{tag.lower()}%' ESCAPE '\' """)
        if group and len(group) > 0:
            add_commands.append(fr""" groups LIKE '%{group.lower()}%' ESCAPE '\' """)
        if artist and len(artist) > 0:
            add_commands.append(fr""" artist LIKE '%{artist.lower()}%' ESCAPE '\' """)
        if parody and len(parody) > 0:
            add_commands.append(fr""" parodies LIKE '%{parody.lower()}%' ESCAPE '\' """)

        if len(add_commands) == 0:
            command = """SELECT * FROM main.comics ORDER BY ID DESC LIMIT 0, 15"""
        else:
            command = base_command + str(add_commands[0]) + ("AND" if len(add_commands) > 1 else "") + \
                      "AND".join(add_commands[1:]) + (fr"""ORDER BY 'upload_date' ASC """ if newest else "") \
                      + f" LIMIT 0, {str(Perm.search_limit)}"
        conn = self.create_connection()
        with conn:
            results = self.execute_command(conn, command)[0]
            for result in results:
                yield dict(zip(self.keys, result))

    def insertEntry(self, params: list = None, params_dict: dict = None):
        """[ID, available, name, artist, tags, parodies, groups, description, meta_description, comments, ratio,
        access_date, requested, url, views]"""

        if params_dict:
            params = [params_dict["ID"],
                      params_dict["available"],
                      params_dict["name"],
                      params_dict["artist"].strip(),
                      params_dict["tags"],
                      params_dict["parodies"],
                      params_dict["groups"].strip(),
                      params_dict["description"],
                      params_dict["meta_description"],
                      json.dumps(params_dict["comments"]),
                      float(params_dict["ratio"] / 100),
                      self.getCurrentTime(),
                      False,
                      params_dict["url"],
                      params_dict["views"],
                      params_dict["votes"],
                      json.dumps(params_dict["images"]),
                      params_dict["upload_date"] if "upload_date" in params_dict else float(0.0),
                      params_dict["author"] if "author" in params_dict else "Unknown",
                      1]

        sql_new_entry = f"""INSERT INTO main.comics(
        ID,
        available,
        name,
        artist,
        tags,
        parodies,
        groups,
        description,
        meta_description,
        comments,
        ratio,
        access_date,
        requested,
        url,
        views,
        votes,
        images,
        upload_date,
        author,
        allowed) 
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        conn = self.create_connection()
        with conn:
            self.execute_command(conn=conn, command=sql_new_entry, params=params)

    def editEntry(self, params: list = None, params_dict: dict = None):
        """[ID, available, name, artist, tags, parodies, groups, description, meta_description, comments, ratio,
        access_date, requested, url, views]"""

        if params_dict:
            params = [params_dict["ID"],
                      params_dict["available"],
                      params_dict["name"],
                      params_dict["artist"].strip(),
                      params_dict["tags"],
                      params_dict["parodies"],
                      params_dict["groups"].strip(),
                      params_dict["description"],
                      params_dict["meta_description"],
                      json.dumps(params_dict["comments"]),
                      float(params_dict["ratio"] / 100),
                      self.getCurrentTime(),
                      False,
                      params_dict["url"],
                      params_dict["views"],
                      params_dict["votes"],
                      json.dumps(params_dict["images"]),
                      params_dict["upload_date"] if "upload_date" in params_dict else float(0.0),
                      params_dict["author"] if "author" in params_dict else "Unknown",
                      1,
                      params_dict["ID"]]

        sql_new_entry = f"""UPDATE main.comics SET (
        ID,
        available,
        name,
        artist,
        tags,
        parodies,
        groups,
        description,
        meta_description,
        comments,
        ratio,
        access_date,
        requested,
        url,
        views,
        votes,
        images,
        upload_date,
        author,
        allowed) = (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) WHERE ID == (?)"""
        conn = self.create_connection()
        self.execute_command(conn=conn, command=sql_new_entry, params=params)

    def setAllowed(self, comic_id: int, allowed: bool = False):
        """Sets a comic postable or not"""
        command = """UPDATE main.comics SET allowed = (?) WHERE ID == (?)"""
        params = [allowed, comic_id]
        conn = self.create_connection()
        self.execute_command(conn=conn, command=command, params=params)

    def log(self, request: str, success: bool, error: str, author: str):
        connection = self.create_connection()
        command = """INSERT INTO main.logs (request_date, request, success, error, author) VALUES (?,?,?,?,?)"""
        params = [self.getCurrentTime(), request, success, error, author]
        self.execute_command(conn=connection, command=command, params=params)

    def getComic(self, FROM: int = -1, TO: int = None, EQUALS: int = None) -> [dict]:
        """Generator: Gets all comics from the database where the id is between FROM and TO (both not included)"""
        connection = self.create_connection()
        command: str = "None"
        params = []
        if FROM:
            command = f"""SELECT * FROM main.comics WHERE ID > (?)"""
            params.append(FROM)
        if TO:
            command = command + "AND ID < (?)"
            params.append(TO)
        if EQUALS:
            command = f"""SELECT * FROM main.comics WHERE ID == (?)"""
            params = [EQUALS]
        results, cursor = self.execute_command(connection, command, params=params)
        connection.close()

        for result in results:
            yield dict(zip(self.keys, result))

    @staticmethod
    def getCurrentTime() -> float:
        return time.time()


class SubclassedBot(commands.Bot):
    second_session = None
    guild: discord.Guild = None

    # Everything that has to do with feedparsing
    timer = None
    last_response = None
    last_response_data = {}

    database = None
    active_embeds: int = 0

    COMIC_NAME: str = "Comic name failed to load!"

    site_status: bool = True  # True if the site is online, False if not

    interval_caller: Periodic = None

    current_failed_requests = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_response = list()
        self.database = DataController()
        self.loop.create_task(self._create_Session())
        self.interval_caller = Periodic(self._searchUpdates, 12)

        self.loop.create_task(self.interval_caller.start())

    async def _create_Session(self):
        self.second_session = aiohttp.ClientSession()

    def createPermissions(self, role: str, allowed: bool):
        """owners -> permission, everyone -> permission, mods -> [permission], denied -> [permission]"""
        if role.lower() == "owners":
            return {guild: create_permission(Perm.guild_owners[guild], SlashCommandPermissionType.USER, allowed)
                    for guild in Perm.guild_owners}
        elif role.lower() == "everyone":
            return {
                str(guild): create_permission(Perm.everyone_roles[guild], SlashCommandPermissionType.ROLE, allowed)
                for guild in Perm.everyone_roles}
        elif role.lower() == "mods":
            return {guild: [create_permission(Perm.roles[str(guild)][index],
                                              SlashCommandPermissionType.ROLE, allowed)
                            for index in range(len(Perm.roles[str(guild)]))] for guild in Perm.roles}
        elif role.lower() == "denied":
            return {str(guild): [create_permission(Perm.denied_roles[str(guild)][index],
                                                   SlashCommandPermissionType.ROLE, allowed)
                                 for index in range(len(Perm.denied_roles[str(guild)]))] for guild in Perm.denied_roles}

    async def stop(self):
        Perm.everyone_roles = {str(guild.id): guild.default_role.id for guild in self.guilds}
        if self.interval_caller and self.interval_caller.is_started:
            await self.interval_caller.stop()
        Perm.saveToFile()
        await self.second_session.close()

    @staticmethod
    def getID(link: str):
        """
        Assuming a well-formed link
        :param link:
        :return:
        """
        if link.isdigit():
            return int(link)
        return link.split("/")[-1].split("-")[0]

    @staticmethod
    def getIDAndName(link: str):
        """
        Assuming a well-formed link
        :param link:
        :return:
        """
        if link.isdigit():
            return int(link)
        linkle = link.split("/")[-1].split("-")
        return linkle[0], " ".join(linkle[1:])

    def getImageLinks(self, html, comic_id, url, additional_params=None) -> dict:
        if additional_params is None:
            additional_params = {}
        artist_name: str = "Unknown"
        tag_names: str = "No tags given"
        parody_names: str = "No parody"
        group_names: str = "Unknown"
        comic_name: str = "No comic name"
        description: str = ""
        meta_description: str = ""
        available = False
        rating, votes, views = 0, 0, 0

        # We scraping
        soup = BeautifulSoup(html, features="html.parser")

        links = soup.findAll("a")
        imgs = soup.findAll("img")

        try:
            raw_name = soup.find("meta", property="og:title")
            raw_description = soup.find("div", {"class": "f-desc full-text clearfix"})
            if raw_description:
                description = " ".join([i for i in raw_description.stripped_strings])
            meta_description = soup.find("meta", property="og:description")["content"]
            # logging.log(logging.DEBUG, soup.find("meta"))
            # logging.log(logging.DEBUG, name)
            # This was only for me ^
            comic_name = raw_name["content"].strip()
        except Exception as e:
            logging.log(logging.WARNING, str(e), repr(e))

        try:

            for name in soup.find_all("div", {"class": "full-tags"}):
                if "Artist" in name.text:
                    artist_name = name.text.split(":")[1]
                if "Tags" in name.text:
                    tag_names = ", ".join(name.text.replace("Tags:", "").strip().split(", "))
                    # logging.log(logging.DEBUG, tag_names)
                if "Parody" in name.text:
                    parody_names = ", ".join(name.text.split(":")[1].split(", "))
                if "Group" in name.text:
                    group_names = name.text.split(":")[1]
        except Exception as e:
            logging.log(logging.WARN, str(e), repr(e))

        try:
            # Get rating and views
            raw_rate_data = soup.find("div", {"class": "rate-data"}).stripped_strings
            rate_data = [0, 0]
            if raw_rate_data:
                rate_data = [g.replace("+", "") for g in raw_rate_data]
            raw_views = soup.findAll("div", {"class": "f-views icon-l"})
            if raw_views:
                views = int([g.text.replace(" ", "") for g in raw_views][1])
                c = int(rate_data[1]) if int(rate_data[1]) > 0 else 1
                b = int(rate_data[0])
                rating = round((c - (c - b) / 2) / c * 100)
                votes = c
        except Exception as e:
            logging.log(logging.WARN, str(e), repr(e))

        # Creating the five imagelists (I will be adding the webp one in the next update)
        imagesjpg = [link["href"].replace(Perm.main_url, "")
                     for link in links if link["href"].endswith("jpg")]
        imagespng = [link["href"].replace(Perm.main_url, "")
                     for link in links if link["href"].endswith("png")]
        imagesgif = [link["href"].replace(Perm.main_url, "")
                     for link in links if link["href"].endswith("gif")]
        imagesjpeg = [link["href"].replace(Perm.main_url, "")
                      for link in links if link["href"].endswith("jpeg")]
        imageswebp = [link["href"].replace(Perm.main_url, "")
                      for link in links if link["href"].endswith("webp")]

        # This is bad programming, but it makes it very clear what's happening, eh?
        images = imagesjpg + imagespng + imagesgif + imagesjpeg + imageswebp
        for link in imgs:
            try:
                if link["data-src"].endswith("jpg") or \
                        link["data-src"].endswith("png") or \
                        link["data-src"].endswith("gif") or \
                        link["data-src"].endswith("jpeg") or \
                        link["data-src"].endswith("webp"):
                    # Exclude these damn thumbs to prevent double downloads
                    if "thumbs" not in link["data-src"].split("/"):
                        images.append(
                            str(link["data-src"]))
            except KeyError:
                # Means, that this is not one of the relevant images
                # they always have a data-src
                pass

        comments_raw = soup.findAll("li", {"class": "comments-tree-item"})
        comments = {comment.find("img")["alt"]: comment.text.strip() for comment in comments_raw}
        time.sleep(1)
        try:
            if len(images) > 0:
                imageurl = images[0] if images[0].startswith("https://") else str("https://xlecx.one" + images[0])
                expect = requests.head(imageurl)
                if expect.status_code != 200:
                    alt_image = "/".join(images[0].split("/")[:-1]) + "/thumbs/" + images[0].split("/")[-1]
                    ping_alt = requests.get(Perm.main_url + alt_image)
                    if ping_alt.status_code == 200:
                        available = True
                else:
                    available = True
        except Exception as e:
            logging.log(logging.WARN, f"Fetching a comic state failed: {comic_id} : {str(e)}")

        result = {
            "available": available,
            "images": images,
            "artist": artist_name,
            "tags": tag_names,
            "parodies": parody_names,
            "groups": group_names,
            "name": comic_name,
            "description": description,
            "meta_description": meta_description,
            "comments": comments,
            "ID": comic_id,
            "url": url,
            "ratio": rating,
            "votes": votes,
            "views": views,
            "allowed": 1,
            **additional_params
        }
        try:
            self.database.insertEntry(params_dict=result)
        except Exception as e:
            logging.log(logging.WARN, str(e), repr(e))
        return result

    def getNewEmbedID(self, embed):
        if embed not in Perm.active_embeds:
            self.active_embeds += 1
            Perm.active_embeds.append(embed)
        for embed in Perm.active_embeds:
            if not embed.isActive():
                Perm.active_embeds.pop()
        return self.active_embeds

    async def addNewRSSLink(self, entry: dict, retries: int = 0):
        retries += 1
        if retries > 3:
            return
        try:
            async with self.second_session.get(entry["link"]) as response:
                code = response.status
                answer = await response.text()
            if code != 200:
                logging.log(logging.WARN, f"Comic with ID {entry['id']} failed to load!")
            self.getImageLinks(answer, self.getID(entry['link']), entry['link'],
                               additional_params={"author": entry["author"],
                                                  "upload_date": time.mktime(entry["published_parsed"])})
        except Exception as e:
            logging.warning(e, exc_info=True)
            logging.warning(f"An Exception has occurred while adding an RSS Link! Retry: {retries}")
            await asyncio.sleep(2)
            await self.addNewRSSLink(entry, retries=retries)

    async def _searchUpdates(self):
        logging.log(logging.DEBUG, self.site_status)
        try:
            async with self.second_session.get(Perm.rsspath) as answer:
                raw_result = await answer.text()
                if not answer.ok:
                    print("The site is currently offline!")
                    if self.site_status:
                        self.current_failed_requests += 1
                        if self.current_failed_requests > 5:
                            for joined_guild in self.guilds:
                                if str(joined_guild.id) in Perm.bot_updates_channel:
                                    await joined_guild.get_channel(
                                        Perm.bot_updates_channel[str(joined_guild.id)]).send(
                                        embed=discord.Embed(title="The site went offline!", colour=discord.Colour.red(),
                                                            timestamp=datetime.datetime.now())
                                    )
                            self.site_status = False
                    return
                self.current_failed_requests = 0
                if not self.site_status:
                    logging.log(logging.WARNING, "## Site should be online but status says its offline!")
                    for joined_guild in self.guilds:
                        if str(joined_guild.id) in Perm.bot_updates_channel:
                            await joined_guild.get_channel(
                                Perm.bot_updates_channel[str(joined_guild.id)]).send(
                                embed=discord.Embed(title="The site went online!", colour=discord.Colour.green(),
                                                    timestamp=datetime.datetime.now())
                            )
        except socket.gaierror as error:
            logging.warning("Resolution Error (gaierror), retrying...")
        except aiohttp.ClientOSError as error:
            logging.warning("Connection was reset (ClientOSError), retrying...")
        except Exception as e:
            logging.warning(e, exc_info=True)
        response = feedparser.parse(raw_result)
        logging.log(logging.DEBUG, json.dumps(response["entries"]))
        print("The site is currently online!")
        self.site_status = True
        for r in response["entries"]:
            try:
                comic_id = self.getID(r["link"])
            except Exception as e:
                logging.log(logging.WARN, f"Comic with ID {response['link']} failed to load: {repr(e)}")
                return
            if comic_id not in self.last_response:
                if len(self.last_response) > Perm.max_loaded_comics:
                    self.last_response_data.pop(self.last_response.pop())
                self.last_response.insert(0, comic_id)
                self.last_response_data[comic_id] = r
                in_database = len(list(self.database.getComic(EQUALS=int(comic_id))))
                if not in_database or in_database == 0:
                    await self.addNewRSSLink(r)
                    for joined_guild in self.guilds:
                        if str(joined_guild.id) in Perm.bot_updates_channel and \
                                Perm.bot_updates_enabled[str(joined_guild.id)]:
                            await joined_guild.get_channel(
                                Perm.bot_updates_channel[str(joined_guild.id)]).send(
                                embed=self.generateUpdateEmbed(
                                    comic_id=int(comic_id)
                                ))

    def generateHelpEmbed(self):
        embed = discord.Embed(title="Help", colour=discord.Colour.blurple())
        embed.set_thumbnail(url=self.user.display_avatar.url)
        for command in Perm.commands:
            embed.add_field(name=command["name"], value=command["action"], inline=False)
        embed.set_footer(text="Bot made by ControlTheBeast #6125 --- This bot is not affiliated with the website in "
                              "any way")
        return embed

    def generateUpdateEmbed(self, comic_id: int) -> discord.Embed:
        in_database = list(self.database.getComic(EQUALS=comic_id))
        if not in_database or len(in_database) == 0:
            embed = discord.Embed(colour=discord.Colour.red(),
                                  title="Comic not found!")
        else:
            logging.log(logging.DEBUG, in_database[0])
            in_database = in_database[0]
            embed = discord.Embed(colour=discord.Colour.green(),
                                  url=in_database["url"],
                                  title=in_database["name"])
            embed.add_field(name="Description", value=in_database["description"][:1024]) \
                if in_database["description"] != "" else None
            embed.add_field(name="Tags", value=in_database["tags"][:1024])
            embed.add_field(name="Groups", value=in_database["groups"][:1024]) \
                if in_database["groups"] != "Unknown" else None
            embed.add_field(name="Artist", value=in_database["artist"][:1024], inline=False)
            embed.add_field(name="Uploader", value=in_database["author"][:1024], inline=True)
            embed.set_thumbnail(url=str(Perm.main_url + json.loads(in_database["images"])[0]))
            embed.set_footer(text=f"Auto-generated --- ID: {in_database['ID']}")
        return embed

    @staticmethod
    def generateSiteDatabaseEmbed(comic_dict: dict, search_page: tuple = None) -> discord.Embed:
        std_comic_dict = ["images", "url", "name", "tags", "groups", "artist", "author"]
        if not search_page:
            search_page = (1, 1)
        for key in std_comic_dict:
            if not comic_dict[key]:
                comic_dict[key] = "Unknown"
        images = json.loads(comic_dict["images"])
        embed = discord.Embed(colour=discord.Colour.blue(),
                              url=comic_dict["url"],
                              title=comic_dict["name"])
        embed.add_field(name="Tags", value=comic_dict["tags"][:1024])
        embed.add_field(name="Groups", value=comic_dict["groups"][:1024]) if comic_dict["groups"] != "Unknown" else None
        embed.add_field(name="Artist", value=comic_dict["artist"][:1024], inline=False)
        embed.add_field(name="Uploader", value=comic_dict["author"][:1024], inline=True)
        if len(images) > 0:
            embed.set_thumbnail(url=str(Perm.main_url + images[0]))
        embed.set_footer(text=f"ID: {comic_dict['ID']} --- Page {search_page[0]}/{search_page[1]}")
        return embed

    @staticmethod
    def generateSiteSearchEmbed(comic_id: int, comic_url: str, comic_name: str, comic_thumbnail: str,
                                search_page: tuple = None) -> discord.Embed:
        if not search_page:
            search_page = (1, 1)
        embed = discord.Embed(colour=discord.Colour.blue(),
                              url=comic_url,
                              title=comic_name)
        embed.set_thumbnail(url=comic_thumbnail)
        embed.set_footer(text=f"ID: {comic_id} --- Page {search_page[0]}/{search_page[1]}")
        return embed

    async def sendReport(self, ctx_guild: discord.Guild, report_message: str = None, comic_id: str = None,
                         dismissed: bool = False):
        try:
            in_database = list(self.database.getComic(EQUALS=comic_id))[0]
            if len(in_database.keys()) == 0:
                return 2
            if str(ctx_guild.id) in Perm.bot_report_channel:
                embed = discord.Embed(colour=discord.Colour.red() if not dismissed else discord.Colour.green(),
                                      url=in_database["url"],
                                      title=in_database["name"])
                embed.add_field(name="Reason: ", value=report_message[:1024])
                embed.add_field(name="Tags", value=in_database["tags"][:1024])
                embed.add_field(name="Artist", value=in_database["artist"][:1024], inline=False)
                embed.set_thumbnail(url=str(Perm.main_url + json.loads(in_database["images"])[0]))
                embed.set_footer(text=f"Auto-generated --- ID: {in_database['ID']}")

                msg = await ctx_guild.get_channel(
                    Perm.bot_report_channel[str(ctx_guild.id)]).send(
                    embed=embed
                )
                logging.log(logging.DEBUG, "Adding message: ", str(msg.id))
                Perm.report_messages[msg.id] = {"ctx_guild": (ctx_guild.id, ctx_guild.name),
                                                "report_message": report_message,
                                                "comic_id": comic_id, "dismissed": dismissed}
                logging.log(logging.DEBUG, "Message added!")
                await msg.add_reaction("⛔")
                await msg.add_reaction("✅")
                return 0
        except Exception as e:
            self.database.log(f"Report request: {report_message}, {comic_id}", False, f"{e, repr(e)}",
                              author=f"{ctx_guild.id}")
            return 1

    async def sendMissingTag(self, ctx_guild: discord.Guild, ctx_author: discord.Member, tag: str):
        try:
            if str(ctx_guild.id) in Perm.bot_report_channel:
                embed = discord.Embed(colour=discord.Colour.yellow(),
                                      title="Blacklist this tag?")
                embed.add_field(name="Tag: ", value=tag[:1024])
                embed.add_field(name="Author: ", value=ctx_author, inline=False)
                embed.set_footer(text=f"Auto-generated --- Please react!")
                msg = await ctx_guild.get_channel(
                    Perm.bot_report_channel[str(ctx_guild.id)]).send(
                    embed=embed
                )
                logging.log(logging.DEBUG, "Adding message: ", str(msg.id))
                Perm.report_messages[msg.id] = {"ctx_guild": (ctx_guild.id, ctx_guild.name), "ctx_author": ctx_author,
                                                "tag": tag}
                logging.log(logging.DEBUG, "Message added!")
                await msg.add_reaction("⛔")
                await msg.add_reaction("✅")
                self.database.log(f"Tag request: {tag}", True, f"",
                                  author=f"{ctx_author}")
                return 0
        except Exception as e:
            self.database.log(f"Tag request: {tag}", False, f"{e, repr(e)}",
                              author=f"{ctx_author}")
            return 1


class ComicEmbed:
    """
    Represents a comic_embed which can be sent to a discord channel
    """
    artist: str = None
    pages: int = None
    name: str = None
    groups: str = None
    images: list = None
    source: str = None
    tags: str = None
    current_page: int = 0

    context = None

    paginator = None
    _id: int = 0  # Internal value to keep track of embeds

    creation_date: float = None

    fields: list = ["artist", "pages", "name", "groups", "images", "source"]

    def __init__(self, ctx, _fromDict_=None):
        """
        :param _fromDict_: Dictionary with artist, pages, name, groups, images and source information
        """
        self.artist = _fromDict_["artist"] if _fromDict_["artist"] else "No artist!"
        self.pages = _fromDict_["pages"] if _fromDict_["pages"] else 0
        self.name = _fromDict_["name"] if _fromDict_["name"] else "None"
        self.groups = _fromDict_["groups"] if _fromDict_["groups"] else None
        self.images = _fromDict_["images"] if _fromDict_["images"] else None
        self.tags = _fromDict_["tags"] if _fromDict_["tags"] else "No tags for this comic!"
        self.source = _fromDict_["source"] if _fromDict_["source"] else ""
        self.available = _fromDict_["available"]
        self.creation_date = time.time()
        self.color = discord.Colour.light_grey() if _fromDict_["available"] else discord.Colour.gold()
        self.context = ctx

        logging.log(logging.DEBUG, self.__dict__)
        self._id = bot.getNewEmbedID(embed=self)

    def isActive(self) -> bool:
        if self.creation_date is not None:
            return int(time.time() - self.creation_date) > Perm.paginator_timeout
        if self.paginator.stop:
            return False

    def getTitlePage(self) -> list:
        if self.name and self.source:
            embed = discord.Embed(colour=self.color,
                                  url=self.source,
                                  title=self.name)
            embed.add_field(name="Warning",
                            value="""```cs\n# The comic you want to view might have pages missing!```""") \
                if not self.available else None
            # embed.add_field(name="tags", value=self.tags)
            embed.add_field(name="groups", value=self.groups[:1024], inline=False) if self.groups != "Unknown" else None
            embed.add_field(name="artist", value=self.artist[:1024], inline=True)
            embed.set_thumbnail(url=str(Perm.main_url + self.images[0]))
            embed.set_footer(text=f"Page {0}/{len(self.images)}")
            return [embed]

    def getImageStructEmbeds(self) -> list:

        new_images: list = []
        images_changed: bool = False
        result: list = []
        if self.images is not None and len(self.images) > 0:
            for image in self.images:
                alt_image = None
                embed = discord.Embed(colour=self.color,
                                      url=self.source,
                                      title=self.name)
                embed.set_image(
                    url=str(Perm.main_url + image) if not alt_image else str(Perm.main_url + alt_image))

                embed.set_footer(text=f"Page {self.images.index(image) + 1}/{len(self.images)}")
                result.append(embed)
                new_images.append(image if not alt_image else alt_image)
        if images_changed:
            reportAltLink(new_images, bot.getID(self.source))
        return result

    def createPaginator(self):
        pages = self.getTitlePage()
        subembeds = [page for page in self.getImageStructEmbeds()]
        pages.extend(subembeds)
        self.paginator = Paginator(bot=bot, ctx=self.context, pages=pages,
                                   timeout=300, useSelect=False,
                                   disableAfterTimeout=True,
                                   useLinkButton=True, linkLabel=self.name, linkURL=self.source)
        # useQuitButton=True, quitButtonLabel="⛔")
        return self.paginator


def reportAltLink(new_images, comic_id):
    conn = bot.database.create_connection()
    result, _ = bot.database.execute_command(
        conn=conn,
        command="""UPDATE main.comics SET images = (?) WHERE ID == (?)""",
        params=[json.dumps(new_images, ensure_ascii=False), comic_id]
    )
    conn.close()


bot = SubclassedBot(command_prefix="X!")
bot._enable_debug_events = True
bot.load_extension("SocketFix")
slash = SlashCommand(bot, sync_commands=True)


@bot.event
async def on_ready():
    bot.AppInfo = await bot.application_info()

    startup = f"""
    \nBot name: {bot.user.name} - {bot.user.id}\n
    Owner: {bot.AppInfo.owner}\n
    discord.py version: {discord.__version__}\n
    """
    logging.info(startup)

    Perm.guild_owners = {guild.id: guild.owner_id for guild in
                         [bot.get_guild(guild_id) for guild_id in Perm.guild] if guild}

    activity_name = f"/help"
    bot_activity = discord.Activity(name=activity_name, type=discord.ActivityType.listening)
    await bot.change_presence(activity=bot_activity)
    logging.info("The bot is ready!\n")


@bot.event
async def on_raw_reaction_add(ctx: discord.RawReactionActionEvent):
    important_part = ""
    try:
        if ctx.member.id == bot.user.id:
            return
        if ctx.message_id not in Perm.report_messages:
            return
        authorized = False
        if str(ctx.guild_id) in Perm.roles:
            if str(ctx.member.id) in Perm.guild_owners[str(ctx.guild_id)]:
                authorized = True
            for role in ctx.member.roles:
                if role.id in Perm.roles[str(ctx.guild_id)]:
                    authorized = True
                    break
        if not authorized:
            return
    except Exception as e:
        logging.log(logging.WARN, str(e))
    try:
        allowed = 1
        msg = await bot.get_guild(ctx.guild_id).get_channel(ctx.channel_id).fetch_message(ctx.message_id)
        tag = "tag" in Perm.report_messages[ctx.message_id]
        removal: dict = Perm.report_messages.pop(ctx.message_id)
        logging.log(logging.DEBUG, "removing message", removal)
        important_part = removal["comic_id"] if "comic_id" in removal else removal["tag"]
        if ctx.emoji.name == "⛔":
            if tag:
                Perm.blacklisted_tags.remove(important_part) if \
                    important_part in Perm.blacklisted_tags else None
                await msg.edit(content=f"Tag {important_part} is allowed!", embed=None)
            else:
                bot.database.setAllowed(comic_id=int(important_part), allowed=False)
                await msg.edit(content=f"Comic {important_part} can't be posted anymore!", embed=None)
                allowed = 0
        elif ctx.emoji.name == "✅":
            if tag:
                Perm.blacklisted_tags.append(important_part) if \
                    important_part not in Perm.blacklisted_tags else None
                await msg.edit(content=f"Tag {important_part} is not allowed anymore!", embed=None)
            else:
                bot.database.setAllowed(comic_id=int(important_part), allowed=True)
                await msg.edit(content=f"Allowed comic {important_part}!", embed=None)
        bot.database.log((str(important_part) + f" got {'allowed' if allowed == 1 else 'excluded'}" +
                          ", on raw reaction add"), True, error=f"", author=ctx.member.name)
    except Exception as e:
        bot.database.log((str(Perm.report_messages[ctx.message_id]["comic_id"]
                              if ctx.message_id in Perm.report_messages else important_part)
                          + ", on raw reaction add"), False, error=f"{e}: {repr(e)}", author=ctx.member.name)


# ----------------------------------------------------------------------------------------------------------------------
# Meme commands


@slash.slash(
    name="good_morning",
    guild_ids=[],  # Only for the one and only true inofficial discord server and only butterbean
    description="Greet someone",
    permissions={1: [
        create_permission(2, SlashCommandPermissionType.USER, True),  # Yes butterbeans id was here
        create_permission(2, SlashCommandPermissionType.ROLE, False)  # yes, i denied it for everyone else
    ]}
)
async def good_morning(ctx):
    await ctx.send("https://youtu.be/IkEBhqeJDdM")


# ----------------------------------------------------------------------------------------------------------------------
# General Bot Commands

@slash.slash(
    name="help",
    description="Send a short help message"
)
async def _help(ctx):
    await ctx.send(embed=bot.generateHelpEmbed())


@slash.slash(
    name="read_comic",
    description="Send a comic to the channel",
    options=[
        create_option(
            name="preference",
            description="How should the comic be sent?",
            option_type=3,
            required=True,
            choices=[
                create_choice(
                    name="As a pagination embed",
                    value="pagination"
                ),
                create_choice(
                    name="Into a new thread",
                    value="thread"
                )
            ]
        ),
        create_option(
            name="comic",
            description="Comic URL or ID",
            option_type=3,
            required=True
        )
    ])
async def read_comic(ctx, preference: str, comic: str):
    deep_search = False
    full_comic = None
    comic_images = None
    msg = None

    try:
        comic_id = int(comic) if comic.isdigit() else bot.getID(comic)
    except NotImplementedError as n:
        bot.database.log(str(comic + ", " + preference), False, error=f"{n}: {repr(n)}", author=ctx.author.name)
        await ctx.send("Please enter a valid comic url or ID! Search for a comic first if you need to (/search)!")
        return
    try:
        full_comic = list(bot.database.getComic(EQUALS=comic_id))[0]
        comic_images = json.loads(full_comic["images"])
        if full_comic is None or len(comic_images) == 0:
            msg = await ctx.send("Preparing for a deeper search, this comic is not listed in the database!")
            deep_search = True
    except IndexError as i:
        bot.database.log(str(comic + ", " + preference), False, error=f"{i}: {repr(i)}", author=ctx.author.name)
        msg = await ctx.send("Preparing for a deeper search, this comic is not listed in the database!")
        deep_search = True
    except KeyError as e:
        bot.database.log(str(comic + ", " + preference), False, error=f"e: {repr(e)}", author=ctx.author.name)
        await ctx.send(
            "There seems to be an error with this comic! Please try to inform the owner ControlTheBeast #6125!")
        return

    if deep_search:
        async with ctx.channel.typing():

            if not comic.startswith(Perm.main_url) or len(comic) < 21:
                bot.database.log(str(comic + ", " + preference), False,
                                 error=f"Not a valid URL", author=ctx.author.name)
                await ctx.send("Enter a valid URL!")
                return
            message = await ctx.send("Searching for comic...")

            # Checking if it's a URL
            async with bot.second_session.get(comic) as r:
                code = r.status
                answer = await r.text()

            if code == 404:
                await message.edit(content="This comic could not be found!")
                bot.database.log(str(comic + ", " + preference), False, error=f"Not found", author=ctx.author.name)
                await msg.delete() if msg else None
                return

            if code == 403:
                await message.edit(content="Sadly, member comics are against discord TOS!")
                bot.database.log(str(comic + ", " + preference), False, error=f"Member comic", author=ctx.author.name)
                await msg.delete() if msg else None
                return

            full_comic = bot.getImageLinks(answer, bot.getID(comic), comic)
            comic_images = full_comic["images"]
            # Update the "requested" database field
            bot.database.execute_command(conn=bot.database.create_connection(),
                                         command="UPDATE main.comics SET requested = requested + 1 WHERE ID == (?)",
                                         params=[comic_id])
            if len(comic_images) == 0:
                await message.edit(content="There were no pictures found! Are you sure you put in the right URL?")
                bot.database.log(str(comic + ", " + preference), False, error=f"No pictures!", author=ctx.author.name)
                await msg.delete() if msg else None
                return
    for tag in Perm.blacklisted_tags:
        if tag in full_comic["tags"]:
            bot.database.log(str(comic + ", " + preference), False,
                             error=f"Banned tag: ({tag})", author=ctx.author.name)
            await ctx.send(content=f"Your comic contains a banned tag ({tag})!")
            return

    if full_comic["allowed"] == 0:
        bot.database.log(str(comic + ", " + preference), False,
                         error=f"Banned comic: ({comic_id})", author=ctx.author.name)
        await ctx.send(content=f"Your comic was reported as offensive and could therefore not be posted!")
        return
    if preference.lower() == "pagination":
        try:
            comic_embed = ComicEmbed(ctx=ctx, _fromDict_={"artist": full_comic["artist"],
                                                          "pages": len(full_comic["images"]),
                                                          "name": full_comic["name"],
                                                          "groups": full_comic["groups"],
                                                          "available": full_comic["available"],
                                                          "images": comic_images,
                                                          "tags": full_comic["tags"],
                                                          "source": full_comic["url"]})

            bot.database.execute_command(conn=bot.database.create_connection(),
                                         command="UPDATE main.comics SET requested = requested + 1 WHERE ID == (?)",
                                         params=[comic_id])
            await comic_embed.createPaginator().run()
        except Exception as e:
            bot.database.log(str(comic + ", " + preference), False, error=f"{e}: {repr(e)}", author=ctx.author.name)
            await ctx.send("Embed creation failed! Please ping ControlTheBeast #6125!")
            return

    if preference.lower() == "thread":
        msg2 = await ctx.send("Success!")
        # Thread creation
        sub_thread = await ctx.channel.create_thread(
            type=ChannelType.public_thread,
            name=full_comic["name"],
            reason=f"Requested by {ctx.author}"
        )
        try:
            alt_images: list = []
            for image in comic_images:
                if not image.startswith("https:"):
                    alt_images.append(str(Perm.main_url + image))
            for index in range(0, len(comic_images), 5):
                await sub_thread.send(("\n".join(comic_images[index:index + 5]))
                                      if len(alt_images) == 0 else ("\n".join(alt_images[index:index + 5])))
            # await sub_thread.send("\n".join(images[index:index+5]))
        except Exception as e:
            await msg.edit(content=f"An exception occurred while sending image links! {repr(e)}")
            bot.database.log(str(comic + ", " + preference), False, error=f"{e}: {repr(e)}", author=ctx.author.name)
            logging.error(e)
            return
        else:
            await msg.delete() if msg else None
            await sub_thread.send(
                f"{full_comic['name']} "
                f"by {full_comic['artist']}\n"
                f"{('Group: ' + full_comic['groups']) if not full_comic['groups'] == 'Unknown' else ''}\n"
                f"Tags: {full_comic['tags']}\n"
                f"Parody: {full_comic['parodies']}\n"
                f"{full_comic['url']}")
        if msg2:
            await msg2.delete()
    bot.database.log(str(comic + ", " + preference + ", " + ("Added a new comic" if deep_search else "")), True,
                     error="", author=ctx.author.name)
    logging.info("Comic sent!")


@slash.slash(
    name="report_comic",
    description="Report a comic or edit the blacklist",
    options=[
        create_option(
            name="because_of",
            description="Report a comic for abuse, incomplete tags or something else!",
            option_type=3,
            required=True,
            choices=[
                create_choice(
                    name="abuse",
                    value="abuse"
                ),
                create_choice(
                    name="a missing tag",
                    value="tag_missing"
                ),
                create_choice(
                    name="something else",
                    value="something_else"
                )
            ]),
        create_option(
            name="message",
            description="Type in the tag that are missing or the message you want to send!",
            option_type=3,
            required=True
        ),
        create_option(
            name="comic",
            description="Comic URL or ID",
            option_type=3,
            required=False
        )
    ])
async def report_comic(ctx: SlashContext, because_of: str = None, comic: str = None, message: str = None):
    comic = comic if comic else ""
    try:
        if because_of == "tag_missing":
            await bot.sendMissingTag(ctx_guild=ctx.guild, ctx_author=ctx.author, tag=message)
            await ctx.send("Report sent!")
            return
        await bot.sendReport(ctx.guild, comic_id=bot.getID(comic), report_message=message)
        await ctx.send("Report sent!")
        bot.database.log(str("Report:" + comic + ", " + because_of + ", " + message), True,
                         error="", author=ctx.author.name)
    except Exception as e:
        await ctx.send("The report failed to send properly, please inform a Mod or Admin!")
        bot.database.log(str("Report:" + comic + ", " + because_of + ", " + message), False,
                         error=f"{e}, {repr(e)}", author=ctx.author.name)


@slash.slash(
    name="search",
    description="Search for a comic",
    options=[
        create_option(
            name="title",
            option_type=3,
            description="search for a title",
            required=False
        ),
        create_option(
            name="tag",
            option_type=3,
            description="search for a tag",
            required=False
        ),
        create_option(
            name="group",
            option_type=3,
            description="search for a group",
            required=False
        ),
        create_option(
            name="artist",
            option_type=3,
            description="search for an artist",
            required=False
        ),
        create_option(
            name="parody",
            option_type=3,
            description="search for a parody",
            required=False
        ),
        create_option(
            name="sitesearch",
            option_type=5,
            description="Do a sitesearch instead of a database search (Takes longer and less precise!)",
            required=False
        )
    ]
)
async def search(ctx: SlashContext, title: str = None, tag: str = None, group: str = None, artist: str = None,
                 parody: str = None, sitesearch: bool = False):
    try:
        if not sitesearch:
            response = list(
                bot.database.searchDatabase(title=title, tag=tag, group=group, artist=artist, parody=parody))
            print(response)
            if len(response) == 0:
                await ctx.send("This comic couldn't be found!")
                return
            embeds = [bot.generateSiteDatabaseEmbed(comic_dict=response[query], search_page=(query + 1, len(response)))
                      for query in range(len(response))]
            logging.debug(str(embeds))
            await Paginator(bot=bot, ctx=ctx, pages=embeds,
                            timeout=300, useSelect=False, authorOnly=True, disableAfterTimeout=True).run()
            bot.database.log(str(f"Searched for: {title=}, {tag=} , {group=}, {artist=}, {parody=}, {sitesearch=}, " +
                                 str(ctx.guild_id)),
                             True, error="", author=ctx.author.name)
        else:
            await ctx.defer()
            data = {
                "do": "search",
                "subaction": "search",
                "story": "+".join([title if title else "", tag if tag else "",
                                   group if group else "", artist if artist else "",
                                   parody if parody else ""]).replace(" ", "+")
            }

            async with bot.second_session.post("https://xlecx.one", data=data) as r:
                answer = await r.text()
                if not r.ok:
                    await ctx.send("The site send back an error! Report this problem with the /report_comic command!")
                    return

            soup = BeautifulSoup(answer, features="html.parser")
            s = "Unfortunately"
            for result in soup.findAll("div", {"class": "berrors"}):
                s = [x for x in result.stripped_strings][1]

            if s.startswith("Unfortunately"):
                await ctx.send(content="There were no comics found!")
                return

            await ctx.send(s.replace(":", ""))
            response = [[bot.getIDAndName(link["href"]), link.find("img")["src"], link["href"]]
                        for link in soup.findAll("a", {"class": "th-img img-resp-h"})]
            if len(response) < 1:
                await ctx.send(content="There were no comics found!")
                return
            embeds = [bot.generateSiteSearchEmbed(
                comic_id=int(query[0][0]), comic_url=query[2], comic_name=query[0][1],
                comic_thumbnail=Perm.main_url + query[1],
                search_page=(response.index(query) + 1, len(response))) for query in response]
            await Paginator(bot=bot, ctx=ctx, pages=embeds,
                            timeout=300, useSelect=False, authorOnly=True, disableAfterTimeout=True).run()
        bot.database.log(str(f"Searched for: {title=}, {tag=} , {group=}, {artist=}, {parody=}, {sitesearch=}, " +
                             str(ctx.guild_id)),
                         True, error="", author=ctx.author.name)
    except Exception as e:
        await ctx.send("Something went wrong while searching! Report this with /report_comic command!")
        bot.database.log(str(f"Searched for: {title=}, {tag=} , {group=}, {artist=}, {parody=}, {sitesearch=}, " +
                             str(ctx.guild_id)), False, error=str(e) + repr(e), author=ctx.author.name)


@slash.slash(
    name="details",
    description="Get details on a comic",
    options=[
        create_option(
            name="comic",
            option_type=3,
            description="Give a comic ID or link!",
            required=False
        )]
)
async def details(ctx: SlashContext, comic: str):
    await ctx.send(embed=bot.generateUpdateEmbed(bot.getID(comic)))


# ----------------------------------------------------------------------------------------------------------------------
# Guild Admin Commands


@slash.slash(
    name="add_allowed",
    guild_ids=Perm.guild,
    description="Add a role that can set postability on comics",
    permissions={int(guild): [
        bot.createPermissions("everyone", allowed=False)[guild],
        bot.createPermissions("owners", allowed=True)[guild]].append(
        bot.createPermissions("denied", allowed=False)[guild].append(
            bot.createPermissions("mods", allowed=True)[guild])
    )
        for guild in Perm.guild_owners
    },
    options=[create_option(
        name="mentionable",
        description="select a role",
        option_type=8,
        required=True
    )]
)
async def add_allowed(ctx: SlashContext, mentionable: discord.Role = None):
    try:
        if not ctx.guild.get_role(mentionable.id):
            await ctx.send(f"{mentionable} is not a role on this server!")
            return

        Perm.roles[str(ctx.guild_id)].append(mentionable.id)
        await ctx.send(f"Appended {mentionable.name} to the elevated roles list for this guild!")
        bot.database.log(str("Added role:" + mentionable.name + ", " + str(ctx.guild_id) + ", " + str(mentionable.id)),
                         True, error="", author=ctx.author.name)
        Perm.saveToFile()
    except Exception as e:
        logging.log(logging.WARN, str(e), repr(e))


@slash.slash(
    name="remove_allowed",
    guild_ids=Perm.guild,
    description="Remove a role that can set postability on comics",
    permissions={str(guild): [bot.createPermissions("everyone", allowed=False)[str(guild)],
                              bot.createPermissions("owners", allowed=True)[str(guild)]].append(
        bot.createPermissions("denied", allowed=False)[str(guild)].append(bot.createPermissions(
            "mods", allowed=True
        )[str(guild)])
    )
        for guild in Perm.guild_owners
    },
    options=[create_option(
        name="mentionable",
        description="select a role",
        option_type=8,
        required=True
    )]
)
async def remove_allowed(ctx: SlashContext, mentionable: discord.Role = None):
    try:
        if not ctx.guild.get_role(mentionable.id):
            await ctx.send(f"{mentionable} is not a role on this server!")
            return

        if mentionable.id not in Perm.roles[str(ctx.guild_id)]:
            await ctx.send(f"{mentionable} is not an allowed role on this server!")
            return
        Perm.roles[str(ctx.guild_id)].append(mentionable.id)
        await ctx.send(f"Removed {mentionable.name} from the elevated roles list for this guild!")
        bot.database.log(str("Added role:" + mentionable.name + ", " + str(ctx.guild_id) + ", " + str(mentionable.id)),
                         True, error="", author=ctx.author.name)
        Perm.saveToFile()
    except Exception as e:
        logging.log(logging.WARN, str(e), repr(e))


@slash.slash(
    name="set_report_channel",
    guild_ids=Perm.guild,
    description="Set a channel you want to receive report messages in!",
    permissions={str(guild): [bot.createPermissions("everyone", allowed=False)[str(guild)],
                              bot.createPermissions("owners", allowed=True)[str(guild)]].append(
        bot.createPermissions("denied", allowed=False)[str(guild)].append(bot.createPermissions(
            "mods", allowed=True
        )[str(guild)])
    )
        for guild in Perm.guild_owners
    },
    options=[
        create_option(
            name="channel",
            description="Select the Channel!",
            option_type=7,
            required=True
        )
    ]
)
async def set_report_channel(ctx: SlashContext, channel: discord.TextChannel):
    try:
        if not ctx.guild.get_channel(channel.id):
            await ctx.send(f"Could not set {channel} to a report channel! It might not exist")
            return
        Perm.bot_report_channel[str(ctx.guild_id)] = channel.id
        bot.database.log(str("Set report channel:" + channel.name + ", " + str(ctx.guild_id) + ", " + str(channel.id)),
                         True, error="", author=ctx.author.name)
        await ctx.send(f"Successfully set {channel.mention} as standard report channel!")
        Perm.saveToFile()
    except Exception as e:
        await ctx.send(f"Could not set {channel} to a report channel! It might not exist")
        logging.log(logging.WARN, str(e), repr(e))


@slash.slash(
    name="set_updates_channel",
    guild_ids=Perm.guild,
    description="Set a channel you want to receive update messages in!",
    permissions={str(guild): [bot.createPermissions("everyone", allowed=False)[str(guild)],
                              bot.createPermissions("owners", allowed=True)[str(guild)]].append(
        bot.createPermissions("denied", allowed=False)[str(guild)].append(bot.createPermissions(
            "mods", allowed=True
        )[str(guild)])
    )
        for guild in Perm.guild_owners
    },
    options=[
        create_option(
            name="channel",
            description="Select the Channel!",
            option_type=7,
            required=True
        )
    ]
)
async def set_updates_channel(ctx: SlashContext, channel: discord.TextChannel):
    try:
        if not ctx.guild.get_channel(channel.id):
            await ctx.send(f"Could not set {channel} to an update channel! It might not exist")
            return
        Perm.bot_updates_channel[str(ctx.guild_id)] = channel.id
        bot.database.log(str("Set update channel:" + channel.name + ", " + str(ctx.guild_id) + ", " + str(channel.id)),
                         True, error="", author=ctx.author.name)
        await ctx.send(f"Successfully set {channel.mention} as standard update channel!")
        Perm.saveToFile()
    except Exception as e:
        await ctx.send(f"Could not set {channel} to an update channel! It might not exist")
        logging.log(logging.WARN, str(e), repr(e))


@slash.slash(
    name="updates_enabled",
    guild_ids=Perm.guild,
    description="Set if you want to receive site updates!",
    permissions={str(guild): [bot.createPermissions("everyone", allowed=False)[str(guild)],
                              bot.createPermissions("owners", allowed=True)[str(guild)]].append(
        bot.createPermissions("denied", allowed=False)[str(guild)].append(bot.createPermissions(
            "mods", allowed=True
        )[str(guild)])
    )
        for guild in Perm.guild_owners
    },
    options=[
        create_option(
            name="receive",
            description="Select a setting!",
            option_type=5,
            required=True
        )
    ]
)
async def updates_enabled(ctx: SlashContext, receive: bool):
    try:
        Perm.bot_updates_enabled[str(ctx.guild_id)] = receive
        Perm.saveToFile()
        await ctx.send(f"Successfully {'disabled' if not receive else 'enabled'} site updates on this server!")
    except Exception as e:
        await ctx.send(f"Could not {'disable' if not receive else 'enable'} "
                       f"updates on this guild {ctx.guild_id=}, {ctx.guild.name=}")
        logging.log(logging.WARN, str(e), repr(e))


# ----------------------------------------------------------------------------------------------------------------------
# Owner Bot commands


@slash.slash(
    name="general_updates_enabled",
    guild_ids=[],  # Only allowed for setup guild
    description="Set if the main update loop should be running.",
    options=[
        create_option(
            name="receive",
            description="Select a setting!",
            option_type=5,
            required=True
        )
    ]
)
async def general_updates_enabled(ctx: SlashContext, receive: bool):
    try:
        if bot.interval_caller.is_started and not receive:
            await bot.interval_caller.stop()
        elif not bot.interval_caller.is_started and receive:
            await bot.interval_caller.start()
        await ctx.send(f"General updates are {'running' if bot.interval_caller.is_started else 'not running'}")

    except Exception as e:
        await ctx.send(f"Could not {'disable' if not receive else 'enable'} "
                       f"general updates {ctx.guild_id=}, {ctx.guild.name=}")
        logging.log(logging.WARN, str(e), repr(e))


@slash.slash(
    name="settings",
    guild_ids=[],  # Only allowed for setup guild
    description="load or dump settings from the file",
    options=[
        create_option(
            name="action",
            description="what to do",
            option_type=3,
            required=True,
            choices=[
                create_choice(
                    name="load",
                    value="load"
                ),
                create_choice(
                    name="dump",
                    value="dump"
                )])])
async def settings(ctx, action: str):
    if action == "load":
        Perm.updateFromFile()
    if action == "dump":
        Perm.saveToFile()
    await ctx.send("Success!")


bot.run(os.getenv("TOKEN"))

""" THIS WILL GET ALTERNATIVE SOURCE LINKS FOR BROKEN IMAGES!!
        ping = requests.get(str("https://xlecx.one" + image))
        if ping.status_code != 200:
            alt_image = "/".join(image.split("/")[:-1]) + "/thumbs/" + image.split("/")[-1]
            ping_alt = requests.get(str("https://xlecx.one" + alt_image))
            if ping_alt.status_code == 200:
                images_changed = True
"""
