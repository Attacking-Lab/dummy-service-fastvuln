from logging import LoggerAdapter
from re import L
from enochecker3 import ChainDB, Enochecker, GetflagCheckerTaskMessage, MumbleException, PutflagCheckerTaskMessage
from random import Random
from enochecker3.types import ExploitCheckerTaskMessage
import httpx
import json
from os import environ

checker_port = int(environ.get("CHECKER_PORT", 8000))
service_port = int(environ.get("SERVICE_PORT", 9000))
checker = Enochecker("fastvuln", service_port)
app = lambda: checker.app

ACCEPT_JSON = {"Content-Type": "application/json", "Accept": "application/json"}

async def register(client: httpx.AsyncClient, userdata: dict, logger: LoggerAdapter):
    try:
        logger.info(f">> register {userdata}")
        r = await client.post("/register", json=userdata)
        logger.info(f"<< register {r.json()}")
        r.raise_for_status()
    except (httpx.HTTPStatusError, json.decoder.JSONDecodeError):
        logger.exception("Faulty register")
        raise MumbleException("Faulty register")

async def login(client: httpx.AsyncClient, userdata: dict, logger: LoggerAdapter):
    try:
        logger.info(f">> login {userdata}")
        r = await client.post("/login", json=userdata)
        logger.info(f"<< login {r.json()}")
        r.raise_for_status()
    except (httpx.HTTPStatusError, json.decoder.JSONDecodeError):
        logger.exception("Faulty login")
        raise MumbleException("Faulty login")

async def get_profile(client: httpx.AsyncClient, logger: LoggerAdapter):
    try:
        logger.info(">> profile")
        r = await client.get("/profile")
        logger.info(f"<< profile {r.json()}")
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPStatusError, json.decoder.JSONDecodeError):
        logger.exception("Faulty profile")
        raise MumbleException("Faulty profile")

async def put_profile(client: httpx.AsyncClient, profile: dict, logger: LoggerAdapter):
    try:
        logger.info(f">> put_profile {profile}")
        r = await client.put("/profile", json=profile)
        logger.info(f"<< put_profile {r.json()}")
        r.raise_for_status()
    except (httpx.HTTPStatusError, json.decoder.JSONDecodeError):
        logger.exception("Faulty profile")
        raise MumbleException("Faulty profile")

@checker.putflag(0)
async def putflag0(task: PutflagCheckerTaskMessage, client: httpx.AsyncClient, random: Random, db: ChainDB, logger: LoggerAdapter):
    username = random.randbytes(16).hex()
    email = random.randbytes(16).hex()
    password = random.randbytes(16).hex()
    userdata = {"username": username, "email": email, "password": password}
    await register(client, userdata, logger)
    userdata.pop("email")
    await login(client, userdata, logger)
    profile = {
        "full_name": random.randbytes(8).hex(),
        "bio": "Hello, I'm checker, looking services with good SLA.\n" \
            f"My favorite dish is: {task.flag}"
    }
    await put_profile(client, profile, logger)
    await db.set("userdata", userdata)
    return username

@checker.getflag(0)
async def getflag0(task: GetflagCheckerTaskMessage, client: httpx.AsyncClient, db: ChainDB, logger: LoggerAdapter):
    try:
        userdata = await db.get("userdata")
    except KeyError:
        raise MumbleException("Missing data from previous round")
    await login(client, userdata, logger)
    try:
        profile = await get_profile(client, logger)
        flag = profile["bio"].split()[-1]
        assert flag == task.flag
    except (KeyError, AssertionError):
        raise MumbleException("Faulty profile data")

@checker.putnoise(0)
async def putnoise0(client: httpx.AsyncClient, db: ChainDB, random: Random, logger: LoggerAdapter):
    username = random.randbytes(16).hex()
    email = random.randbytes(16).hex()
    password = random.randbytes(16).hex()
    userdata = {"username": username, "email": email, "password": password}
    await register(client, userdata, logger)
    userdata.pop("email")
    await login(client, userdata, logger)
    dish = random.choice([
        "pineapple on pizza",
        "spaghetti with strawberry",
        "spaghetti with ketchup",
    ])
    profile = {
        "full_name": random.randbytes(8).hex(),
        "bio": "Hello, I'm checker, looking services with good SLA.\n" \
            f"My favorite dish is: {dish}"
    }
    await put_profile(client, profile, logger)
    await db.set("userdata", userdata)
    await db.set("dish", dish)

@checker.getnoise(0)
async def getnoise0(client: httpx.AsyncClient, db: ChainDB, logger: LoggerAdapter):
    try:
        userdata = await db.get("userdata")
        dish = await db.get("dish")
    except KeyError:
        raise MumbleException("Missing data from previous round")
    await login(client, userdata, logger)
    try:
        profile = await get_profile(client, logger)
        assert dish in profile["bio"]
    except (KeyError, AssertionError):
        raise MumbleException("Faulty profile data")

@checker.exploit(0)
async def exploit0(task: ExploitCheckerTaskMessage, client: httpx.AsyncClient, logger: LoggerAdapter):
    if (task.attack_info or "") == "":
        raise MumbleException("Missing attack info")
    req = {"username": task.attack_info}

    try:
        logger.info(f">> backdoor {req}")
        r = await client.get("/backdoor", params=req)
        logger.info(f"<< backdoor {r.json()}")
        return r.json()["bio"].split()[-1]
    except (KeyError, json.decoder.JSONDecodeError):
        pass

if __name__ == "__main__":
    checker.run(checker_port)
